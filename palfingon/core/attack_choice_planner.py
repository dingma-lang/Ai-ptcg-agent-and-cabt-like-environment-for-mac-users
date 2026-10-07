from __future__ import annotations

from typing import Any

from card_db import get_db
from state_eval import OPT_ATTACK, active_pokemon, card_id, getv, option_type
from core.priority_tables import canonical_name_from_id


def score_attack_choice_option(state: Any, option: Any, base_score: float = 0.0) -> float:
    if option_type(option) != OPT_ATTACK:
        return 0.0
    return score_palaking_attack_choice(state, option, base_score)


def score_palaking_attack_choice(state: Any, option: Any, base_score: float = 0.0) -> float:
    active_name = canonical_name_from_id(card_id(active_pokemon(state)))
    attack = get_db().get_attack(getv(option, "attackId"))
    attack_name = str(getattr(attack, "name", "") or "")
    if active_name == "Palafin ex":
        try:
            from core.giga_impact_planner import score_giga_impact_attack

            giga = score_giga_impact_attack(state, option)
            if giga.score >= 8500.0:
                return 2400.0
            if giga.score >= 6000.0:
                return 900.0
            if giga.score >= 2500.0:
                return 500.0
        except Exception:
            pass
        return 6200.0 if base_score >= 10000.0 else 2200.0
    if active_name == "Mega Dragonite ex":
        if base_score >= 10000.0:
            return 6200.0
        if "Ryuno" in attack_name or "Glide" in attack_name:
            return -2500.0
        return 0.0
    if active_name == "Palafin":
        return -3000.0
    return 0.0
