from functools import lru_cache

from deck_profile import card_priority, list_value, load_deck_ids, load_profile

PRIMARY_ATTACKERS = ["N's Zoroark ex"]
MAIN_ATTACKERS = ["N's Zoroark ex"]
MAIN_DAMAGE_DEALERS = ["N's Zoroark ex"]
BACKUP_ATTACKERS = [
    "Second N's Zoroark ex",
    "Pecharunt ex only late/emergency",
    "Yveltal only utility/emergency",
    "N's Zekrom Shred only emergency",
    "N's Darmanitan direct Back Draft only emergency",
]
SECONDARY_ATTACKERS = ["N's Darmanitan", "N's Reshiram", "Yveltal", "Pecharunt ex"]
COPY_SOURCES = ["N's Zekrom", "N's Darmanitan", "N's Reshiram", "N's Darumaka"]
UTILITY_POKEMON = ["Yveltal", "Munkidori"]
SUPPORT_ONLY = ["Fezandipiti ex"]

SETUP_BASICS = ["N's Zorua", "N's Zekrom", "N's Reshiram", "N's Darumaka", "Yveltal", "Munkidori"]
ZOROARK_LINE = ["N's Zorua", "N's Zoroark ex"]
DARMANITAN_LINE = ["N's Darumaka", "N's Darmanitan"]
NS_BENCH_ATTACKS = ["N's Zekrom", "N's Darmanitan", "N's Reshiram"]
SEARCH_CARDS = ["Buddy-Buddy Poffin", "Poké Pad", "Cyrano", "Ciphermaniac's Codebreaking"]
DISRUPTION_CARDS = ["Boss's Orders", "Unfair Stamp", "Tool Scrapper", "Team Rocket's Watchtower"]
PRIMARY_ENERGY_TARGETS = ["N's Zoroark ex", "Second N's Zoroark ex"]
SECONDARY_ENERGY_TARGETS = ["Munkidori", "Yveltal", "N's Darmanitan", "Pecharunt ex"]
BAD_ENERGY_TARGETS = ["N's Zekrom", "N's Reshiram", "Fezandipiti ex", "Pecharunt ex"]
TARGET_BOARD = {
    "active_or_ready_attacker": "N's Zoroark ex with 2 Darkness",
    "backup_line": "Second N's Zorua / N's Zoroark ex line",
    "copy_source_1": "N's Zekrom",
    "copy_source_2_optional": "N's Reshiram or N's Darmanitan",
    "support_slots": ["Fezandipiti ex", "Pecharunt ex", "Munkidori"],
    "total_slots": 6,
}

ENERGY_PLAN = {
    "Basic Darkness Energy": {
        "primary_targets": ["N's Zoroark ex"],
        "secondary_targets": ["N's Darmanitan", "Munkidori", "Yveltal", "Pecharunt ex"],
        "reason": "Zoroark ex is the main attacker; N's PP Up can recover Darkness Energy from discard.",
    }
}

PROTECTED_CARDS = [
    "N's Zorua",
    "N's Zoroark ex",
    "N's Zekrom",
    "N's Reshiram",
    "N's PP Up",
    "N's Castle",
    "Basic Darkness Energy",
]

DISCARD_FIRST_CANDIDATES = [
    "extra Boss's Orders when no gust KO exists",
    "extra N's Castle after Stadium is already active",
    "extra Binding Mochi when no attacker can use it",
    "extra Darkness Energy when N's PP Up or Night Stretcher creates value",
    "extra Ciphermaniac when no Trade/draw conversion exists",
    "Team Rocket's Watchtower while our Abilities still matter",
    "extra low-impact support Basic after Bench is stable",
]

CARD_BASE_PRIORITY = {
    "N's Zoroark ex": 100,
    "N's Zorua": 96,
    "N's Zekrom": 94,
    "Buddy-Buddy Poffin": 92,
    "N's Reshiram": 90,
    "Poke Pad": 88,
    "N's PP Up": 86,
    "N's Castle": 84,
    "Lillie's Determination": 82,
    "Ciphermaniac's Codebreaking": 80,
    "Cyrano": 78,
    "Boss's Orders": 74,
    "Black Belt's Training": 72,
    "Binding Mochi": 70,
    "Unfair Stamp": 69,
    "Air Balloon": 69,
    "Tool Scrapper": 64,
    "Team Rocket's Watchtower": 57,
    "N's Darumaka": 68,
    "N's Darmanitan": 68,
    "Yveltal": 62,
    "Munkidori": 60,
    "Fezandipiti ex": 58,
    "Pecharunt ex": 58,
    "Basic Darkness Energy": 56,
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
    "BACKUP_ATTACKERS",
    "COPY_SOURCES",
    "UTILITY_POKEMON",
    "SUPPORT_ONLY",
    "SETUP_BASICS",
    "ZOROARK_LINE",
    "DARMANITAN_LINE",
    "NS_BENCH_ATTACKS",
    "SEARCH_CARDS",
    "DISRUPTION_CARDS",
    "PRIMARY_ENERGY_TARGETS",
    "SECONDARY_ENERGY_TARGETS",
    "BAD_ENERGY_TARGETS",
    "TARGET_BOARD",
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
