from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from state_eval import bench_space, hand_count
from core.priority_tables import canonical_name_from_id, count_in_play, has_in_hand


@dataclass(frozen=True)
class ExactSetupNeed:
    needs_poffin: bool = False
    needs_pokepad: bool = False
    reason: str = ""


def bench_needs_poffin(state: Any) -> bool:
    try:
        from core.turn_plan import poffin_need_score

        return poffin_need_score(state) >= 2500.0
    except Exception:
        pass
    if bench_space(state) <= 0:
        return False
    palafin_pieces = count_in_play(state, "Finizen") + count_in_play(state, "Palafin") + count_in_play(state, "Palafin ex")
    if palafin_pieces < 2:
        return True
    if not has_in_hand(state, "Buddy-Buddy Poffin") and count_in_play(state, "Tatsugiri") == 0:
        return True
    return False


def poffin_already_in_hand(state: Any) -> bool:
    return has_in_hand(state, "Buddy-Buddy Poffin")


def score_secret_box_item_target(state: Any, target_name: str) -> float:
    poffin_needed = bench_needs_poffin(state)
    if not poffin_needed:
        if target_name == "Lillie's Determination" and hand_count(state) <= 4:
            return 6200.0
        return 0.0
    if target_name == "Lillie's Determination":
        return 15000.0 if hand_count(state) <= 4 else 7200.0
    if target_name in {"Team Rocket's Petrel", "Hilda", "Crispin"}:
        return 4200.0
    if target_name == "Buddy-Buddy Poffin":
        return 5500.0
    try:
        from core.pokepad_dragonite_planner import needed_non_rulebox_evolution_piece

        if target_name == "Poke Pad" and needed_non_rulebox_evolution_piece(state) == "Palafin":
            return 7600.0
        if needed_non_rulebox_evolution_piece(state) == "Palafin" and target_name == "Air Balloon":
            return 4600.0
        if needed_non_rulebox_evolution_piece(state) == "Palafin" and target_name == "Surfing Beach":
            return 7600.0
    except Exception:
        pass
    if target_name in {"Poke Pad", "Switch"} and immediate_zero_to_hero_item(target_name, state):
        return 800.0
    return -4000.0


def score_petrel_poffin_target(state: Any, target_name: str) -> float:
    if target_name != "Buddy-Buddy Poffin":
        return 0.0
    try:
        from core.pokepad_dragonite_planner import needed_non_rulebox_evolution_piece

        if needed_non_rulebox_evolution_piece(state) == "Palafin":
            return -2500.0
    except Exception:
        pass
    if poffin_already_in_hand(state):
        return -8000.0
    return 5000.0 if bench_needs_poffin(state) else -2500.0


def score_poffin_before_box_or_petrel(state: Any, card_name: str) -> float:
    if not bench_needs_poffin(state):
        return 0.0
    if card_name == "Buddy-Buddy Poffin":
        return 6500.0
    if poffin_already_in_hand(state) and card_name in {"Team Rocket's Petrel", "Secret Box"}:
        return -6500.0
    return 0.0


def immediate_zero_to_hero_item(target_name: str, state: Any) -> bool:
    return target_name == "Switch" and count_in_play(state, "Palafin") > 0


__all__ = [
    "bench_needs_poffin",
    "poffin_already_in_hand",
    "score_secret_box_item_target",
    "score_petrel_poffin_target",
    "score_poffin_before_box_or_petrel",
]
