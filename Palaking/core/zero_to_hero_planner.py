from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

from state_eval import OPT_ABILITY, OPT_PLAY, OPT_RETREAT, card_id_from_option, option_type
from core.palafin_planner import LILLIE, active_name, bench_has_water_switch_target, palafin_ex_overloaded_in_hand, score_palaking_option
from core.priority_tables import canonical_name_from_id


@dataclass(frozen=True)
class ZeroToHeroPlan:
    available: bool
    option_index: Optional[int] = None
    score: float = 0.0
    reason: str = ""


def detect_zero_to_hero_opportunity(state: Any, legal_options: Sequence[Any]) -> ZeroToHeroPlan:
    best = ZeroToHeroPlan(False, reason="Zero to Hero not ready.")
    active_is_palafin = active_name(state) == "Palafin"
    should_shuffle_ex_back = palafin_ex_overloaded_in_hand(state) and lillie_play_legal(state, legal_options)
    try:
        from core.turn_plan import zero_to_hero_route

        route = zero_to_hero_route(state)
    except Exception:
        route = None
    for idx, option in enumerate(legal_options):
        name = canonical_name_from_id(card_id_from_option(state, option))
        typ = option_type(option)
        score = 0.0
        reason = ""
        if route is not None and not route.palafin_ex_in_deck and (
            typ == OPT_ABILITY and name == "Palafin" or active_is_palafin and typ == OPT_RETREAT
        ):
            score = -10000.0
            reason = route.reason
        elif route is not None and active_is_palafin and not route.can_start and (
            typ == OPT_ABILITY and name == "Palafin" or typ == OPT_RETREAT or name in {"Surfing Beach", "Switch", "Kieran", "Air Balloon"}
        ):
            score = -7000.0
            reason = route.reason
        elif should_shuffle_ex_back and (typ == OPT_ABILITY and name == "Palafin" or active_is_palafin and typ == OPT_RETREAT):
            score = -9000.0
            reason = "Use Lillie first because multiple Palafin ex are stuck in hand."
        elif should_shuffle_ex_back and active_is_palafin and name in {"Surfing Beach", "Switch", "Kieran", "Air Balloon"}:
            score = -9000.0
            reason = "Use Lillie first because multiple Palafin ex are stuck in hand."
        elif active_is_palafin and typ == OPT_RETREAT and bench_has_water_switch_target(state):
            retreat_score = score_palaking_option(state, option, 0.0, idx)
            if retreat_score < 0.0:
                score = retreat_score
                reason = "Hold retreat because it would discard Energy without urgency."
            else:
                score = 9200.0 if route is not None and route.can_attack_this_turn else 8600.0
                reason = route.reason if route is not None else "Use switch effect to move Palafin to Bench and trigger Zero to Hero."
        elif typ == OPT_ABILITY and name == "Palafin":
            score = 9800.0 if route is not None and route.can_attack_this_turn else 8600.0
            reason = "Zero to Hero available: transform Palafin into Palafin ex."
        else:
            score = score_palaking_option(state, option, 0.0, idx)
            if score >= 7000.0 and active_is_palafin:
                reason = route.reason if route is not None else "Use switch effect to move Palafin to Bench and trigger Zero to Hero."
        if score > best.score:
            best = ZeroToHeroPlan(score > 0.0, idx, score, reason or "Zero to Hero line.")
    return best


def lillie_play_legal(state: Any, legal_options: Sequence[Any]) -> bool:
    return any(option_type(option) == OPT_PLAY and card_id_from_option(state, option) == LILLIE for option in legal_options)


def score_zero_to_hero_option(state: Any, option: Any, option_index: int = 0) -> float:
    plan = detect_zero_to_hero_opportunity(state, getattr(state, "options", []) or [])
    return plan.score if plan.option_index == option_index else 0.0
