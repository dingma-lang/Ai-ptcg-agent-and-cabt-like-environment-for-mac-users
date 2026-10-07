from __future__ import annotations


EXPERT_LOG_2_LESSONS = {
    "opening_low_setup": "When opening hand has only one Basic and little setup, use search to find a second Basic before relying on draw.",
    "disposable_active": "If Active Basic is likely to be KO'd, attach Energy to the Benched evolution line, not the disposable Active.",
    "pre_ko_fezandipiti": "If opponent can KO our Active next turn and Fezandipiti ex is searchable, search/bench Fezandipiti before KO to enable Flip the Script.",
    "setup_before_lillie": "Use obvious setup cards before Lillie's Determination, then use Lillie to refresh after board improves.",
    "pokepad_context": "Use Poké Pad based on missing non-Rule Box pieces: second Deino first, Gastly if Gengar chain is in hand, Zweilous if Deino can evolve.",
    "rare_candy_reserved": "Rare Candy is primarily for Hydreigon ex. Do not waste it if Hydreigon line is expected.",
    "gastly_air_balloon_pivot": "Gastly/Haunter with Air Balloon can be a pivot after KO and later retreat into Hydreigon.",
    "toxtricity_prize_check": "If Toxel/Toxtricity pieces are prized/unavailable, lower the Toxtricity engine priority.",
    "crispin_hydreigon_completion": "Use Crispin to complete exact Hydreigon energy requirements. Do not overattach.",
    "obsidian_target_engine": "Use Obsidian Bench damage on opponent engine pieces, not random Bench Pokémon.",
    "crashing_headbutt_when_obsidian_bad": "If Obsidian does not KO Active and Bench damage has low value or is blocked, use Crashing Headbutt.",
    "deino_discard_recovery": "If all Deino are in discard, shift to recovery goal: Night Stretcher/Sacred Ash, while building Mega Gengar.",
}


EXPERT_LOG_2_NAME = "tristary_vs_ceruledge_win"


def lesson_text(key: str) -> str:
    return EXPERT_LOG_2_LESSONS.get(key, "")
