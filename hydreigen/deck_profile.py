from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List

from core.strategy_scope import (
    GENERIC_STRATEGY_ID,
    HYDREIGON_GENGAR_STRATEGY_ID,
    deck_matches_hydreigon_gengar,
    normalized_strategy_id,
    profile_is_hydreigon_specific,
    reset_strategy_scope_cache,
)


PREFER_GOING_FIRST = True

MAIN_ATTACKERS = ["Mega Gengar ex", "Hydreigon ex"]
SECONDARY_ATTACKERS = []
SETUP_BASICS = ["Deino", "Gastly", "Toxel"]
SUPPORT_POKEMON = ["Fezandipiti ex", "Pecharunt ex"]
MAIN_DAMAGE_DEALERS = ["Mega Gengar ex", "Hydreigon ex"]
PRIZE_EXCHANGE_ENGINE = ["Mega Gengar ex"]
ENERGY_ENGINE = ["Toxtricity"]
ENERGY_ENGINE_BASICS = ["Toxel"]
SETUP_PRIORITY = [
    "Buddy-Buddy Poffin",
    "Lillie's Determination",
    "Ultra Ball",
    "Rare Candy",
    "Mega Gengar ex",
    "Hydreigon ex",
    "Deino",
]
PROTECTED_CARDS = [
    "Hydreigon ex",
    "Deino",
    "Rare Candy",
    "Mega Gengar ex",
    "Gastly",
    "Secret Box",
    "Boss's Orders",
    "Special Red Card",
    "Night Stretcher",
    "Sacred Ash",
    "Energy Recycler",
    "Basic Metal Energy",
    "Basic Psychic Energy",
]
CONDITIONALLY_PROTECTED_CARDS = [
    "Fezandipiti ex",
    "Pecharunt ex",
    "Toxtricity",
    "Toxel",
    "Crispin",
    "Team Rocket's Petrel",
    "Lillie's Determination",
]
DISCARD_FIRST_CANDIDATES = [
    "extra Battle Cage after stadium is already in play",
    "extra Air Balloon if switching is already covered",
    "extra Poké Pad after supporter access is stable",
    "extra Team Rocket's Petrel when disruption is not immediately useful",
    "extra Lillie's Determination if already used/held enough draw",
    "extra basic Pokémon after board is fully set",
    "extra Darkness Energy if Energy Recycler is still available",
]
DO_NOT_BENCH_WITHOUT_REASON = [
    "Fezandipiti ex",
    "Pecharunt ex",
    "extra Mega Gengar ex",
]

DEFAULT_DECK_IDS = [
    228,
    227,
    227,
    227,
    229,
    229,
    229,
    140,
    772,
    833,
    833,
    771,
    834,
    834,
    59,
    59,
    141,
    772,
    1092,
    1231,
    1231,
    1264,
    1264,
    1139,
    1121,
    1121,
    1103,
    1152,
    1152,
    1152,
    1227,
    1227,
    1227,
    1227,
    1129,
    1097,
    1198,
    1198,
    1219,
    1219,
    1219,
    1086,
    1086,
    1086,
    1174,
    1174,
    1182,
    1079,
    1079,
    1079,
    7,
    7,
    7,
    7,
    7,
    7,
    8,
    8,
    5,
    5,
]


