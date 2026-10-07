from __future__ import annotations

from typing import Any, Optional

from core.finizen_setup_planner import finizen_setup_stable
from core.palafin_planner import DRAGONAIR, DRATINI, PALAFIN, PALAFIN_EX, MEGA_DRAGONITE_EX
from core.priority_tables import count_in_play, has_in_hand


def needed_non_rulebox_evolution_piece(state: Any) -> Optional[str]:
    if count_in_play(state, "Finizen") > 0 and not has_in_hand(state, "Palafin") and count_in_play(state, "Palafin") == 0:
        return "Palafin"
    if finizen_setup_stable(state) and not dratini_in_play(state) and not has_in_hand(state, "Dratini"):
        return "Dratini"
    if dratini_in_play(state) and count_in_play(state, "Dragonair") == 0 and not has_in_hand(state, "Dragonair"):
        return "Dragonair"
    if not has_in_hand(state, "Tatsugiri") and count_in_play(state, "Tatsugiri") == 0:
        return "Tatsugiri"
    return None


def score_pokepad_target_from_plan(state: Any, target_name: str) -> float:
    if target_name in {"Palafin ex", "Mega Dragonite ex"}:
        return -7000.0
    if target_name == "Dragonair" and not dratini_in_play(state):
        return -9000.0
    needed = needed_non_rulebox_evolution_piece(state)
    if target_name == needed == "Palafin":
        return 5500.0
    if target_name == needed == "Dratini":
        return 3500.0
    if target_name == needed == "Dragonair":
        return 3500.0
    if target_name == needed == "Tatsugiri":
        return 2200.0
    return 0.0


def pokepad_can_find_needed_piece(state: Any) -> bool:
    return needed_non_rulebox_evolution_piece(state) is not None


def dratini_in_play(state: Any) -> bool:
    return count_in_play(state, "Dratini") > 0


__all__ = ["needed_non_rulebox_evolution_piece", "score_pokepad_target_from_plan", "pokepad_can_find_needed_piece", "dratini_in_play"]
