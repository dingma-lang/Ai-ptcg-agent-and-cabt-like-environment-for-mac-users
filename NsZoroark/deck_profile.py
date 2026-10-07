from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List

from core.strategy_scope import GENERIC_STRATEGY_ID, NS_ZOROARK_STRATEGY_ID, normalized_strategy_id, reset_strategy_scope_cache


PREFER_GOING_FIRST = True

DEFAULT_DECK_IDS = [
    292, 292, 292, 292, 293, 293, 293, 293, 906, 906,
    112, 112, 257, 258, 303, 689, 141, 140, 1227, 1227,
    1227, 1227, 1205, 1205, 1205, 1182, 1182, 1182, 1188, 1188,
    1211, 1086, 1086, 1086, 1086, 1152, 1152, 1152, 1152, 1113,
    1113, 1113, 1097, 1097, 1137, 1080, 1162, 1162, 1174, 1253,
    1253, 1256, 7, 7, 7, 7, 7, 7, 7, 7,
]

DEFAULT_PROFILE: Dict[str, Any] = {
    "strategy_id": NS_ZOROARK_STRATEGY_ID,
    "strategy_scope": "deck_specific",
    "archetype": "N's Zoroark ex Night Joker toolbox",
    "prefer_going_first": PREFER_GOING_FIRST,
    "preferred_going": "first" if PREFER_GOING_FIRST else "second",
    "main_attackers_names": ["N's Zoroark ex"],
    "main_damage_dealers_names": ["N's Zoroark ex"],
    "secondary_attackers_names": [],
    "copy_sources_names": ["N's Zekrom", "N's Darmanitan", "N's Reshiram", "N's Darumaka"],
    "setup_basics_names": ["N's Zorua", "N's Zekrom", "N's Darumaka", "N's Reshiram", "Yveltal", "Munkidori"],
    "support_pokemon_names": ["Fezandipiti ex", "Pecharunt ex", "Munkidori"],
    "setup_priority_names": [
        "Buddy-Buddy Poffin",
        "N's Zorua",
        "N's Zoroark ex",
        "N's Zekrom",
        "N's Reshiram",
        "Poke Pad",
        "Lillie's Determination",
        "N's PP Up",
        "N's Castle",
        "Ciphermaniac's Codebreaking",
    ],
    "protected_cards_names": [
        "N's Zoroark ex",
        "N's Zorua",
        "N's Zekrom",
        "N's Reshiram",
        "N's PP Up",
        "N's Castle",
        "Darkness Energy",
    ],
    "conditionally_protected_cards_names": [
        "N's Darumaka",
        "N's Darmanitan",
        "Fezandipiti ex",
        "Pecharunt ex",
        "Binding Mochi",
        "Boss's Orders",
        "Black Belt's Training",
        "Cyrano",
        "Ciphermaniac's Codebreaking",
        "Unfair Stamp",
        "Tool Scrapper",
        "Night Stretcher",
        "Air Balloon",
        "Team Rocket's Watchtower",
    ],
    "primary_attackers": [293],
    "secondary_attackers": [],
    "copy_sources": [906, 258, 303, 257],
    "main_damage_dealers": [293],
    "setup_pokemon": [292, 906, 303, 257, 689, 112],
    "support_pokemon": [140, 141, 112],
    "draw_search_cards": [1086, 1152, 1227, 1205, 1188, 1113, 1097, 1080],
    "key_supporters": [1227, 1182, 1205, 1188, 1211],
    "key_items": [1086, 1113, 1097, 1152, 1080, 1137, 1162, 1174],
    "setup_priority": [1086, 292, 293, 906, 303, 1152, 1227, 1113, 1253],
    "evolution_priorities": [293, 258],
    "energy_ids": [7],
    "darkness_energy_ids": [7],
    "protected_energy_ids": [7],
    "energy_attachment_priorities": [293, 292],
    "retreat_switch_priorities": [293],
    "must_use_before_attack": [1086, 1152, 1113, 1253, 1227, 1188],
    "protected_cards": [293, 292, 906, 303, 1113, 1253, 7],
    "conditionally_protected_cards": [257, 258, 112, 140, 141, 1162, 1174, 1182, 1188, 1211, 1205, 1097, 1080],
    "discard_freely": [],
    "bench_only_if_useful": [140, 141],
    "avoid_benching": [],
    "avoid_discard_names": ["N's Zoroark ex", "N's Zorua", "N's Zekrom", "N's Reshiram", "N's PP Up"],
    "draw_keywords": ["draw", "shuffle your hand into your deck", "put cards from your deck into your hand"],
    "search_keywords": ["search your deck", "look at the top", "put it into your hand"],
    "energy_acceleration_keywords": ["attach a Basic Energy", "attach an Energy", "energy cards from your deck"],
    "prize_mapping": {
        "normal_1_prize_line": [292, 257, 258, 303, 689, 112],
        "ex_2_prize_line": [293, 140, 141],
        "high_risk_liabilities": [140, 141],
    },
    "matchup_notes": {},
    "conditional_rules": [
        "Use Buddy-Buddy Poffin early for N's Zorua; in this list Poffin usually cannot get the other Basics because they are over 70 HP.",
        "Prioritize N's Zorua into N's Zoroark ex, then keep useful N's Pokemon on the Bench only so Night Joker has attacks to copy.",
        "Use N's Reshiram as an additional Night Joker copy source; Powerful Rage scales from damage counters on the attacking Zoroark.",
        "Use N's PP Up to accelerate Darkness Energy only to Benched N's Zorua or N's Zoroark ex.",
        "Use N's Castle when retreat cost blocks a Zoroark or copy-source attack line.",
        "Use Lillie's Determination when the hand is low quality or overloaded with pieces that should be back in deck.",
        "Use Boss's Orders only for a clean KO or prize-map improvement.",
        "Use Ciphermaniac's Codebreaking when Trade or another draw will convert stacked cards into the hand.",
        "Avoid Team Rocket's Watchtower while our Zoroark, Pecharunt, Fezandipiti, or Munkidori Abilities still matter.",
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
    "copy_sources_names": [],
    "setup_basics_names": [],
    "support_pokemon_names": [],
    "setup_priority_names": [],
    "protected_cards_names": [],
    "conditionally_protected_cards_names": [],
    "primary_attackers": [],
    "secondary_attackers": [],
    "copy_sources": [],
    "main_damage_dealers": [],
    "setup_pokemon": [],
    "support_pokemon": [],
    "draw_search_cards": [],
    "key_supporters": [],
    "key_items": [],
    "setup_priority": [],
    "evolution_priorities": [],
    "energy_ids": [],
    "darkness_energy_ids": [],
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