DEFAULT_PROFILE: Dict[str, Any] = {
    "strategy_id": HYDREIGON_GENGAR_STRATEGY_ID,
    "strategy_scope": "deck_specific",
    "archetype": "Hydreigon ex / Mega Gengar ex setup",
    "prefer_going_first": PREFER_GOING_FIRST,
    "preferred_going": "first" if PREFER_GOING_FIRST else "second",
    "main_attackers_names": MAIN_ATTACKERS,
    "main_damage_dealers_names": MAIN_DAMAGE_DEALERS,
    "prize_exchange_engine_names": PRIZE_EXCHANGE_ENGINE,
    "energy_engine_names": ENERGY_ENGINE,
    "energy_engine_basics_names": ENERGY_ENGINE_BASICS,
    "secondary_attackers_names": SECONDARY_ATTACKERS,
    "setup_basics_names": SETUP_BASICS,
    "support_pokemon_names": SUPPORT_POKEMON,
    "setup_priority_names": SETUP_PRIORITY,
    "protected_cards_names": PROTECTED_CARDS,
    "conditionally_protected_cards_names": CONDITIONALLY_PROTECTED_CARDS,
    "discard_first_candidates": DISCARD_FIRST_CANDIDATES,
    "do_not_bench_without_reason": DO_NOT_BENCH_WITHOUT_REASON,
    "primary_attackers": [772, 229],
    "secondary_attackers": [],
    "main_damage_dealers": [772, 229],
    "prize_exchange_engine": [772],
    "energy_engine": [834],
    "energy_engine_basics": [833],
    "setup_pokemon": [227, 59, 833],
    "support_pokemon": [140, 141],
    "draw_search_cards": [1086, 1121, 1152, 1227, 1231, 1092, 1198],
    "key_supporters": [1227, 1231, 1198, 1219, 1182],
    "key_items": [1086, 1121, 1079, 1092, 1152, 1139, 1129, 1097, 1103],
    "setup_priority": [1086, 1227, 1121, 1079, 772, 229, 227],
    "evolution_priorities": [772, 229, 834, 771, 228],
    "energy_ids": [7, 8, 5],
    "darkness_energy_ids": [7],
    "protected_energy_ids": [8, 5],
    "energy_attachment_priorities": [229, 228, 227, 772, 771, 59],
    "retreat_switch_priorities": [229, 772, 834, 141, 140],
    "must_use_before_attack": [1086, 1121, 1079, 1198, 1227],
    "protected_cards": [229, 227, 1079, 772, 59, 1092, 1182, 1103, 1097, 1129, 1139, 8, 5],
    "conditionally_protected_cards": [140, 141, 834, 833, 1198, 1219, 1227],
    "discard_freely": [7],
    "bench_only_if_useful": [140, 141, 772],
    "avoid_benching": [140, 141],
    "avoid_discard_names": ["Hydreigon ex", "Rare Candy", "Secret Box", "Boss"],
    "draw_keywords": ["draw", "shuffle your hand into your deck", "put cards from your deck into your hand"],
    "search_keywords": ["search your deck", "look at the top", "put it into your hand"],
    "energy_acceleration_keywords": ["attach a Basic Energy", "attach an Energy", "energy cards from your deck"],
    "prize_mapping": {
        "normal_1_prize_line": [227, 228, 59, 771, 833, 834],
        "ex_2_prize_line": [229, 140, 141],
        "high_risk_liabilities": [140, 141, 772],
    },
    "matchup_notes": {},
    "conditional_rules": [
        "If a legal attack can take a knockout, take it unless a gust line wins more prizes immediately.",
        "Early game: prioritize Buddy-Buddy Poffin for Deino, Gastly, and Toxel.",
        "Get at least two Deino in play when possible before benching support ex liabilities.",
        "Build whichever attacker line is live first: Mega Gengar ex through Gastly/Haunter or Hydreigon ex through Deino/Rare Candy.",
        "Use Mega Gengar ex as a real damage dealer and prize-exchange engine, not only as a backup.",
        "Preserve recovery, switch cards, and non-Darkness energy against control or stall.",
        "Use disruption late when it protects the prize route or reduces comeback potential.",
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
    "prize_exchange_engine_names": [],
    "energy_engine_names": [],
    "energy_engine_basics_names": [],
    "secondary_attackers_names": [],
    "setup_basics_names": [],
    "support_pokemon_names": [],
    "setup_priority_names": [],
    "protected_cards_names": [],
    "conditionally_protected_cards_names": [],
    "discard_first_candidates": [],
    "do_not_bench_without_reason": [],
    "primary_attackers": [],
    "secondary_attackers": [],
    "main_damage_dealers": [],
    "prize_exchange_engine": [],
    "energy_engine": [],
    "energy_engine_basics": [],
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
        if _should_use_hydreigon_profile(user_profile):
            profile = deepcopy(DEFAULT_PROFILE)
            if user_profile:
                _deep_update(profile, user_profile)
        else:
            profile = deepcopy(GENERIC_PROFILE)
            if user_profile and not profile_is_hydreigon_specific(user_profile):
                _deep_update(profile, user_profile)
        _PROFILE = profile
    return _PROFILE


def _should_use_hydreigon_profile(user_profile: Dict[str, Any]) -> bool:
    deck_ids = _deck_ids_without_profile()
    deck_matches = deck_matches_hydreigon_gengar(deck_ids or DEFAULT_DECK_IDS)
    declared = normalized_strategy_id(user_profile.get("strategy_id") or user_profile.get("deck_strategy") or user_profile.get("strategy"))
    if declared in {GENERIC_STRATEGY_ID, "none", "off", "disabled"}:
        return False
    if declared == HYDREIGON_GENGAR_STRATEGY_ID:
        return deck_matches
    if user_profile:
        return profile_is_hydreigon_specific(user_profile) and deck_matches
    return deck_matches


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
        root / "sample_submission" / "deck.csv",
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
