from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List

from core.strategy_scope import GENERIC_STRATEGY_ID, PALAKING_STRATEGY_ID, normalized_strategy_id, reset_strategy_scope_cache


PREFER_GOING_FIRST = True

DEFAULT_DECK_IDS = [
    105, 105, 105, 105, 904, 902, 902, 903, 903, 107,
    107, 107, 107, 106, 106, 106, 904, 122, 1086, 1086,
    1086, 1086, 1227, 1227, 1227, 1227, 1092, 1118, 1152, 1152,
    1152, 1152, 1123, 1129, 1182, 1182, 1097, 1198, 1198, 1262,
    1262, 1262, 1225, 1219, 1219, 1219, 1219, 1174, 1174, 1191,
    3, 3, 3, 3, 3, 3, 3, 4, 4, 4,
]

DEFAULT_PROFILE: Dict[str, Any] = {
    "strategy_id": PALAKING_STRATEGY_ID,
    "strategy_scope": "deck_specific",
    "archetype": "Palafin ex / Mega Dragonite ex water-lightning setup",
    "prefer_going_first": PREFER_GOING_FIRST,
    "preferred_going": "first" if PREFER_GOING_FIRST else "second",
    "main_attackers_names": ["Palafin ex", "Mega Dragonite ex"],
    "main_damage_dealers_names": ["Palafin ex", "Mega Dragonite ex"],
    "secondary_attackers_names": ["Palafin", "Tatsugiri"],
    "setup_basics_names": ["Finizen", "Dratini"],
    "support_pokemon_names": ["Tatsugiri"],
    "setup_priority_names": [
        "Buddy-Buddy Poffin",
        "Finizen",
        "Dratini",
        "Palafin",
        "Palafin ex",
        "Dragonair",
        "Mega Dragonite ex",
        "Poke Pad",
        "Lillie's Determination",
    ],
    "protected_cards_names": [
        "Palafin ex",
        "Mega Dragonite ex",
        "Finizen",
        "Dratini",
        "Secret Box",
        "Basic Water Energy",
        "Basic Lightning Energy",
    ],
    "conditionally_protected_cards_names": [
        "Palafin",
        "Dragonair",
        "Tatsugiri",
        "Surfing Beach",
        "Team Rocket's Petrel",
        "Lillie's Determination",
        "Crispin",
        "Hilda",
        "Kieran",
    ],
    "primary_attackers": [107, 904],
    "secondary_attackers": [106, 122],
    "main_damage_dealers": [107, 904],
    "setup_pokemon": [105, 902],
    "support_pokemon": [122],
    "draw_search_cards": [1086, 1152, 1227, 1219, 1092, 1118, 1123, 1129, 1097, 1198, 1225, 1191],
    "key_supporters": [1227, 1219, 1182, 1198, 1225, 1191],
    "key_items": [1086, 1152, 1118, 1092, 1123, 1129, 1097, 1174],
    "setup_priority": [1086, 105, 902, 106, 107, 903, 904, 1152, 1227],
    "evolution_priorities": [107, 106, 903, 904],
    "energy_ids": [3, 4],
    "protected_energy_ids": [3, 4],
    "energy_attachment_priorities": [107, 106, 904, 903, 902],
    "retreat_switch_priorities": [107, 904, 106, 122],
    "must_use_before_attack": [1086, 1152, 1227, 1219, 1092, 1198],
    "protected_cards": [107, 904, 105, 902, 1092, 3, 4],
    "conditionally_protected_cards": [106, 903, 122, 1262, 1219, 1227, 1198, 1225, 1191],
    "discard_freely": [],
    "bench_only_if_useful": [122],
    "avoid_benching": [],
    "avoid_discard_names": ["Palafin ex", "Mega Dragonite ex", "Finizen", "Dratini", "Secret Box"],
    "draw_keywords": ["draw", "shuffle your hand into your deck", "put cards from your deck into your hand"],
    "search_keywords": ["search your deck", "look at the top", "put it into your hand"],
    "energy_acceleration_keywords": ["attach a Basic Energy", "attach an Energy", "energy cards from your deck"],
    "prize_mapping": {
        "normal_1_prize_line": [105, 106, 902, 903, 122],
        "ex_2_prize_line": [107, 904],
        "high_risk_liabilities": [107, 904],
    },
    "matchup_notes": {},
    "conditional_rules": [
        "Use Buddy-Buddy Poffin whenever the Bench has room and Finizen targets are likely left in deck.",
        "Use Poké Pad or Hilda-style search for Dratini because Dratini is above the Poffin HP limit.",
        "Build Palafin ex first when the Finizen line is live, with Mega Dragonite ex as the second real damage dealer.",
        "Palafin ex should have exactly one useful Energy attached.",
        "Only Basic Water Energy should attach to the Finizen / Palafin / Palafin ex line.",
        "Reserve Basic Lightning Energy for the Dragonite line.",
        "Prefer Finizen in the opening Active Spot over the Dragonite line when both are legal.",
        "Use Air Balloon on active Palafin, attack-locked Palafin ex, or Tatsugiri when it enables a reset route.",
        "Do not attach Energy to Tatsugiri for retreat setup; use Air Balloon for Tatsugiri pivoting.",
        "Mega Dragonite ex should not pay a two-Energy retreat cost.",
        "If active Palafin ex can use Giga Impact, keep Mega Dragonite ex switch Ability low.",
        "If Palafin ex cannot use Giga Impact or normal Palafin needs Zero to Hero, raise Mega Dragonite ex switch Ability.",
        "After our Active is Knocked Out, if no attacker is ready on board, promote Finizen.",
        "Protect lone Finizen, Dratini, Dragonair, Palafin, and live next-turn evolution pieces.",
        "Use Tatsugiri's Attract Customers before spending a Supporter when Tatsugiri is Active.",
        "Before Lillie's Determination, check usable Items, legal evolution, Basics to Bench, useful Abilities, and Energy attachment.",
        "Before attacking or ending the turn, rerun the checklist for evolution, useful Items, Energy attachment, and unused Supporters unless an attack takes a clean Knock Out.",
    ],
}

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
    return list(DEFAULT_DECK_IDS)


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
    for path in [root / "deck_profile.json", Path(os.getcwd()) / "deck_profile.json", Path("/kaggle_simulations/agent/deck_profile.json")]:
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
        Path(os.getcwd()) / "deck.csv",
        Path("/kaggle_simulations/agent/deck.csv"),
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
