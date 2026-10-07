from deck_profile import card_priority, list_value, load_deck_ids, load_profile

PRIMARY_ATTACKERS = ["Mega Gengar ex", "Hydreigon ex"]

MAIN_ATTACKERS = PRIMARY_ATTACKERS

MAIN_DAMAGE_DEALERS = ["Mega Gengar ex", "Hydreigon ex"]

PRIZE_EXCHANGE_ENGINE = ["Mega Gengar ex"]

ENERGY_ENGINE = ["Toxtricity"]

ENERGY_ENGINE_BASICS = ["Toxel"]

SECONDARY_ATTACKERS = []

SETUP_BASICS = ["Deino", "Gastly", "Toxel"]

HYDREIGON_LINE = ["Deino", "Zweilous", "Hydreigon ex"]

GENGAR_LINE = ["Gastly", "Haunter", "Mega Gengar ex"]

TOXTRICITY_LINE = ["Toxel", "Toxtricity"]

EARLY_GAME_CORE_CARDS = [
    "Buddy-Buddy Poffin",
    "Poké Pad",
    "Deino",
    "Gastly",
    "Toxel",
    "Rare Candy",
    "Hydreigon ex",
    "Haunter",
    "Mega Gengar ex",
    "Lillie's Determination",
]

STAGE1_LINES = {
    "Deino": ["Zweilous"],
    "Gastly": ["Haunter"],
    "Toxel": ["Toxtricity"],
}

STAGE2_LINES = {
    "Deino": ["Hydreigon ex"],
    "Zweilous": ["Hydreigon ex"],
}

RARE_CANDY_TARGETS = {
    "Deino": "Hydreigon ex",
}

PROTECTED_CARDS = [
    "Deino",
    "Hydreigon ex",
    "Rare Candy",
    "Zweilous",
    "Mega Gengar ex",
    "Gastly",
    "Basic Metal Energy",
    "Basic Psychic Energy",
    "Crispin",
    "Secret Box",
    "Boss's Orders",
    "Night Stretcher",
    "Sacred Ash",
    "Energy Recycler",
]

DISCARDABLE_LOW_PRIORITY = [
    "extra Battle Cage",
    "extra Air Balloon",
    "extra Poke Pad when setup is already complete",
    "extra Team Rocket's Petrel when no disruption is needed",
    "extra Lillie's Determination when supporter already used or hand is already strong",
    "extra Darkness Energy only if Hydreigon energy plan is already satisfied or Energy Recycler is available",
    "extra Basic Pokemon after Bench is full and setup is stable",
]

DO_NOT_BENCH_WITHOUT_REASON = [
    "Fezandipiti ex",
    "Pecharunt ex",
    "extra Mega Gengar ex",
]

ENERGY_RESERVATION_RULES = {
    "Basic Metal Energy": {
        "primary_targets": ["Hydreigon ex", "Zweilous", "Deino"],
        "secondary_targets": [],
        "avoid_targets": ["Gastly", "Toxel", "Fezandipiti ex", "Pecharunt ex", "Toxtricity", "Mega Gengar ex"],
        "reason": "Metal Energy is reserved for the Deino evolution chain.",
    },
    "Basic Psychic Energy": {
        "primary_targets": ["Hydreigon ex", "Zweilous", "Deino"],
        "secondary_targets": [],
        "avoid_targets": ["Gastly", "Toxel", "Fezandipiti ex", "Pecharunt ex", "Toxtricity", "Mega Gengar ex"],
        "reason": "Psychic Energy is reserved for the Deino evolution chain.",
    },
    "Basic Darkness Energy": {
        "primary_targets": ["Mega Gengar ex", "Hydreigon ex", "Haunter", "Gastly", "Deino", "Zweilous"],
        "secondary_targets": [],
        "avoid_targets": ["Toxel", "Toxtricity", "Fezandipiti ex", "Pecharunt ex"],
        "reason": "Darkness Energy supports Mega Gengar ex and the Hydreigon ex attack line.",
    },
}

SEARCH_PRIORITY_EARLY = [
    "Deino",
    "Deino",
    "Buddy-Buddy Poffin",
    "Rare Candy",
    "Mega Gengar ex",
    "Hydreigon ex",
    "Zweilous",
    "Gastly",
    "Toxel",
    "Lillie's Determination",
    "Crispin",
]

SEARCH_PRIORITY_MID = [
    "Mega Gengar ex",
    "Hydreigon ex",
    "Rare Candy",
    "Crispin",
    "Basic Metal Energy",
    "Basic Psychic Energy",
    "Boss's Orders",
    "Night Stretcher",
]

SEARCH_PRIORITY_LATE = [
    "Boss's Orders",
    "Hydreigon ex",
    "Night Stretcher",
    "Sacred Ash",
    "Energy Recycler",
    "Basic Metal Energy",
    "Basic Psychic Energy",
]

CARD_BASE_PRIORITY = {
    "Deino": 100,
    "Hydreigon ex": 100,
    "Rare Candy": 95,
    "Buddy-Buddy Poffin": 95,
    "Lillie's Determination": 90,
    "Poke Pad": 85,
    "Poké Pad": 85,
    "Ultra Ball": 85,
    "Crispin": 80,
    "Zweilous": 75,
    "Basic Metal Energy": 75,
    "Basic Psychic Energy": 75,
    "Basic Darkness Energy": 65,
    "Mega Gengar ex": 95,
    "Gastly": 60,
    "Toxel": 55,
    "Toxtricity": 55,
    "Boss's Orders": 80,
    "Boss’s Orders": 80,
    "Secret Box": 80,
    "Night Stretcher": 70,
    "Sacred Ash": 65,
    "Energy Recycler": 60,
    "Fezandipiti ex": 45,
    "Pecharunt ex": 45,
    "Battle Cage": 45,
    "Air Balloon": 45,
    "Team Rocket's Petrel": 50,
    "Special Red Card": 55,
    "Dawn": 50,
}

__all__ = [
    "MAIN_ATTACKERS",
    "PRIMARY_ATTACKERS",
    "MAIN_DAMAGE_DEALERS",
    "PRIZE_EXCHANGE_ENGINE",
    "ENERGY_ENGINE",
    "ENERGY_ENGINE_BASICS",
    "SECONDARY_ATTACKERS",
    "SETUP_BASICS",
    "HYDREIGON_LINE",
    "GENGAR_LINE",
    "TOXTRICITY_LINE",
    "EARLY_GAME_CORE_CARDS",
    "STAGE1_LINES",
    "STAGE2_LINES",
    "RARE_CANDY_TARGETS",
    "PROTECTED_CARDS",
    "DISCARDABLE_LOW_PRIORITY",
    "DO_NOT_BENCH_WITHOUT_REASON",
    "ENERGY_RESERVATION_RULES",
    "SEARCH_PRIORITY_EARLY",
    "SEARCH_PRIORITY_MID",
    "SEARCH_PRIORITY_LATE",
    "CARD_BASE_PRIORITY",
    "card_priority",
    "list_value",
    "load_deck_ids",
    "load_profile",
]
