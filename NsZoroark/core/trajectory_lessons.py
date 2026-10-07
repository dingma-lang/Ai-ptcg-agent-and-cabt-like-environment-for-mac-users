from __future__ import annotations


LESSON_OPENING_POFFIN = {
    "id": "LESSON_OPENING_POFFIN",
    "condition": "Bench not full and Poffin legal",
    "action": "use Buddy-Buddy Poffin",
    "priority": 5000,
    "reason": "Use Poffin immediately to establish the Deino/Gastly/Toxel setup core.",
}

LESSON_SECRET_BOX_TO_POFFIN = {
    "id": "LESSON_SECRET_BOX_TO_POFFIN",
    "condition": "early game, Secret Box legal, bench weak, discard acceptable, no Poffin in hand",
    "action": "use Secret Box to find Poffin package",
    "priority": 3600,
    "package": ["Buddy-Buddy Poffin", "Air Balloon", "Lillie's Determination", "Battle Cage"],
    "reason": "Expert log used Secret Box to find Poffin and setup resources.",
}

LESSON_FEZ_AFTER_KO = {
    "id": "LESSON_FEZ_AFTER_KO",
    "condition": "our Pokemon was KO'd last opponent turn and Fezandipiti ability legal",
    "action": "use Flip the Script before Supporter",
    "priority": 5000,
    "reason": "Expert log used Fezandipiti immediately after KO to recover.",
}

LESSON_MEGA_GENGAR_ATTACKER = {
    "id": "LESSON_MEGA_GENGAR_ATTACKER",
    "condition": "Haunter/Mega Gengar line available and Darkness Energy available",
    "action": "build Mega Gengar as real attacker",
    "priority": 4200,
    "reason": "Expert log used Mega Gengar ex to attack Decidueye ex for 230 and move Energy to Hydreigon.",
}

LESSON_TOXTRICITY_ENGINE = {
    "id": "LESSON_TOXTRICITY_ENGINE",
    "condition": "Toxtricity ability legal and Darkness attacker needs Energy",
    "action": "use Sinister Surge",
    "priority": 4300,
    "reason": "Use Toxtricity as support-only Energy acceleration, not as an attacker.",
}

LESSON_HYDREIGON_OBSIDIAN_MULTI_PRIZE = {
    "id": "LESSON_HYDREIGON_OBSIDIAN_MULTI_PRIZE",
    "condition": "Hydreigon Obsidian can KO Active and important Bench targets",
    "action": "attack with Obsidian",
    "priority": 6000,
    "reason": "Expert log won by taking multi-prize Obsidian turns.",
}

LESSON_RECOVER_ENERGY_LATE = {
    "id": "LESSON_RECOVER_ENERGY_LATE",
    "condition": "late game, key Energy in discard, Hydreigon can be rebuilt",
    "action": "use Energy Recycler / Night Stretcher",
    "priority": 3800,
    "reason": "Expert log recovered Energy before final Obsidian.",
}

ALL_LESSONS = [
    LESSON_OPENING_POFFIN,
    LESSON_SECRET_BOX_TO_POFFIN,
    LESSON_FEZ_AFTER_KO,
    LESSON_MEGA_GENGAR_ATTACKER,
    LESSON_TOXTRICITY_ENGINE,
    LESSON_HYDREIGON_OBSIDIAN_MULTI_PRIZE,
    LESSON_RECOVER_ENERGY_LATE,
]
