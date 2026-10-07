from __future__ import annotations

import csv
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable


PALAKING_STRATEGY_ID = "palfingon"
GENERIC_STRATEGY_ID = "generic"

PALAKING_REQUIRED_IDS = {105, 106, 107, 902, 904}
PALAKING_SIGNATURE_IDS = {
    51,
    1213,
    1264,
    105,
    106,
    107,
    122,
    902,
    903,
    904,
    1086,
    1092,
    1118,
    1123,
    1152,
    1174,
    1182,
    1198,
    1219,
    1225,
    1227,
    1262,
    3,
    4,
}


def active_strategy_id(state: Any = None) -> str:
    del state
    profile = current_profile_json()
    declared = normalized_strategy_id(profile.get("strategy_id") or profile.get("deck_strategy") or profile.get("strategy"))
    deck_ids = current_deck_ids()
    if declared in {"none", "off", "disabled", GENERIC_STRATEGY_ID}:
        return GENERIC_STRATEGY_ID
    if declared == PALAKING_STRATEGY_ID or profile_looks_palaking(profile):
        return PALAKING_STRATEGY_ID if (not deck_ids or deck_matches_palaking(deck_ids)) else GENERIC_STRATEGY_ID
    return GENERIC_STRATEGY_ID


def use_palaking_strategy(state: Any = None) -> bool:
    if active_strategy_id(None) != PALAKING_STRATEGY_ID:
        return False
    if state is None:
        return True
    return state_looks_palaking(state)


def deck_matches_palaking(deck_ids: Iterable[int]) -> bool:
    ids = [int(cid) for cid in deck_ids if _is_int_like(cid)]
    if not ids:
        return False
    deck_set = set(ids)
    if not PALAKING_REQUIRED_IDS <= deck_set:
        return False
    signature_count = sum(1 for cid in ids if cid in PALAKING_SIGNATURE_IDS)
    return signature_count >= 20


def profile_looks_palaking(profile: dict[str, Any]) -> bool:
    text = " ".join(str(profile.get(key, "")) for key in ("archetype", "name", "deck_name", "strategy_name")).lower()
    if "palafin" in text and "dragonite" in text:
        return True
    names = []
    for key in ("main_attackers_names", "main_damage_dealers_names", "setup_basics_names"):
        value = profile.get(key, [])
        if isinstance(value, list):
            names.extend(str(item).lower() for item in value)
    joined = " ".join(names)
    return "palafin ex" in joined and "mega dragonite ex" in joined


def state_looks_palaking(state: Any) -> bool:
    current = _getv(state, "current")
    if current is None:
        return True
    player = _our_player_state(state, current)
    if player is None:
        return True

    in_play_ids = _ids_from_list(_getv(player, "active", [])) + _ids_from_list(_getv(player, "bench", []))
    palaking_pokemon = {51, 105, 106, 107, 122, 902, 903, 904}
    if any(cid in palaking_pokemon for cid in in_play_ids):
        return True
    if in_play_ids:
        return False

    hand_ids = _ids_from_list(_getv(player, "hand", []))
    discard_ids = _ids_from_list(_getv(player, "discard", []))
    known_ids = hand_ids + discard_ids
    return not known_ids or any(cid in PALAKING_SIGNATURE_IDS for cid in known_ids)


def normalized_strategy_id(value: Any) -> str:
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "palafin_dragonite": PALAKING_STRATEGY_ID,
        "palafin_ex_mega_dragonite_ex": PALAKING_STRATEGY_ID,
        "palafin_ex_dragonite_ex": PALAKING_STRATEGY_ID,
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
    return [root / "deck_profile.json"]


def _deck_paths() -> list[Path]:
    root = Path(__file__).resolve().parents[1]
    return [root / "deck.csv"]


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
