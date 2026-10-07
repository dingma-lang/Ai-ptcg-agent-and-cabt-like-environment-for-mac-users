from deck_profile import card_priority, list_value, load_deck_ids, load_profile
from functools import lru_cache

PRIMARY_ATTACKERS = ["Palafin ex"]
MAIN_ATTACKERS = PRIMARY_ATTACKERS
MAIN_DAMAGE_DEALERS = ["Palafin ex", "Mega Dragonite ex"]
SECONDARY_ATTACKERS = ["Mega Dragonite ex", "Palafin TEF 49"]

SETUP_BASICS = ["Finizen", "Dratini", "Tatsugiri"]
PALAFIN_LINE = ["Finizen", "Palafin", "Palafin ex"]
DRAGONITE_LINE = ["Dratini", "Dragonair", "Mega Dragonite ex"]
SWITCH_CARDS = ["Surfing Beach", "Switch", "Air Balloon"]
SEARCH_CARDS = ["Buddy-Buddy Poffin", "Poké Pad", "Team Rocket's Petrel", "Secret Box", "Hilda"]

ENERGY_PLAN = {
    "Basic Water Energy": {
        "primary_targets": ["Palafin ex", "Palafin", "Finizen"],
        "secondary_targets": ["Mega Dragonite ex", "Dragonair", "Dratini"],
        "reason": "Palafin ex attacks for one Water; Dragonite may also need Water.",
    },
    "Basic Lightning Energy": {
        "primary_targets": ["Mega Dragonite ex", "Dragonair", "Dratini"],
        "secondary_targets": [],
        "reason": "Lightning Energy is scarce and reserved for Mega Dragonite ex.",
    },
}

PROTECTED_CARDS = [
    "Finizen",
    "Palafin",
    "Palafin ex",
    "Dratini",
    "Dragonair",
    "Mega Dragonite ex",
    "Basic Lightning Energy",
    "Surfing Beach",
    "Switch",
    "Secret Box",
    "Crispin",
    "Hilda",
    "Energy Retrieval",
    "Night Stretcher",
]

DISCARD_FIRST_CANDIDATES = [
    "extra Buddy-Buddy Poffin after Bench is full",
    "extra Surfing Beach if Stadium already in play",
    "extra Air Balloon if switch engine is stable",
    "extra Lillie's Determination if Supporter already used or hand is already strong",
    "extra Team Rocket's Petrel when no exact Trainer is needed",
    "extra Water Energy if Energy Retrieval is available and Palafin already has Energy",
]

CARD_BASE_PRIORITY = {
    "Palafin ex": 100,
    "Palafin": 96,
    "Finizen": 94,
    "Mega Dragonite ex": 92,
    "Dragonair": 86,
    "Dratini": 82,
    "Buddy-Buddy Poffin": 95,
    "Poke Pad": 90,
    "Poké Pad": 90,
    "Surfing Beach": 88,
    "Switch": 84,
    "Air Balloon": 82,
    "Hilda": 86,
    "Crispin": 84,
    "Lillie's Determination": 80,
    "Team Rocket's Petrel": 78,
    "Secret Box": 86,
    "Judge": 60,
    "Battle Cage": 55,
    "Palafin TEF 49": 68,
    "Boss's Orders": 74,
    "Boss’s Orders": 74,
    "Tatsugiri": 72,
    "Basic Water Energy": 70,
    "Basic Lightning Energy": 84,
    "Energy Retrieval": 62,
    "Night Stretcher": 64,
}


@lru_cache(maxsize=1)
def card_analysis_map():
    from core.card_analysis import build_all_card_analyses

    return build_all_card_analyses()


@lru_cache(maxsize=1)
def card_relationships():
    from core.card_relationships import build_card_relationships

    return build_card_relationships()


@lru_cache(maxsize=1)
def generated_policy_rules():
    from core.policy_rules_from_analysis import generate_policy_rules_from_card_analysis

    return generate_policy_rules_from_card_analysis(card_analysis_map(), card_relationships())

__all__ = [
    "PRIMARY_ATTACKERS",
    "MAIN_ATTACKERS",
    "MAIN_DAMAGE_DEALERS",
    "SECONDARY_ATTACKERS",
    "SETUP_BASICS",
    "PALAFIN_LINE",
    "DRAGONITE_LINE",
    "SWITCH_CARDS",
    "SEARCH_CARDS",
    "ENERGY_PLAN",
    "PROTECTED_CARDS",
    "DISCARD_FIRST_CANDIDATES",
    "CARD_BASE_PRIORITY",
    "card_analysis_map",
    "card_relationships",
    "generated_policy_rules",
    "card_priority",
    "list_value",
    "load_deck_ids",
    "load_profile",
]
