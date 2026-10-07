from __future__ import annotations

import importlib
import importlib.util
import json
import os
import platform
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Optional


class CabtUnavailable(RuntimeError):
    """Raised when the official cabt runtime cannot be imported or loaded."""


class CabtInitializationError(RuntimeError):
    """Raised when the official engine rejects battle initialization."""


@dataclass(frozen=True)
class EnvironmentReport:
    os: str
    platform: str
    machine: str
    processor: str
    python_version: str
    kaggle_environments: str
    cg_package: str
    cabt_package: str
    native_library: str
    native_library_note: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def describe_environment(search_root: Path | None = None) -> EnvironmentReport:
    root = Path.cwd() if search_root is None else search_root
    kaggle = _module_status("kaggle_environments")
    cabt = _module_status("cabt")
    cg = _module_status("cg")
    native, note = detect_native_library(root)
    return EnvironmentReport(
        os=os.name,
        platform=platform.platform(),
        machine=platform.machine(),
        processor=platform.processor(),
        python_version=sys.version.replace("\n", " "),
        kaggle_environments=kaggle,
        cg_package=cg,
        cabt_package=cabt,
        native_library=native,
        native_library_note=note,
    )


def _module_status(name: str) -> str:
    spec = importlib.util.find_spec(name)
    return f"found: {spec.origin}" if spec else "missing"


def detect_native_library(root: Path) -> tuple[str, str]:
    candidates = list(root.rglob("libcg.so")) + list(root.rglob("cg.dll"))
    if not candidates:
        parent = root.parent if root.name == "cabt-local-simulator" else root
        candidates = list(parent.rglob("libcg.so")) + list(parent.rglob("cg.dll"))
    if not candidates:
        return "missing", "No official native engine library was found under the project or parent workspace."
    paths = ", ".join(f"{path} ({native_file_kind(path)})" for path in candidates[:8])
    note = "Found native library candidate(s). Import still must succeed on this OS/architecture."
    if platform.system() == "Darwin" and platform.machine().lower() == "arm64":
        note += " macOS ARM cannot load Linux ELF .so or Windows .dll engine binaries."
    return paths, note


def native_file_kind(path: Path) -> str:
    try:
        raw = path.read_bytes()[:64]
    except OSError:
        return "unreadable"
    if raw.startswith(b"\x7fELF") and len(raw) >= 20:
        endian = "<" if raw[5] == 1 else ">"
        try:
            import struct

            machine = struct.unpack(endian + "H", raw[18:20])[0]
        except Exception:
            machine = None
        names = {62: "Linux ELF x86-64", 183: "Linux ELF ARM64"}
        return names.get(machine, f"Linux ELF machine={machine}")
    if raw.startswith(b"MZ"):
        return "Windows PE/DLL"
    if raw.startswith(b"\xcf\xfa\xed\xfe") or raw.startswith(b"\xfe\xed\xfa\xcf"):
        return "macOS Mach-O"
    if raw.startswith(b"\xca\xfe\xba\xbe") or raw.startswith(b"\xbe\xba\xfe\xca"):
        return "macOS universal Mach-O"
    return "unknown binary"


def add_cg_search_path(path: str | Path | None = None) -> None:
    value = path or os.getenv("CABT_CG_PATH")
    if not value:
        return
    p = Path(value).expanduser().resolve()
    if p.is_dir():
        sys.path.insert(0, str(p))


def import_cg_module(module_name: str = "api", cg_path: str | Path | None = None) -> Any:
    add_cg_search_path(cg_path)
    errors: list[str] = []
    for name in (f"cg.{module_name}", f"cabt.{module_name}"):
        try:
            return importlib.import_module(name)
        except Exception as exc:
            errors.append(f"{name}: {type(exc).__name__}: {exc}")
    raise CabtUnavailable("; ".join(errors) or "cg/cabt module not available")


def get_card_api(cg_path: str | Path | None = None) -> Any:
    return import_cg_module("api", cg_path)


def get_game_api(cg_path: str | Path | None = None) -> Any:
    return import_cg_module("game", cg_path)


def kaggle_make_available() -> bool:
    return importlib.util.find_spec("kaggle_environments") is not None


@dataclass
class MatchResult:
    match_id: str
    engine: str
    winner: Optional[int]
    rewards: list[Any]
    done: bool
    turn_count: int
    decision_count: int
    termination_reason: str
    summary_path: Optional[str] = None
    replay_path: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_kaggle_env_match(
    deck_a: list[int],
    deck_b: list[int],
    agent_a: Callable[[dict], list[int]],
    agent_b: Callable[[dict], list[int]],
    replay_path: Path | None = None,
) -> MatchResult:
    try:
        from kaggle_environments import make
    except Exception as exc:
        raise CabtUnavailable(f"kaggle_environments unavailable: {exc}") from exc

    env = make("cabt", configuration={"decks": [deck_a, deck_b]})
    env.run([agent_a, agent_b])
    rewards = list(getattr(env, "rewards", []) or [])
    winner = _winner_from_rewards(rewards)
    if replay_path is not None:
        replay_path.parent.mkdir(parents=True, exist_ok=True)
        replay_path.write_text(env.render(mode="html"), encoding="utf-8")
    return MatchResult(
        match_id="kaggle-env-match",
        engine="kaggle_environments.cabt",
        winner=winner,
        rewards=rewards,
        done=True,
        turn_count=0,
        decision_count=0,
        termination_reason="env.run completed",
        replay_path=str(replay_path) if replay_path else None,
    )


def _winner_from_rewards(rewards: list[Any]) -> Optional[int]:
    if len(rewards) != 2:
        return None
    if rewards[0] == rewards[1]:
        return None
    return 0 if rewards[0] > rewards[1] else 1


def startdata_to_dict(start_data: Any) -> dict[str, Any]:
    if start_data is None:
        return {}
    data: dict[str, Any] = {}
    for name in ("battlePtr", "errorPlayer", "errorType"):
        try:
            data[name] = getattr(start_data, name)
        except Exception:
            pass
    return data


def write_summary(path: Path, result: MatchResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    result.summary_path = str(path)
    path.write_text(json.dumps(result.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
