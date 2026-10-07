from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List

from core.strategy_scope import GENERIC_STRATEGY_ID, PALAKING_STRATEGY_ID, normalized_strategy_id, reset_strategy_scope_cache


PREFER_GOING_FIRST = True

DEFAULT_PROFILE: Dict[str, Any] = {"strategy_id": PALAKING_STRATEGY_ID}

GENERIC_PROFILE: Dict[str, Any] = {
    "strategy_id": GENERIC_STRATEGY_ID,
    "strategy_scope": "general",
    "archetype": "Generic legal-action baseline",
    "prefer_going_first": False,
    "preferred_going": "second",
    "main_attackers_names": [],
    "main_damage_dealers_names": [],
    "secondary_attackers_names": [],
    "setup_basics_names": [],
    "support_pokemon_names": [],
    "setup_priority_names": [],
    "protected_cards_names": [],
    "conditionally_protected_cards_names": [],
    "primary_attackers": [],
    "secondary_attackers": [],
    "main_damage_dealers": [],
    "setup_pokemon": [],
    "support_pokemon": [],
    "draw_search_cards": [],
    "key_supporters": [],
    "key_items": [],
    "setup_priority": [],
    "evolution_priorities": [],
    "energy_ids": [],
    "protected_energy_ids": [],
    "energy_attachment_priorities": [],
    "retreat_switch_priorities": [],
    "must_use_before_attack": [],
    "protected_cards": [],
    "conditionally_protected_cards": [],
    "discard_freely": [],
    "bench_only_if_useful": [],
    "avoid_benching": [],
    "avoid_discard_names": [],
    "draw_keywords": ["draw", "shuffle your hand into your deck", "put cards from your deck into your hand"],
    "search_keywords": ["search your deck", "look at the top", "put it into your hand"],
    "energy_acceleration_keywords": ["attach a Basic Energy", "attach an Energy", "energy cards from your deck"],
    "prize_mapping": {
        "normal_1_prize_line": [],
        "ex_2_prize_line": [],
        "high_risk_liabilities": [],
    },
    "matchup_notes": {},
    "conditional_rules": [],
}

_PROFILE: Dict[str, Any] | None = None


def load_profile() -> Dict[str, Any]:
    global _PROFILE
    if _PROFILE is None:
        user_profile = _read_json_profile()
        declared = normalized_strategy_id(user_profile.get("strategy_id") or user_profile.get("deck_strategy") or user_profile.get("strategy"))
        if declared in {GENERIC_STRATEGY_ID, "none", "off", "disabled"}:
            profile = deepcopy(GENERIC_PROFILE)
        else:
            profile = deepcopy(DEFAULT_PROFILE)
            if user_profile:
                _deep_update(profile, user_profile)
        _PROFILE = profile
    return _PROFILE


def reset_profile_cache() -> None:
    global _PROFILE
    _PROFILE = None
    reset_strategy_scope_cache()


def _deck_ids_without_profile() -> List[int]:
    for path in _deck_paths():
        if not path.exists():
            continue
        try:
            with path.open("r", encoding="utf-8") as handle:
                deck = [int(line.strip().split(",")[0]) for line in handle if line.strip()]
            if len(deck) == 60:
                return deck
        except Exception:
            continue
    return []


def load_deck_ids() -> List[int]:
    for path in _deck_paths():
        if not path.exists():
            continue
        try:
            with path.open("r", encoding="utf-8") as handle:
                deck = [int(line.strip()) for line in handle if line.strip()]
            if len(deck) == 60:
                return deck
        except Exception:
            continue
    return []


def list_value(name: str) -> List[int]:
    value = load_profile().get(name, [])
    if isinstance(value, list):
        return [int(v) for v in value if _is_int_like(v)]
    return []


def card_priority(card_id: int, key: str, default: float = 0.0) -> float:
    values = list_value(key)
    if card_id not in values:
        return default
    return float(len(values) - values.index(card_id))


def _read_json_profile() -> Dict[str, Any]:
    root = Path(__file__).resolve().parent
    for path in [root / "deck_profile.json"]:
        if not path.exists():
            continue
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


def _deck_paths() -> List[Path]:
    root = Path(__file__).resolve().parent
    return [
        root / "deck.csv",
    ]


def _deep_update(base: Dict[str, Any], override: Dict[str, Any]) -> None:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_update(base[key], value)
        else:
            base[key] = value


def _is_int_like(value: Any) -> bool:
    try:
        int(value)
        return True
    except (TypeError, ValueError):
        return False
