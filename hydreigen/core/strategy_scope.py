from __future__ import annotations

import csv
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Optional


HYDREIGON_GENGAR_STRATEGY_ID = "hydreigon_mega_gengar"
GENERIC_STRATEGY_ID = "generic"

HYDREIGON_GENGAR_REQUIRED_IDS = {227, 229, 59, 772}
HYDREIGON_GENGAR_SIGNATURE_IDS = {227, 228, 229, 59, 771, 772, 833, 834, 140, 141}


def active_strategy_id(state: Any = None) -> str:
    del state
    profile = current_profile_json()
    declared = normalized_strategy_id(profile.get("strategy_id") or profile.get("deck_strategy") or profile.get("strategy"))
    deck_matches = deck_matches_hydreigon_gengar(current_deck_ids())

    if declared in {"none", "off", "disabled", GENERIC_STRATEGY_ID}:
        return GENERIC_STRATEGY_ID
    if declared == HYDREIGON_GENGAR_STRATEGY_ID:
        return HYDREIGON_GENGAR_STRATEGY_ID if deck_matches else GENERIC_STRATEGY_ID
    if profile_looks_hydreigon_gengar(profile):
        return HYDREIGON_GENGAR_STRATEGY_ID if deck_matches else GENERIC_STRATEGY_ID
    return GENERIC_STRATEGY_ID


def use_hydreigon_gengar_strategy(state: Any = None) -> bool:
    return active_strategy_id(state) == HYDREIGON_GENGAR_STRATEGY_ID


def deck_matches_hydreigon_gengar(deck_ids: Iterable[int]) -> bool:
    ids = [int(cid) for cid in deck_ids if _is_int_like(cid)]
    if not ids:
        return False
    deck_set = set(ids)
    if not HYDREIGON_GENGAR_REQUIRED_IDS <= deck_set:
        return False
    signature_count = sum(1 for cid in ids if cid in HYDREIGON_GENGAR_SIGNATURE_IDS)
    return signature_count >= 10


def profile_looks_hydreigon_gengar(profile: dict[str, Any]) -> bool:
    text = " ".join(
        str(profile.get(key, ""))
        for key in ("archetype", "name", "deck_name", "strategy_name")
    ).lower()
    if "hydreigon" in text and "gengar" in text:
        return True
    names = []
    for key in ("main_attackers_names", "main_damage_dealers_names", "setup_basics_names"):
        value = profile.get(key, [])
        if isinstance(value, list):
            names.extend(str(item).lower() for item in value)
    joined = " ".join(names)
    return "hydreigon ex" in joined and "mega gengar ex" in joined


def profile_is_hydreigon_specific(profile: dict[str, Any]) -> bool:
    declared = normalized_strategy_id(profile.get("strategy_id") or profile.get("deck_strategy") or profile.get("strategy"))
    return declared == HYDREIGON_GENGAR_STRATEGY_ID or profile_looks_hydreigon_gengar(profile)


def normalized_strategy_id(value: Any) -> str:
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "hydreigon_gengar": HYDREIGON_GENGAR_STRATEGY_ID,
        "hydreigon_ex_mega_gengar_ex": HYDREIGON_GENGAR_STRATEGY_ID,
        "hydreigon_ex_gengar_ex": HYDREIGON_GENGAR_STRATEGY_ID,
        "general": GENERIC_STRATEGY_ID,
        "default": GENERIC_STRATEGY_ID,
    }
    return aliases.get(text, text)


@lru_cache(maxsize=1)
def current_profile_json() -> dict[str, Any]:
    for path in _profile_paths():
        if not path.exists():
            continue
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


@lru_cache(maxsize=1)
def current_deck_ids() -> tuple[int, ...]:
    for path in _deck_paths():
        if not path.exists():
            continue
        try:
            with path.open("r", encoding="utf-8", newline="") as handle:
                rows = [row for row in csv.reader(handle) if row]
            ids = []
            for row in rows:
                value = str(row[0]).strip()
                if value and value.isdigit():
                    ids.append(int(value))
            if len(ids) == 60:
                return tuple(ids)
        except Exception:
            continue
    return ()


def reset_strategy_scope_cache() -> None:
    current_profile_json.cache_clear()
    current_deck_ids.cache_clear()


def _profile_paths() -> list[Path]:
    root = Path(__file__).resolve().parents[1]
    cwd = Path.cwd()
    paths = [
        cwd / "deck_profile.json",
        root / "deck_profile.json",
        Path("/kaggle_simulations/agent/deck_profile.json"),
    ]
    return _unique_paths(paths)


def _deck_paths() -> list[Path]:
    root = Path(__file__).resolve().parents[1]
    cwd = Path.cwd()
    paths = [
        cwd / "deck.csv",
        root / "deck.csv",
        Path("/kaggle_simulations/agent/deck.csv"),
    ]
    return _unique_paths(paths)


def _unique_paths(paths: Iterable[Path]) -> list[Path]:
    result = []
    seen = set()
    for path in paths:
        resolved = str(path)
        if resolved in seen:
            continue
        seen.add(resolved)
        result.append(path)
    return result


def _is_int_like(value: Any) -> bool:
    try:
        int(value)
        return True
    except Exception:
        return False
