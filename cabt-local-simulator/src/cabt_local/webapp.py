from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import io
import json
import os
import re
import shutil
import socket
import threading
import webbrowser
import zipfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from .card_catalog import CardCatalog, discover_csv_catalog
from .deck import DeckError, deck_report
from .engine import CabtUnavailable, describe_environment, get_game_api, native_file_kind
from .local_runtime import LocalRuntimeManager, effective_environment_report
from .replay_engine import LogReplayEngine, replay_engine_status
from .remote_engine import RemoteCabtGame, remote_engine_health
from .replay_visualizer import episode_payload_from_path
from .official_visualizer import refresh_replay_html
from .runner import TwoDeckRunner
from .study import (
    create_study,
    decide_finding,
    install_runtime_hook,
    list_checkpoints,
    load_study,
    memory_status,
    restore_checkpoint,
    validate_current_checkpoint,
)
from .study_page import STUDY_HTML
from .ui_theme import decorate_page


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
MAX_AGENT_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_AGENT_ARCHIVE_BYTES = 32 * 1024 * 1024
MAX_AGENT_ARCHIVE_FILES = 300


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cabt-local-app", description="Browser app for cabt local tooling.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--root", default="")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.root).expanduser().resolve() if args.root else project_root()
    return run_app(root=root, host=args.host, port=args.port, open_browser=not args.no_browser)


def run_app(root: Path, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, open_browser: bool = True) -> int:
    chosen_port = first_open_port(host, port)
    server = CabtLocalServer((host, chosen_port), CabtLocalHandler, root)
    url = f"http://{host}:{chosen_port}/"
    if open_browser:
        threading.Timer(0.35, lambda: webbrowser.open(url)).start()
    print(f"cabt local app: {url}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping cabt local app.")
    finally:
        server.server_close()
    return 0


def project_root() -> Path:
    here = Path.cwd().resolve()
    for candidate in (here, *here.parents):
        if (candidate / "pyproject.toml").exists() and (candidate / "src" / "cabt_local").exists():
            return candidate
    return Path(__file__).resolve().parents[2]


def first_open_port(host: str, preferred: int) -> int:
    for port in range(preferred, preferred + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((host, port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"No open port found from {preferred} to {preferred + 49}.")


class CabtLocalServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], handler_class: type[BaseHTTPRequestHandler], root: Path) -> None:
        super().__init__(server_address, handler_class)
        self.root = root.resolve()


class CabtLocalHandler(BaseHTTPRequestHandler):
    server: CabtLocalServer

    def do_HEAD(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/study"}:
            raw = (STUDY_HTML if parsed.path == "/study" else INDEX_HTML).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.send_html(INDEX_HTML)
            return
        if parsed.path == "/study":
            self.send_html(STUDY_HTML)
            return
        if parsed.path == "/api/status":
            self.send_json(build_status(self.server.root))
            return
        if parsed.path == "/api/deck-report":
            params = parse_qs(parsed.query)
            deck = (params.get("deck") or [""])[0]
            self.send_json(deck_report_payload(self.server.root, deck))
            return
        if parsed.path == "/api/results":
            self.send_json(results_payload(self.server.root))
            return
        if parsed.path == "/api/episodes":
            self.send_json(episodes_payload(self.server.root))
            return
        if parsed.path == "/api/episode":
            params = parse_qs(parsed.query)
            path = (params.get("path") or [""])[0]
            self.send_json(load_episode_payload(self.server.root, path))
            return
        if parsed.path == "/api/study/status":
            self.send_json(study_status_payload(self.server.root))
            return
        if parsed.path == "/api/study/session":
            params = parse_qs(parsed.query)
            study_id = (params.get("id") or [""])[0]
            try:
                self.send_json(load_study(self.server.root, study_id))
            except ValueError as exc:
                self.send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        if parsed.path == "/api/study/checkpoints":
            params = parse_qs(parsed.query)
            agent = (params.get("agent") or [""])[0]
            try:
                self.send_json(study_checkpoints_payload(self.server.root, agent))
            except ValueError as exc:
                self.send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        if parsed.path.startswith("/files/"):
            self.send_file(parsed.path.removeprefix("/files/"))
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/validate":
            payload = self.read_json()
            self.send_json(validate_match_deck_payload(self.server.root, payload))
            return
        if parsed.path == "/api/play":
            self.send_json(play_payload(self.server.root, self.read_json()))
            return
        if parsed.path == "/api/agents/import":
            try:
                payload = self.read_json(max_bytes=MAX_AGENT_UPLOAD_BYTES * 2)
                self.send_json(import_agent_payload(self.server.root, payload))
            except (ValueError, OSError, zipfile.BadZipFile) as exc:
                self.send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        if parsed.path == "/api/engine/start":
            self.send_json(runtime_action(self.server.root, "start"))
            return
        if parsed.path == "/api/engine/stop":
            self.send_json(runtime_action(self.server.root, "stop"))
            return
        if parsed.path == "/api/engine/verify":
            self.send_json(verify_kaggle_environment())
            return
        if parsed.path == "/api/visualize-log":
            payload = self.read_json()
            try:
                replay = LogReplayEngine.from_text(str(payload.get("text") or ""))
                self.send_json(replay.payload)
            except ValueError as exc:
                self.send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        if parsed.path == "/api/study/analyze":
            try:
                self.send_json(study_analyze_payload(self.server.root, self.read_json()))
            except (OSError, ValueError) as exc:
                self.send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        if parsed.path == "/api/study/decision":
            try:
                self.send_json(study_decision_payload(self.server.root, self.read_json()))
            except (OSError, ValueError) as exc:
                self.send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        if parsed.path == "/api/study/rollback":
            try:
                self.send_json(study_rollback_payload(self.server.root, self.read_json()))
            except (OSError, ValueError) as exc:
                self.send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        if parsed.path == "/api/study/validate":
            try:
                self.send_json(study_validate_payload(self.server.root, self.read_json()))
            except (OSError, ValueError) as exc:
                self.send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        if parsed.path == "/api/study/install-hook":
            try:
                self.send_json(study_install_hook_payload(self.server.root, self.read_json()))
            except (OSError, ValueError) as exc:
                self.send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def read_json(self, max_bytes: int = 2 * 1024 * 1024) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        if length > max_bytes:
            raise ValueError("Request body is too large.")
        raw = self.rfile.read(length).decode("utf-8")
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return value if isinstance(value, dict) else {}

    def send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        raw = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def send_html(self, html_text: str) -> None:
        raw = html_text.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def send_file(self, relative: str) -> None:
        try:
            target = safe_relative_path(self.server.root, relative)
        except ValueError:
            self.send_error(HTTPStatus.FORBIDDEN, "Forbidden")
            return
        if not target.exists() or not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        raw = target.read_bytes()
        if target.suffix.lower() == ".html" and target.parent == (self.server.root / "data" / "replays").resolve():
            raw = refresh_replay_html(target, raw.decode("utf-8")).encode("utf-8")
        content_type = {
            ".html": "text/html; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".jsonl": "application/x-ndjson; charset=utf-8",
            ".csv": "text/csv; charset=utf-8",
            ".log": "text/plain; charset=utf-8",
            ".txt": "text/plain; charset=utf-8",
        }.get(target.suffix.lower(), "application/octet-stream")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def build_status(root: Path) -> dict[str, Any]:
    report = effective_environment_report(root)
    engine = engine_probe(root)
    return {
        "root": str(root),
        "environment": report,
        "engine": engine,
        "runtime": LocalRuntimeManager(root).status(),
        "agents": discover_agents(root),
        "replay_engine": replay_engine_status().to_dict(),
        "decks": list_decks(root),
        "results": results_payload(root),
    }


def engine_probe(root: Path) -> dict[str, Any]:
    audit = official_runtime_audit(root)
    try:
        get_game_api(os.getenv("CABT_CG_PATH") or None)
    except CabtUnavailable as exc:
        remote = remote_engine_health(timeout_s=0.75)
        if remote.get("ok"):
            return {
                **audit,
                "available": True,
                "status": "official cabt engine ready through local Linux worker",
                "detail": "Real matches use the organizer's cg.game and libcg.so through Lima VZ and Rosetta.",
                "backend": "remote-linux-amd64",
                "worker": remote,
                "missing_components": [],
                "mac_note": "macOS ARM host; official Linux x86-64 engine is running in the local translated worker.",
            }
        return {
            **audit,
            "available": False,
            "status": "official cabt engine worker is stopped",
            "detail": str(remote.get("error") or exc),
            "backend": "unavailable",
            "mac_note": mac_runtime_note(root),
        }
    except Exception as exc:
        return {
            "available": False,
            "status": "official cabt engine import failed",
            "detail": f"{type(exc).__name__}: {exc}",
            **audit,
            "mac_note": mac_runtime_note(root),
        }
    return {
        **audit,
        "available": True,
        "status": "official cabt engine import succeeded",
        "detail": "Real matches can run from this app.",
        "backend": "in-process",
        "missing_components": [],
        "mac_note": mac_runtime_note(root),
    }


def runtime_action(root: Path, action: str) -> dict[str, Any]:
    manager = LocalRuntimeManager(root)
    try:
        return manager.start() if action == "start" else manager.stop()
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "runtime": manager.status()}


