from __future__ import annotations

import csv
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable


NS_ZOROARK_STRATEGY_ID = "ns_zoroark"
GENERIC_STRATEGY_ID = "generic"

NS_ZOROARK_REQUIRED_IDS = {292, 293}
NS_ZOROARK_SIGNATURE_IDS = {
    7,
    112,
    140,
    141,
    257,
    258,
    292,
    293,
    303,
    689,
    906,
    1080,
    1086,
    1097,
    1113,
    1137,
    1152,
    1162,
    1174,
    1182,
    1188,
    1205,
    1211,
    1227,
    1253,
    1256,
}


def active_strategy_id(state: Any = None) -> str:
    del state
    profile = current_profile_json()
    declared = normalized_strategy_id(profile.get("strategy_id") or profile.get("deck_strategy") or profile.get("strategy"))
    deck_ids = current_deck_ids()
    if declared in {"none", "off", "disabled", GENERIC_STRATEGY_ID}:
        return GENERIC_STRATEGY_ID
    if declared == NS_ZOROARK_STRATEGY_ID or profile_looks_ns_zoroark(profile):
        return NS_ZOROARK_STRATEGY_ID if (not deck_ids or deck_matches_ns_zoroark(deck_ids)) else GENERIC_STRATEGY_ID
    return GENERIC_STRATEGY_ID


def use_ns_zoroark_strategy(state: Any = None) -> bool:
    if active_strategy_id(None) != NS_ZOROARK_STRATEGY_ID:
        return False
    if state is None:
        return True
    return state_looks_ns_zoroark(state)


def deck_matches_ns_zoroark(deck_ids: Iterable[int]) -> bool:
    ids = [int(cid) for cid in deck_ids if _is_int_like(cid)]
    if not ids:
        return False
    deck_set = set(ids)
    if not NS_ZOROARK_REQUIRED_IDS <= deck_set:
        return False
    signature_count = sum(1 for cid in ids if cid in NS_ZOROARK_SIGNATURE_IDS)
    return signature_count >= 18


def profile_looks_ns_zoroark(profile: dict[str, Any]) -> bool:
    text = " ".join(str(profile.get(key, "")) for key in ("archetype", "name", "deck_name", "strategy_name")).lower()
    if "zoroark" in text and ("n's" in text or "n’s" in text or "zekrom" in text):
        return True
    names = []
    for key in ("main_attackers_names", "main_damage_dealers_names", "setup_basics_names", "copy_sources_names"):
        value = profile.get(key, [])
        if isinstance(value, list):
            names.extend(str(item).lower() for item in value)
    joined = " ".join(names)
    return "zoroark" in joined and "zekrom" in joined


def state_looks_ns_zoroark(state: Any) -> bool:
    current = _getv(state, "current")
    if current is None:
        return True
    player = _our_player_state(state, current)
    if player is None:
        return True

    in_play_ids = _ids_from_list(_getv(player, "active", [])) + _ids_from_list(_getv(player, "bench", []))
    if any(cid in NS_ZOROARK_SIGNATURE_IDS for cid in in_play_ids):
        return True
    if in_play_ids:
        return False

    hand_ids = _ids_from_list(_getv(player, "hand", []))
    discard_ids = _ids_from_list(_getv(player, "discard", []))
    known_ids = hand_ids + discard_ids
    return not known_ids or any(cid in NS_ZOROARK_SIGNATURE_IDS for cid in known_ids)


def normalized_strategy_id(value: Any) -> str:
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "n_zoroark": NS_ZOROARK_STRATEGY_ID,
        "ns_zoroark_ex": NS_ZOROARK_STRATEGY_ID,
        "n_s_zoroark": NS_ZOROARK_STRATEGY_ID,
        "n's_zoroark": NS_ZOROARK_STRATEGY_ID,
        "n’s_zoroark": NS_ZOROARK_STRATEGY_ID,
        "n_zoroark_ex": NS_ZOROARK_STRATEGY_ID,
        "n's_zoroark_ex": NS_ZOROARK_STRATEGY_ID,
        "n’s_zoroark_ex": NS_ZOROARK_STRATEGY_ID,
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
    return _unique_paths([cwd / "deck_profile.json", root / "deck_profile.json", Path("/kaggle_simulations/agent/deck_profile.json")])


def _deck_paths() -> list[Path]:
    root = Path(__file__).resolve().parents[1]
    cwd = Path.cwd()
    return _unique_paths([cwd / "deck.csv", root / "deck.csv", Path("/kaggle_simulations/agent/deck.csv")])


def _unique_paths(paths: Iterable[Path]) -> list[Path]:
    result = []
    seen = set()
    for path in paths:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return result


def _is_int_like(value: Any) -> bool:
    try:
        int(value)
        return True
    except Exception:
        return False


def _our_player_state(state: Any, current: Any) -> Any:
    players = _getv(current, "players", [])
    if not isinstance(players, list):
        return None
    idx = _getv(state, "your_index", None)
    if idx is None:
        idx = _getv(current, "yourIndex", 0)
    try:
        idx = int(idx)
    except Exception:
        idx = 0
    return players[idx] if 0 <= idx < len(players) else None


def _ids_from_list(values: Any) -> list[int]:
    if not isinstance(values, list):
        return []
    result = []
    for value in values:
        cid = _card_id(value)
        if cid is not None:
            result.append(cid)
    return result


def _card_id(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, dict):
        for key in ("id", "cardId", "card_id", "card"):
            cid = _card_id(value.get(key))
            if cid is not None:
                return cid
    try:
        return int(value)
    except Exception:
        return None


def _getv(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)