def verify_kaggle_environment() -> dict[str, Any]:
    try:
        return RemoteCabtGame(timeout_s=95.0).verify_environment()
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def official_runtime_audit(root: Path) -> dict[str, Any]:
    workspace = root.parent if root.name == "cabt-local-simulator" else root
    wrappers = sorted(workspace.rglob("cg/game.py"))
    native_paths = sorted(workspace.rglob("libcg.so")) + sorted(workspace.rglob("cg.dll"))
    wrapper_text = ", ".join(str(path.relative_to(workspace)) for path in wrappers[:8]) or "missing"
    native_text = ", ".join(
        f"{path.relative_to(workspace)} ({native_file_kind(path)})" for path in native_paths[:8]
    ) or "missing"
    return {
        "python_wrapper_source": wrapper_text,
        "native_core_files": native_text,
        "missing_components": [
            "a running local Lima/Rosetta worker, or a directly importable compatible cg package",
        ],
        "recovery_process": [
            "start the private Lima VZ virtual machine",
            "run an amd64 Python container through Apple's Rosetta for Linux",
            "load the organizer-provided cg package and libcg.so inside that worker",
            "send only battle API requests and observations over localhost",
        ],
    }


def mac_runtime_note(root: Path) -> str:
    report = describe_environment(root)
    machine = report.machine.lower()
    platform = report.platform.lower()
    if "macos" not in platform and "darwin" not in platform:
        return "This is not a macOS runtime."
    if "arm64" not in machine:
        return "macOS detected. A macOS-compatible official cabt native library is still required for real matches."
    native = report.native_library
    if ".so" in native or ".dll" in native:
        return (
            "macOS ARM detected. The native files cannot load directly, but this project can run the official Linux "
            "x86-64 build in its local Lima/Rosetta worker."
        )
    return "macOS ARM detected. No compatible official cabt native library was found."


def list_decks(root: Path) -> list[dict[str, Any]]:
    catalog = load_catalog(root)
    paths = list(sorted((root / "decks").glob("*.csv"))) if (root / "decks").exists() else []
    for profile in discover_agents(root):
        deck_ref = str(profile.get("deck") or "")
        if not deck_ref:
            continue
        try:
            paths.append(_reference_path(root, deck_ref))
        except ValueError:
            continue

    rows: list[dict[str, Any]] = []
    seen: set[Path] = set()
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        reference = deck_reference(root, resolved)
        payload = deck_report_payload(root, reference, catalog=catalog)
        rows.append(
            {
                "path": reference,
                "card_count": payload.get("card_count", 0),
                "valid_size": payload.get("valid_size", False),
                "unsupported_ids": payload.get("unsupported_ids", []),
                "error": payload.get("error", ""),
            }
        )
    return rows


def discover_agents(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {"name": "Random", "spec": "random", "deck": "", "source": "built-in", "ready": True}
    ]
    workspace = root.parent
    for path in sorted(workspace.glob("*/agent.py")):
        if path.parent == root or "sample_submission" in path.parts:
            continue
        rows.append(_agent_profile(root, path, path.parent / "deck.csv", path.parent.name, "workspace"))

    imported_root = root / "data" / "imported_agents"
    manifests = sorted(imported_root.glob("*/agent-manifest.json")) if imported_root.exists() else []
    for manifest_path in manifests:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            agent_path = (manifest_path.parent / str(manifest["agent"])).resolve()
            deck_value = str(manifest.get("deck") or "")
            deck_path = (manifest_path.parent / deck_value).resolve() if deck_value else None
            name = str(manifest.get("name") or manifest_path.parent.name)
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            continue
        if agent_path.is_file():
            rows.append(_agent_profile(root, agent_path, deck_path, name, "imported"))

    deduplicated: list[dict[str, Any]] = []
    seen_specs: set[str] = set()
    for row in rows:
        spec = str(row["spec"])
        if spec in seen_specs:
            continue
        seen_specs.add(spec)
        deduplicated.append(row)
    return deduplicated


def _agent_profile(
    root: Path,
    agent_path: Path,
    deck_path: Path | None,
    name: str,
    source: str,
) -> dict[str, Any]:
    agent_ref = deck_reference(root, agent_path.resolve())
    has_deck = bool(deck_path and deck_path.is_file())
    return {
        "name": name,
        "spec": f"file:{agent_ref}:agent",
        "agent_path": str(agent_path.resolve()),
        "deck": deck_reference(root, deck_path.resolve()) if has_deck and deck_path else "",
        "source": source,
        "ready": agent_path.is_file() and has_deck,
    }


def deck_reference(root: Path, path: Path) -> str:
    return os.path.relpath(path.resolve(), root.resolve())


def _reference_path(root: Path, reference: str) -> Path:
    path = Path(unquote(reference).strip()).expanduser()
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def load_catalog(root: Path) -> CardCatalog | None:
    found = discover_csv_catalog(root)
    if not found:
        return None
    try:
        return CardCatalog.from_csv(found)
    except Exception:
        return None


def deck_report_payload(root: Path, deck: str, catalog: CardCatalog | None = None) -> dict[str, Any]:
    if not deck:
        return {"ok": False, "error": "No deck selected."}
    try:
        path = resolve_deck_reference(root, deck)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    try:
        report = deck_report(path, catalog if catalog is not None else load_catalog(root))
    except (DeckError, OSError, ValueError) as exc:
        return {"ok": False, "path": str(path), "error": str(exc)}
    return {
        "ok": report.valid_size and not report.unsupported_ids,
        "path": deck_reference(root, path),
        "card_count": report.card_count,
        "valid_size": report.valid_size,
        "unsupported_ids": report.unsupported_ids,
        "rows": report.rows,
    }


def validate_match_deck_payload(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    reference = str(payload.get("deck") or "auto")
    side = str(payload.get("side") or "a").lower()
    profile = find_agent_profile(root, str(payload.get("agent") or "random"))
    default_reference = "decks/deck_b.csv" if side == "b" else "decks/deck_a.csv"
    try:
        path = resolve_match_deck(root, reference, profile, default_reference)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return deck_report_payload(root, deck_reference(root, path))


def play_payload(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    raw_agent_a = str(payload.get("agent_a") or "random")
    raw_agent_b = str(payload.get("agent_b") or "random")
    profile_a = find_agent_profile(root, raw_agent_a)
    profile_b = find_agent_profile(root, raw_agent_b)
    agent_a = normalize_agent_spec(root, raw_agent_a)
    agent_b = normalize_agent_spec(root, raw_agent_b)
    record = bool(payload.get("record"))
    direct_cg = bool(payload.get("direct_cg"))
    timeout_s = float(payload.get("timeout_s") or 5.0)
    cg_path = str(payload.get("cg_path") or "")
    try:
        deck_a_path = resolve_match_deck(
            root, str(payload.get("deck_a") or "auto"), profile_a, "decks/deck_a.csv"
        )
        deck_b_path = resolve_match_deck(
            root, str(payload.get("deck_b") or "auto"), profile_b, "decks/deck_b.csv"
        )
        runner = TwoDeckRunner(root / "data", cg_path=cg_path or None, timeout_s=timeout_s)
        result = runner.play_paths(
            deck_a_path,
            deck_b_path,
            agent_a,
            agent_b,
            record=record,
            prefer_kaggle_env=not direct_cg,
            agent_a_name=str((profile_a or {}).get("name") or raw_agent_a),
            agent_b_name=str((profile_b or {}).get("name") or raw_agent_b),
        )
    except Exception as exc:
        return {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "engine": engine_probe(root),
        }
    data = result.to_dict()
    data["ok"] = True
    if data.get("replay_path"):
        data["replay_url"] = file_url(root, Path(str(data["replay_path"])))
    if data.get("summary_path"):
        data["summary_url"] = file_url(root, Path(str(data["summary_path"])))
    return data


def resolve_match_deck(
    root: Path,
    deck_reference_value: str,
    profile: dict[str, Any] | None,
    default_reference: str,
) -> Path:
    reference = deck_reference_value.strip()
    if not reference or reference == "auto":
        reference = str((profile or {}).get("deck") or default_reference)
    return resolve_deck_reference(root, reference)


def resolve_deck_reference(root: Path, reference: str) -> Path:
    candidate = _reference_path(root, reference)
    if candidate.is_relative_to(root.resolve()):
        return candidate
    known = {
        _reference_path(root, str(profile["deck"]))
        for profile in discover_agents(root)
        if profile.get("deck")
    }
    if candidate not in known:
        raise ValueError("Deck must be inside this project or paired with a discovered agent.")
    return candidate


def find_agent_profile(root: Path, spec: str) -> dict[str, Any] | None:
    normalized = normalize_agent_spec(root, spec)
    for profile in discover_agents(root):
        if normalize_agent_spec(root, str(profile["spec"])) == normalized:
            return profile
    return None


def import_agent_payload(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    filename = Path(str(payload.get("filename") or "")).name
    if not filename:
        raise ValueError("Choose an agent.py file or a Kaggle submission ZIP.")
    suffix = Path(filename).suffix.lower()
    if suffix not in {".py", ".zip"}:
        raise ValueError("Agent import accepts only .py or .zip files.")

    encoded = str(payload.get("content_base64") or "")
    try:
        content = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Agent upload is not valid base64 data.") from exc
    if not content:
        raise ValueError("The selected agent file is empty.")
    if len(content) > MAX_AGENT_UPLOAD_BYTES:
        raise ValueError(f"Agent package exceeds the {MAX_AGENT_UPLOAD_BYTES // (1024 * 1024)} MB limit.")

    display_name = str(payload.get("name") or Path(filename).stem).strip() or "Imported Agent"
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", display_name).strip("-.") or "agent"
    digest = hashlib.sha256(content).hexdigest()[:12]
    imported_root = root / "data" / "imported_agents"
    imported_root.mkdir(parents=True, exist_ok=True)
    destination = imported_root / f"{slug[:48]}-{digest}"
    staging = imported_root / f".{slug[:32]}-{digest}-{os.getpid()}-{threading.get_ident()}.tmp"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    try:
        if suffix == ".zip":
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                _extract_agent_archive(archive, staging)
            agent_path = _choose_package_file(staging, "agent.py", required=True)
            deck_path = _choose_package_deck(staging, agent_path)
        else:
            content.decode("utf-8-sig")
            agent_path = staging / "agent.py"
            agent_path.write_bytes(content)
            deck_path = None

        fallback = str(payload.get("deck") or "").strip()
        if deck_path is None and fallback and fallback != "auto":
            source_deck = resolve_deck_reference(root, fallback)
            deck_path = staging / "deck.csv"
            shutil.copy2(source_deck, deck_path)

        manifest = {
            "name": display_name,
            "source_filename": filename,
            "agent": agent_path.relative_to(staging).as_posix(),
            "deck": deck_path.relative_to(staging).as_posix() if deck_path else "",
        }
        (staging / "agent-manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        if destination.exists():
            shutil.rmtree(destination)
        staging.rename(destination)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise

    final_agent = destination / manifest["agent"]
    final_deck = destination / manifest["deck"] if manifest["deck"] else None
    profile = _agent_profile(root, final_agent, final_deck, display_name, "imported")
    deck_result = deck_report_payload(root, str(profile["deck"])) if profile["deck"] else {
        "ok": False,
        "error": "No deck.csv was found. Select a deck override before running this agent.",
    }
    return {"ok": True, "agent": profile, "deck_report": deck_result}


def _extract_agent_archive(archive: zipfile.ZipFile, target_root: Path) -> None:
    infos = [info for info in archive.infolist() if info.filename and not info.filename.endswith("/")]
    if len(infos) > MAX_AGENT_ARCHIVE_FILES:
        raise ValueError(f"Agent ZIP contains more than {MAX_AGENT_ARCHIVE_FILES} files.")
    total_size = sum(info.file_size for info in infos)
    if total_size > MAX_AGENT_ARCHIVE_BYTES:
        raise ValueError("Expanded agent ZIP is too large.")
    for info in infos:
        normalized = info.filename.replace("\\", "/")
        relative = PurePosixPath(normalized)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Unsafe path in agent ZIP: {info.filename}")
        if relative.parts and relative.parts[0] == "__MACOSX":
            continue
        file_type = (info.external_attr >> 16) & 0o170000
        if file_type == 0o120000:
            raise ValueError(f"Symbolic links are not allowed in agent ZIP: {info.filename}")
        destination = target_root.joinpath(*relative.parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(info) as source, destination.open("wb") as output:
            shutil.copyfileobj(source, output)


def _choose_package_file(root: Path, filename: str, required: bool = False) -> Path | None:
    candidates = sorted(
        (path for path in root.rglob(filename) if "__MACOSX" not in path.parts),
        key=lambda path: (len(path.relative_to(root).parts), path.as_posix()),
    )
    if not candidates:
        if required:
            raise ValueError(f"Agent ZIP does not contain {filename}.")
        return None
    return candidates[0]


def _choose_package_deck(root: Path, agent_path: Path) -> Path | None:
    beside_agent = agent_path.parent / "deck.csv"
    return beside_agent if beside_agent.is_file() else _choose_package_file(root, "deck.csv")


def results_payload(root: Path) -> dict[str, Any]:
    summaries = []
    for path in newest_paths((root / "data" / "summaries").glob("*.json")):
        summaries.append({"name": path.name, "url": file_url(root, path)})
    replays = []
    for path in newest_paths((root / "data" / "replays").glob("*.html")):
        replays.append({"name": path.name, "url": file_url(root, path)})
    return {"summaries": summaries, "replays": replays, "episodes": episodes_payload(root)["episodes"]}


def normalize_agent_spec(root: Path, spec: str) -> str:
    if not spec.startswith("file:"):
        return spec
    value = spec.removeprefix("file:")
    path_text, separator, function_name = value.rpartition(":")
    if not separator:
        path_text, function_name = value, "agent"
    path = Path(path_text).expanduser()
    if not path.is_absolute():
        path = (root / path).resolve()
    return f"file:{path}:{function_name or 'agent'}"


def episodes_payload(root: Path) -> dict[str, Any]:
    episodes = []
    episode_dir = root / "data" / "episodes"
    paths = newest_paths(
        path for path in episode_dir.glob("*.jsonl") if not path.name.endswith(".invalid.jsonl")
    ) if episode_dir.exists() else []
    for path in paths:
        try:
            lines = sum(1 for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip())
        except OSError:
            lines = 0
        episodes.append({"name": path.name, "path": path.relative_to(root).as_posix(), "decisions": lines})
    return {"episodes": episodes}


def newest_paths(paths: Any, limit: int = 20) -> list[Path]:
    return sorted(paths, key=lambda path: path.stat().st_mtime_ns, reverse=True)[:limit]


def load_episode_payload(root: Path, path: str) -> dict[str, Any]:
    if not path:
        return {"ok": False, "error": "No episode selected."}
    try:
        target = safe_relative_path(root, path)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    if not target.exists():
        return {"ok": False, "error": f"Episode file does not exist: {path}"}
    payload = episode_payload_from_path(target)
    replay = root / "data" / "replays" / f"{target.stem}.html"
    if replay.is_file():
        payload["review_url"] = file_url(root, replay)
    return payload


def study_status_payload(root: Path) -> dict[str, Any]:
    return {
        "ok": True,
        "agents": discover_agents(root),
        "episodes": episodes_payload(root)["episodes"],
    }


def study_analyze_payload(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    agent_spec = str(payload.get("agent") or "")
    profile = find_agent_profile(root, agent_spec)
    if profile is None or profile.get("spec") == "random":
        raise ValueError("Choose a discovered file agent for this study.")
    log_text = str(payload.get("log_text") or "").strip()
    if not log_text:
        raise ValueError("Paste or upload a battle log before analysis.")
    episode_reference = str(payload.get("episode_path") or "").strip()
    episode_path = safe_relative_path(root, episode_reference) if episode_reference else None
    if episode_path is not None:
        episode_root = (root / "data" / "episodes").resolve()
        if not episode_path.is_relative_to(episode_root) or episode_path.suffix.lower() != ".jsonl":
            raise ValueError("Decision trace must be a recorded episode JSONL file.")
        if not episode_path.is_file():
            raise ValueError("Decision trace does not exist.")
    return create_study(root, log_text=log_text, agent_profile=profile, episode_path=episode_path)


def study_decision_payload(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    study_id = str(payload.get("study_id") or "")
    study = load_study(root, study_id)
    stored_spec = str((study.get("agent") or {}).get("spec") or "")
    profile = find_agent_profile(root, stored_spec)
    if profile is None:
        raise ValueError("The agent used by this study is no longer available.")
    edited_rule = payload.get("edited_rule")
    if edited_rule is not None and not isinstance(edited_rule, dict):
        raise ValueError("Edited rule must be a JSON object.")
    return decide_finding(
        root,
        study_id=study_id,
        finding_id=str(payload.get("finding_id") or ""),
        decision=str(payload.get("decision") or ""),
        agent_profile=profile,
        edited_rule=edited_rule,
        reviewer_note=str(payload.get("reviewer_note") or ""),
    )


def study_checkpoints_payload(root: Path, agent_spec: str) -> dict[str, Any]:
    profile = find_agent_profile(root, agent_spec)
    if profile is None or profile.get("spec") == "random":
        raise ValueError("Choose a discovered file agent.")
    return {
        "ok": True,
        "agent": profile,
        "memory": memory_status(root, profile),
        "checkpoints": list_checkpoints(root, profile),
    }


def study_rollback_payload(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    profile = find_agent_profile(root, str(payload.get("agent") or ""))
    if profile is None or profile.get("spec") == "random":
        raise ValueError("Choose a discovered file agent.")
    checkpoint = restore_checkpoint(root, profile, str(payload.get("checkpoint_id") or ""))
    return {
        "ok": True,
        "checkpoint": checkpoint,
        "memory": memory_status(root, profile),
        "checkpoints": list_checkpoints(root, profile),
    }


def study_validate_payload(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    profile = find_agent_profile(root, str(payload.get("agent") or ""))
    if profile is None or profile.get("spec") == "random":
        raise ValueError("Choose a discovered file agent.")
    validation = validate_current_checkpoint(root, profile)
    return {
        "ok": True,
        "validation": validation,
        "memory": memory_status(root, profile),
        "checkpoints": list_checkpoints(root, profile),
    }


def study_install_hook_payload(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    profile = find_agent_profile(root, str(payload.get("agent") or ""))
    if profile is None or profile.get("spec") == "random":
        raise ValueError("Choose a discovered file agent.")
    result = install_runtime_hook(root, profile)
    result["memory"] = memory_status(root, profile)
    return result


def safe_relative_path(root: Path, value: str) -> Path:
    root = root.resolve()
    clean = unquote(value).strip()
    path = Path(clean)
    if path.is_absolute():
        resolved = path.resolve()
    else:
        resolved = (root / path).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("Path must stay inside the cabt-local-simulator folder.")
    return resolved


def file_url(root: Path, path: Path) -> str:
    try:
        rel = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return ""
    return "/files/" + rel


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Battle Lab | Simulator</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #17202a;
      --muted: #5e6b78;
      --line: #ccd6df;
      --panel: #f7f9fb;
      --accent: #176f8f;
      --accent-2: #1f7a4f;
      --warn: #9a5a12;
      --bad: #a73939;
      --good: #1f7a4f;
      --white: #ffffff;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: var(--white);
    }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 16px 20px;
      border-bottom: 1px solid var(--line);
      background: #eef5f7;
    }
    h1 { margin: 0; font-size: 20px; font-weight: 700; letter-spacing: 0; }
    h2 { margin: 0 0 12px; font-size: 15px; letter-spacing: 0; }
    main {
      display: grid;
      grid-template-columns: minmax(280px, 360px) minmax(0, 1fr);
      min-height: calc(100vh - 58px);
    }
    aside {
      border-right: 1px solid var(--line);
      background: var(--panel);
      padding: 16px;
      overflow: auto;
    }
    section { padding: 16px; }
    button, select, input {
      min-height: 36px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--white);
      color: var(--ink);
      font: inherit;
    }
    button {
      padding: 0 12px;
      cursor: pointer;
      font-weight: 650;
    }
    button.primary { background: var(--accent); border-color: var(--accent); color: white; }
    button.secondary { background: #edf8f1; border-color: #b7d8c6; color: #124b2f; }
    .toolbar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
    .field { display: grid; gap: 6px; margin-bottom: 12px; }
    .field label { font-size: 12px; font-weight: 700; color: var(--muted); }
    .field > input, .field > select { width: 100%; padding: 0 8px; }
    .field > input[type="file"] { padding: 6px 8px; }
    .panel {
      border-top: 1px solid var(--line);
      padding: 16px 0;
    }
    .status {
      display: inline-flex;
      align-items: center;
      min-height: 28px;
      padding: 4px 8px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 700;
      border: 1px solid var(--line);
      background: white;
    }
    .status.good { color: var(--good); border-color: #a6d8be; background: #f0fbf5; }
    .status.bad { color: var(--bad); border-color: #e5b6b6; background: #fff4f4; }
    .status.warn { color: var(--warn); border-color: #ead0a7; background: #fff8eb; }
    .deck-list { display: grid; gap: 8px; }
    .deck-row {
      display: grid;
      gap: 4px;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: white;
    }
    .deck-row strong { font-size: 13px; overflow-wrap: anywhere; }
    .deck-row span { color: var(--muted); font-size: 12px; }
    .grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
      margin-bottom: 16px;
    }
    .output {
      height: min(58vh, 620px);
      overflow: auto;
      white-space: pre-wrap;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      background: #101820;
      color: #e9f4f6;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 12px;
      line-height: 1.45;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      background: white;
    }
    th, td {
      padding: 8px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      font-size: 13px;
    }
    th { background: #eef5f7; color: #344451; }
    a { color: var(--accent); font-weight: 700; text-decoration: none; }
    textarea {
      width: 100%;
      min-height: 160px;
      resize: vertical;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      font: 12px/1.45 ui-monospace, SFMono-Regular, Menlo, monospace;
      color: var(--ink);
      background: white;
    }
    .visualizer {
      display: grid;
      gap: 16px;
      margin-top: 12px;
    }
    .board-view {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }
    .player-board {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: white;
      padding: 12px;
      display: grid;
      gap: 10px;
      min-width: 0;
    }
    .player-board h3 {
      margin: 0;
      font-size: 14px;
      letter-spacing: 0;
    }
    .zone {
      display: grid;
      gap: 6px;
      min-width: 0;
    }
    .zone-label {
      color: var(--muted);
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
    }
    .pill-line {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }
    .pill {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 4px 8px;
      background: #f7fbfb;
      font-size: 12px;
      overflow-wrap: anywhere;
    }
    .timeline {
      display: grid;
      gap: 8px;
      max-height: 620px;
      overflow: auto;
      padding-right: 4px;
    }
    .event-card {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      background: white;
      display: grid;
      gap: 6px;
    }
    .event-button {
      width: 100%;
      min-height: 0;
      text-align: left;
      cursor: pointer;
      font: inherit;
    }
    .event-button.current {
      border-color: var(--accent);
      background: #eaf7fb;
    }
    .event-button.unknown {
      border-color: #e1b5b5;
      background: #fff8f8;
    }
    .replay-controls {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #f7f9fb;
    }
    .replay-controls input[type="range"] {
      flex: 1;
      min-width: 180px;
    }
    .event-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      align-items: center;
      color: var(--muted);
      font-size: 12px;
    }
    .event-action {
      color: var(--accent);
      font-weight: 800;
    }
    .event-raw {
      font-size: 13px;
      overflow-wrap: anywhere;
    }
    .event-detail {
      white-space: pre-wrap;
      color: var(--muted);
      font-size: 12px;
    }
    .decision-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 8px;
    }
    .option-list {
      display: grid;
      gap: 4px;
      max-height: 180px;
      overflow: auto;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 12px;
    }
    .selected-option {
      background: #eaf7fb;
      border-color: #a8d9e8;
    }
    @media (max-width: 760px) {
      main { grid-template-columns: 1fr; }
      aside { border-right: 0; border-bottom: 1px solid var(--line); }
      .grid { grid-template-columns: 1fr; }
      .board-view { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header class="app-header">
    <a class="brand" href="/"><span class="brand-mark">__ICON_layers__</span><span><strong>Battle Lab</strong><small>cabt local simulator</small></span></a>
    <nav class="app-nav" aria-label="Main navigation"><a href="/" aria-current="page">__ICON_swords__ Simulator</a><a href="/study">__ICON_book-open__ Study</a></nav>
    <div class="header-tools">
      <button id="engineBadge" class="status warn" title="Open engine settings">Checking engine</button>
      <button id="refreshBtn" class="icon-button" title="Refresh agents and battles" aria-label="Refresh agents and battles">__ICON_refresh-cw__</button>
    </div>
  </header>
  <main>
    <aside>
      <div class="match-form">
        <p class="eyebrow">New battle</p>
        <h2>Choose your agents</h2>
        <div class="field">
          <label class="agent-label" for="agentA"><span class="side-mark">A</span> Agent A</label>
          <select id="agentA" aria-label="Agent A"><option>Loading agents...</option></select>
        </div>
        <div class="field">
          <label class="agent-label" for="agentB"><span class="side-mark b">B</span> Agent B</label>
          <select id="agentB" aria-label="Agent B"><option>Loading agents...</option></select>
        </div>
        <div class="match-actions">
          <button id="playBtn" class="primary" disabled>__ICON_play__ Run match</button>
          <button id="validateBtn" class="icon-button" title="Validate selected deck" aria-label="Validate selected deck">__ICON_check__</button>
        </div>
      </div>
      <details class="fold" id="packageSettings">
        <summary>__ICON_folder-open__ Agent packages</summary>
        <div class="fold-body">
          <div class="field"><label for="agentFileA">Import for Agent A</label><input id="agentFileA" type="file" accept=".zip,.py,application/zip,text/x-python"></div>
          <div class="field"><label for="agentFileB">Import for Agent B</label><input id="agentFileB" type="file" accept=".zip,.py,application/zip,text/x-python"></div>
          <div id="agentList" class="deck-list"></div>
        </div>
      </details>
      <details class="fold" id="deckSettings">
        <summary>__ICON_layers__ Decks &amp; overrides</summary>
        <div class="fold-body">
          <div class="field"><label for="deckA">Deck A</label><select id="deckA"></select></div>
          <div class="field"><label for="deckB">Deck B</label><select id="deckB"></select></div>
          <div id="deckList" class="deck-list"></div>
        </div>
      </details>
      <details class="fold" id="engineSettings">
        <summary>__ICON_cpu__ Engine &amp; environment</summary>
        <div class="fold-body">
          <div class="toolbar" style="margin-bottom:16px">
            <button id="startEngineBtn" class="primary">Start engine</button>
            <button id="stopEngineBtn">Stop engine</button>
            <button id="verifyEngineBtn">Verify environment</button>
          </div>
          <details class="fold"><summary>Execution environment</summary><div class="fold-body"><table id="envTable"></table></div></details>
          <details class="fold"><summary>Official match engine</summary><div class="fold-body"><table id="engineTable"></table></div></details>
          <details class="fold"><summary>Local runtime</summary><div class="fold-body"><table id="runtimeTable"></table></div></details>
          <details class="fold"><summary>Log replay engine</summary><div class="fold-body"><table id="replayEngineTable"></table></div></details>
        </div>
      </details>
      <details class="fold" id="logImport">
        <summary>__ICON_upload__ Import a battle log</summary>
        <div class="fold-body">
          <div class="field"><label for="episodeSelect">Recorded episode</label><select id="episodeSelect"></select></div>
          <div class="toolbar" style="margin-bottom:16px"><button id="loadEpisodeBtn">Open episode</button></div>
          <div class="field"><label for="logFile">Log file</label><input id="logFile" type="file" accept=".txt,.log,.jsonl,.html"></div>
          <div class="field"><label for="logText">Battle log</label><textarea id="logText"></textarea></div>
          <button id="parseLogBtn" class="primary">Visualize log</button>
        </div>
      </details>
    </aside>
    <section>
      <div class="page-heading"><div><p class="eyebrow">Your local arena</p><h1>Battle simulator</h1></div><span id="battleCount" class="status">Loading battles</span></div>
      <div id="activityStatus" class="inline-status" role="status" aria-live="polite"></div>
      <div class="result-library" id="battleLibrary">
        <div class="library-heading"><h2>Recent battles</h2><input id="battleSearch" type="search" aria-label="Find a battle" placeholder="Find a battle..."></div>
        <div id="resultLinks" class="battle-list"><div class="empty-view">__ICON_swords__<h2>Loading your battles</h2></div></div>
      </div>
      <div id="replayHeading" class="section-heading" hidden><h2 id="replayTitle">Log replay</h2><button id="backToBattles" class="icon-button" aria-label="Back to recent battles" title="Back to recent battles">__ICON_arrow-left__</button></div>
      <div id="visualizer" class="visualizer" aria-live="polite"></div>
      <details class="fold" id="summaryFiles"><summary>__ICON_download__ Result files</summary><div id="summaryLinks" class="fold-body deck-list"></div></details>
      <details class="fold" id="executionLog"><summary>__ICON_settings-2__ Execution details</summary><div class="fold-body"><pre id="output" class="output"></pre></div></details>
    </section>
  </main>
  <script>
    const state = { decks: [], agents: [], episodes: [], replays: [], replayPayload: null, replayCursor: -1, busy: false, engineReady: false };
    const $ = (id) => document.getElementById(id);

    function print(value) {
      $("output").textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
      const failed = value && typeof value === "object" && (value.ok === false || value.error);
      $("activityStatus").className = `inline-status${failed ? " bad" : ""}`;
      $("activityStatus").textContent = typeof value === "string" ? value : failed ? String(value.error || "Action failed. See execution details.") : "";
    }

    function table(el, data) {
      const rows = Object.entries(data || {}).map(([k, v]) => {
        const text = typeof v === "object" ? JSON.stringify(v) : String(v);
        return `<tr><th>${escapeHtml(k)}</th><td>${escapeHtml(text)}</td></tr>`;
      }).join("");
      el.innerHTML = rows || "<tr><td>No data</td></tr>";
    }

    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
      }[c]));
    }

    async function getJson(url) {
      const res = await fetch(url, { cache: "no-store" });
      return await res.json();
    }

    async function postJson(url, body) {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
      return await res.json();
    }

    function renderDecks(decks) {
      state.decks = decks || [];
      const previousA = $("deckA").value || "auto";
      const previousB = $("deckB").value || "auto";
      const choices = state.decks.map((d) => `<option value="${escapeHtml(d.path)}">${escapeHtml(d.path)}</option>`).join("");
      const options = `<option value="auto">Automatic from agent package</option>${choices}`;
      $("deckA").innerHTML = options;
      $("deckB").innerHTML = options;
      $("deckA").value = [...$("deckA").options].some((x) => x.value === previousA) ? previousA : "auto";
      $("deckB").value = [...$("deckB").options].some((x) => x.value === previousB) ? previousB : "auto";
      $("deckList").innerHTML = state.decks.map((d) => {
        const cls = d.valid_size && (!d.unsupported_ids || d.unsupported_ids.length === 0) ? "good" : "bad";
        const msg = d.error || `${d.card_count} cards`;
        return `<div class="deck-row"><strong>${escapeHtml(d.path)}</strong><span class="status ${cls}">${escapeHtml(msg)}</span></div>`;
      }).join("") || "<div class='deck-row'><strong>No deck CSV found</strong><span>Put files under decks/</span></div>";
    }

    function renderAgents(agents) {
      state.agents = agents || [];
      const previousA = $("agentA").value || "random";
      const previousB = $("agentB").value || "random";
      const options = state.agents.map((agent) => {
        const suffix = agent.deck ? "" : " [deck override]";
        return `<option value="${escapeHtml(agent.spec)}">${escapeHtml(agent.name + suffix)}</option>`;
      }).join("");
      $("agentA").innerHTML = options;
      $("agentB").innerHTML = options;
      $("agentA").value = state.agents.some((x) => x.spec === previousA) ? previousA : "random";
      $("agentB").value = state.agents.some((x) => x.spec === previousB) ? previousB : "random";
      $("agentList").innerHTML = state.agents.filter((agent) => agent.spec !== "random").map((agent) => {
        const cls = agent.ready ? "good" : "warn";
        const detail = agent.deck ? `${agent.source} | ${agent.deck}` : `${agent.source} | deck override required`;
        return `<div class="deck-row"><strong>${escapeHtml(agent.name)}</strong><span class="status ${cls}">${escapeHtml(detail)}</span></div>`;
      }).join("") || "<div class='deck-row'><strong>No agent packages</strong></div>";
    }

    function renderResults(results) {
      state.replays = results.replays || [];
      renderBattleList();
      $("summaryLinks").innerHTML = (results.summaries || []).map(item => `<a class="deck-row" href="${escapeHtml(item.url)}" target="_blank" rel="noopener">${escapeHtml(item.name)}</a>`).join("") || "<p class='muted'>No result files yet.</p>";
      renderEpisodes(results.episodes || []);
    }

    function renderBattleList() {
      const query = $("battleSearch").value.trim().toLowerCase();
      const rows = state.replays.filter(item => item.name.toLowerCase().includes(query));
      $("battleCount").textContent = `${state.replays.length} recent battles`;
      $("resultLinks").innerHTML = rows.map(item => {
        const match = item.name.match(/^battle(\d+)_(\d{2})-(\d{2})_(\d{4}-\d{2}-\d{2})_(.+)_vs_(.+)\.html$/);
        const title = match ? `Battle ${match[1]} · ${match[5]} vs ${match[6]}` : item.name.replace(/\.html$/, "");
        const detail = match ? `${match[4]} at ${match[2]}:${match[3]}` : "Recorded battle";
        return `<a class="battle-row" href="${escapeHtml(item.url)}"><span class="battle-art">__ICON_swords__</span><span><strong>${escapeHtml(title)}</strong><small>${escapeHtml(detail)}</small></span>__ICON_chevron-right__</a>`;
      }).join("") || `<div class="empty-view">__ICON_search__<h2>${query ? "No matching battles" : "No battles yet"}</h2></div>`;
    }

    function renderEpisodes(episodes) {
      state.episodes = episodes || [];
      $("episodeSelect").innerHTML = state.episodes.map((ep) => {
        const label = `${ep.name} (${ep.decisions} decisions)`;
        return `<option value="${escapeHtml(ep.path)}">${escapeHtml(label)}</option>`;
      }).join("");
    }

    function renderReplay(payload) {
      $("battleLibrary").hidden = true;
      $("replayHeading").hidden = false;
      $("visualizer").hidden = false;
      $("replayTitle").textContent = payload && payload.decisions ? "Episode review" : "Log replay";
      if (!payload || !payload.ok) {
        $("visualizer").innerHTML = `<div class="event-card"><strong>Visualizer error</strong><div class="event-detail">${escapeHtml((payload && payload.error) || "No replay data")}</div></div>`;
        return;
      }
      if (payload.events) renderLogReplay(payload);
      else if (payload.decisions) renderEpisodeReplay(payload);
      else $("visualizer").innerHTML = "<div class='event-card'>No visualizable data.</div>";
    }

    function renderLogReplay(payload) {
      state.replayPayload = payload;
      state.replayCursor = 0;
      renderLogReplayAtCursor();
    }

    function renderLogReplayAtCursor() {
      const payload = state.replayPayload || {};
      const events = payload.events || [];
      const snapshots = payload.snapshots || [];
      const cursor = events.length ? Math.max(0, Math.min(state.replayCursor, events.length - 1)) : -1;
      state.replayCursor = cursor;
      const visible = cursor >= 0 ? (snapshots[cursor] || {}) : {};
      const players = visible.players || {};
      const board = Object.entries(players).map(([name, p]) => renderPlayerBoard(name, p)).join("");
      const summary = `<table>${Object.entries(payload.summary || {}).map(([k, v]) => `<tr><th>${escapeHtml(k)}</th><td>${escapeHtml(typeof v === "object" ? JSON.stringify(v) : v)}</td></tr>`).join("")}</table>`;
      const coverage = `<table>${Object.entries(payload.coverage || {}).map(([k, v]) => `<tr><th>${escapeHtml(k)}</th><td>${escapeHtml(v)}</td></tr>`).join("")}</table>`;
      const timeline = events.map((ev, idx) => `
        <button type="button" class="event-card event-button ${idx === cursor ? "current" : ""} ${ev.action === "UNKNOWN" ? "unknown" : ""}" data-replay-index="${idx}">
          <div class="event-meta">
            <span>#${ev.index}</span>
            <span>${escapeHtml(ev.turn || "")}</span>
            <span>${escapeHtml(ev.player || "")}</span>
            <span class="event-action">${escapeHtml(ev.action || "")}</span>
          </div>
          <div class="event-raw">${escapeHtml(ev.raw || "")}</div>
          ${ev.detail ? `<div class="event-detail">${escapeHtml(ev.detail)}</div>` : ""}
        </button>
      `).join("");
      const unparsed = (payload.unparsed_lines || []).map((row) => `<div class="event-card unknown"><strong>Line ${escapeHtml(row.line)}</strong><div class="event-raw">${escapeHtml(row.text)}</div><div class="event-detail">${escapeHtml(row.reason)}</div></div>`).join("");
      $("visualizer").innerHTML = `
        <div class="replay-controls">
          <button id="replayFirstBtn" class="icon-button" type="button" title="First event" aria-label="First event">__ICON_chevrons-left__</button>
          <button id="replayPrevBtn" class="icon-button" type="button" title="Previous event" aria-label="Previous event">__ICON_chevron-left__</button>
          <input id="replayRange" type="range" aria-label="Replay event" min="0" max="${Math.max(0, events.length - 1)}" value="${Math.max(0, cursor)}">
          <span class="status good">${events.length ? `Event ${cursor + 1} / ${events.length}` : "No events"}</span>
          <button id="replayNextBtn" class="icon-button" type="button" title="Next event" aria-label="Next event">__ICON_chevron-right__</button>
          <button id="replayLastBtn" class="icon-button" type="button" title="Last event" aria-label="Last event">__ICON_chevrons-right__</button>
          <span class="status ${visible.winner ? "good" : "warn"}">Stadium: ${escapeHtml(visible.stadium || "None")}</span>
        </div>
        <div class="board-view">${board || "<div class='event-card'>No board inferred yet.</div>"}</div>
        <div class="timeline">${timeline || "<div class='event-card'>No events parsed.</div>"}</div>
        <details class="fold"><summary>Summary &amp; parsing coverage</summary><div class="fold-body grid"><div>${summary}</div><div>${coverage}</div></div></details>
        ${unparsed ? `<details class="fold"><summary>Unparsed lines</summary><div class="timeline fold-body">${unparsed}</div></details>` : ""}
      `;
      bindReplayControls(events.length);
    }

    function bindReplayControls(eventCount) {
      const seek = (index) => {
        state.replayCursor = Math.max(0, Math.min(index, Math.max(0, eventCount - 1)));
        renderLogReplayAtCursor();
      };
      $("replayFirstBtn").addEventListener("click", () => seek(0));
      $("replayPrevBtn").addEventListener("click", () => seek(state.replayCursor - 1));
      $("replayNextBtn").addEventListener("click", () => seek(state.replayCursor + 1));
      $("replayLastBtn").addEventListener("click", () => seek(eventCount - 1));
      $("replayRange").addEventListener("input", (event) => seek(Number(event.target.value)));
      document.querySelectorAll("[data-replay-index]").forEach((el) => {
        el.addEventListener("click", () => seek(Number(el.dataset.replayIndex)));
      });
    }

    function renderPlayerBoard(name, p) {
      const active = p.active ? `<span class="pill">${escapeHtml(p.active)}</span>` : `<span class="pill">Empty</span>`;
      const bench = (p.bench || []).map((c) => `<span class="pill">${escapeHtml(c)}</span>`).join("") || `<span class="pill">Empty</span>`;
      const attachments = Object.entries(p.attachments || {}).map(([target, cards]) => {
        return `<div><span class="zone-label">${escapeHtml(target)}</span><div class="pill-line">${(cards || []).map((c) => `<span class="pill">${escapeHtml(c)}</span>`).join("")}</div></div>`;
      }).join("") || `<span class="pill">None</span>`;
      const damage = Object.entries(p.damage || {}).map(([target, amount]) => `<span class="pill">${escapeHtml(target)}: ${escapeHtml(amount)} damage</span>`).join("") || `<span class="pill">None</span>`;
      const conditions = Object.entries(p.conditions || {}).map(([target, values]) => `<span class="pill">${escapeHtml(target)}: ${escapeHtml((values || []).join(", "))}</span>`).join("") || `<span class="pill">None</span>`;
      return `
        <div class="player-board">
          <h3>${escapeHtml(name)}</h3>
          <div class="zone"><span class="zone-label">Active</span><div class="pill-line">${active}</div></div>
          <div class="zone"><span class="zone-label">Bench</span><div class="pill-line">${bench}</div></div>
          <div class="zone"><span class="zone-label">Attachments</span>${attachments}</div>
          <div class="zone"><span class="zone-label">Damage</span><div class="pill-line">${damage}</div></div>
          <div class="zone"><span class="zone-label">Conditions</span><div class="pill-line">${conditions}</div></div>
          <div class="zone"><span class="zone-label">Known Hand / Count</span><div class="pill-line"><span class="pill">${escapeHtml((p.hand_known || []).join(", ") || "Hidden")} / ${escapeHtml(p.hand_count || 0)}</span></div></div>
          <div class="zone"><span class="zone-label">Prizes Taken</span><div class="pill-line"><span class="pill">${escapeHtml(p.prizes_taken || 0)}</span></div></div>
        </div>
      `;
    }

    function renderEpisodeReplay(payload) {
      const review = payload.review_url ? `<p><a href="${escapeHtml(payload.review_url)}" target="_blank" rel="noopener">Open battle review</a></p>` : "";
      const summary = `<table>${Object.entries(payload.summary || {}).map(([k, v]) => `<tr><th>${escapeHtml(k)}</th><td>${escapeHtml(typeof v === "object" ? JSON.stringify(v) : v)}</td></tr>`).join("")}</table>`;
      const decisions = (payload.decisions || []).map((d) => {
        const selected = new Set((d.selected_indexes || []).map((x) => Number(x)));
        const options = (d.legal_options || []).map((opt, idx) => {
          const cls = selected.has(idx) ? "event-card selected-option" : "event-card";
          return `<div class="${cls}"><strong>${idx}</strong> ${escapeHtml(shortText(opt))}</div>`;
        }).join("");
        return `
          <div class="event-card">
            <div class="event-meta">
              <span>#${d.index}</span>
              <span>turn ${escapeHtml(d.turn)}</span>
              <span>player ${escapeHtml(d.player)}</span>
              <span>${escapeHtml(d.agent_id || "")}</span>
            </div>
            <div class="decision-grid">
              <div><strong>Selected</strong><div class="event-detail">${escapeHtml(JSON.stringify(d.selected_indexes || []))}</div></div>
              <div><strong>Features</strong><div class="event-detail">${escapeHtml(JSON.stringify(d.features || {}, null, 2))}</div></div>
            </div>
            <div class="option-list">${options || "No legal options recorded."}</div>
          </div>
        `;
      }).join("");
      $("visualizer").innerHTML = `${review}${summary}<div class="timeline">${decisions || "<div class='event-card'>No decisions in episode.</div>"}</div>`;
    }

    function shortText(value) {
      if (value === null || value === undefined) return "";
      if (typeof value === "string") return value;
      try { return JSON.stringify(value); } catch { return String(value); }
    }

    async function refresh() {
      print("Refreshing...");
      const status = await getJson("/api/status");
      const ok = status.engine && status.engine.available;
      state.engineReady = Boolean(ok);
      $("engineBadge").textContent = ok ? "Engine ready" : "Engine offline";
      $("engineBadge").className = ok ? "status good" : "status warn";
      table($("envTable"), status.environment);
      table($("engineTable"), status.engine);
      table($("runtimeTable"), status.runtime);
      table($("replayEngineTable"), status.replay_engine);
      $("playBtn").disabled = !ok || state.busy;
      $("startEngineBtn").disabled = ok;
      $("stopEngineBtn").disabled = !ok;
      renderDecks(status.decks);
      renderAgents(status.agents);
      renderResults(status.results || {});
      print(status);
    }

    async function validateSelected() {
      const deck = $("deckA").value;
      const report = await postJson("/api/validate", { deck, agent: $("agentA").value, side: "a" });
      print(report);
      if (report.ok) $("activityStatus").textContent = `Deck A validated: ${report.card_count} supported cards.`;
    }

    function readFileBase64(file) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onerror = () => reject(reader.error || new Error("Could not read file"));
        reader.onload = () => resolve(String(reader.result || "").split(",", 2)[1] || "");
        reader.readAsDataURL(file);
      });
    }

    async function importAgent(side, file) {
      if (!file) return;
      const upper = side.toUpperCase();
      const deckSelect = $(`deck${upper}`);
      const defaultDeck = side === "a" ? "decks/deck_a.csv" : "decks/deck_b.csv";
      const fallbackDeck = deckSelect.value === "auto" ? defaultDeck : deckSelect.value;
      print(`Importing ${file.name}...`);
      try {
        const result = await postJson("/api/agents/import", {
          filename: file.name,
          name: file.name.replace(/\.(zip|py)$/i, ""),
          content_base64: await readFileBase64(file),
          deck: fallbackDeck
        });
        if (!result.ok) {
          print(result);
          return;
        }
        await refresh();
        $(`agent${upper}`).value = result.agent.spec;
        deckSelect.value = "auto";
        print(result);
        $("activityStatus").textContent = `${result.agent.name} imported for Agent ${upper}.`;
      } catch (error) {
        print({ ok: false, error: String(error) });
      }
    }

    async function runMatch() {
      if (state.busy) return;
      state.busy = true;
      $("playBtn").disabled = true;
      $("playBtn").textContent = "Battle running...";
      try {
        print("Starting match...");
        const result = await postJson("/api/play", {
          deck_a: $("deckA").value,
          deck_b: $("deckB").value,
          agent_a: $("agentA").value,
          agent_b: $("agentB").value,
          record: true
        });
        print(result);
        const latest = await getJson("/api/results");
        renderResults(latest);
        if (result.ok !== false && !result.error) $("activityStatus").textContent = "Battle complete.";
      } catch (error) {
        print({ok:false, error:String(error)});
      } finally {
        state.busy = false;
        $("playBtn").disabled = !state.engineReady;
        $("playBtn").innerHTML = `__ICON_play__ Run match`;
      }
    }

    async function engineAction(action) {
      $("startEngineBtn").disabled = true;
      $("stopEngineBtn").disabled = true;
      print(action === "start" ? "Starting official engine..." : "Stopping official engine...");
      try {
        const result = await postJson(`/api/engine/${action}`, {});
        await refresh();
        print(result);
      } finally {
        $("startEngineBtn").disabled = state.engineReady;
        $("stopEngineBtn").disabled = !state.engineReady;
      }
    }

    async function verifyEnvironment() {
      $("verifyEngineBtn").disabled = true;
      print("Running Kaggle cabt environment verification...");
      try {
        const result = await postJson("/api/engine/verify", {});
        print(result);
      } finally {
        $("verifyEngineBtn").disabled = false;
      }
    }

    async function loadEpisode() {
      const path = $("episodeSelect").value;
      if (!path) {
        renderReplay({ ok: false, error: "No episode selected." });
        return;
      }
      const payload = await getJson(`/api/episode?path=${encodeURIComponent(path)}`);
      print(payload);
      renderReplay(payload);
    }

    async function visualizeLog() {
      const payload = await postJson("/api/visualize-log", { text: $("logText").value });
      print(payload.summary || payload);
      renderReplay(payload);
    }

    $("logFile").addEventListener("change", async (event) => {
      const file = event.target.files && event.target.files[0];
      if (!file) return;
      $("logText").value = await file.text();
      await visualizeLog().catch(error => print({ok:false,error:String(error)}));
    });

    $("battleSearch").addEventListener("input", renderBattleList);
    $("backToBattles").addEventListener("click", () => { $("battleLibrary").hidden = false; $("replayHeading").hidden = true; $("visualizer").hidden = true; });
    $("engineBadge").addEventListener("click", () => { $("engineSettings").open = true; $("engineSettings").scrollIntoView({block:"nearest"}); });
    $("refreshBtn").addEventListener("click", () => refresh().catch(error => print({ok:false,error:String(error)})));
    const reportError = error => print({ok:false,error:String(error)});
    $("validateBtn").addEventListener("click", () => validateSelected().catch(reportError));
    $("playBtn").addEventListener("click", runMatch);
    $("startEngineBtn").addEventListener("click", () => engineAction("start").catch(reportError));
    $("stopEngineBtn").addEventListener("click", () => engineAction("stop").catch(reportError));
    $("verifyEngineBtn").addEventListener("click", () => verifyEnvironment().catch(reportError));
    $("agentFileA").addEventListener("change", (event) => importAgent("a", event.target.files && event.target.files[0]));
    $("agentFileB").addEventListener("change", (event) => importAgent("b", event.target.files && event.target.files[0]));
    $("loadEpisodeBtn").addEventListener("click", () => loadEpisode().catch(reportError));
    $("parseLogBtn").addEventListener("click", () => visualizeLog().catch(reportError));
    refresh().catch(error => print({ok:false,error:String(error)}));
  </script>
</body>
</html>
"""


INDEX_HTML = decorate_page(INDEX_HTML, "simulator")


if __name__ == "__main__":
    raise SystemExit(main())
