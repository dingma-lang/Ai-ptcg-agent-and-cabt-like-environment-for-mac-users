from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from state_eval import card_id, hand_cards
from core.priority_tables import LOW_PRIORITY_DISCARD_IDS, PROTECTED_IDS, canonical_name_from_id, context_source_name
from core.strategy_scope import use_hydreigon_gengar_strategy
from core.ultra_ball_guard import (
    card_can_be_used_this_turn,
    disposable_evolution_score,
    duplicate_in_hand,
    poffin_must_be_used_before_ultra_ball,
    score_ultra_ball_discard_card,
)


@dataclass(frozen=True)
class DiscardCostPlan:
    source_name: str
    required_count: int
    safe_count: int
    protected_count: int
    reason: str


def score_discard_cost_play_safety(state: Any, source_name: str, required_count: int) -> float:
    plan = discard_cost_plan(state, source_name, required_count)
    if plan.safe_count >= required_count:
        return 0.0
    missing = required_count - plan.safe_count
    if source_name == "Secret Box":
        return -3600.0 - 1200.0 * missing
    return -2200.0 - 900.0 * missing


def discard_cost_plan(state: Any, source_name: str = "", required_count: int = 1) -> DiscardCostPlan:
    source_name = source_name or context_source_name(state)
    safe = 0
    protected = 0
    for hand_card in hand_cards(state):
        cid = card_id(hand_card)
        if cid is None:
            continue
        if canonical_name_from_id(cid) == source_name:
            continue
        score = score_discard_cost_card(state, cid, source_name)
        if score > 0:
            safe += 1
        if score <= -2500.0:
            protected += 1
    return DiscardCostPlan(
        source_name=source_name,
        required_count=required_count,
        safe_count=safe,
        protected_count=protected,
        reason=f"{source_name} discard safety: safe={safe}, protected={protected}, required={required_count}.",
    )


def score_discard_cost_card(state: Any, cid: Optional[int], source_name: str = "") -> float:
    if cid is None:
        return 0.0
    source_name = source_name or context_source_name(state)
    if not use_hydreigon_gengar_strategy(state):
        return score_generic_discard_cost_card(state, cid, source_name)
    if source_name == "Ultra Ball":
        return score_ultra_ball_discard_card(state, cid)

    name = canonical_name_from_id(cid)
    if name == source_name:
        return -9999.0
    if name == "Buddy-Buddy Poffin" and poffin_must_be_used_before_ultra_ball(state):
        return -12000.0
    if name == "Lillie's Determination":
        return -11000.0
    if source_name == "Secret Box":
        try:
            from core.combo_presence_planner import score_secret_box_energy_discard

            energy_combo_score = score_secret_box_energy_discard(state, cid)
            if energy_combo_score:
                return energy_combo_score
        except Exception:
            pass
    if card_can_be_used_this_turn(state, cid):
        return -8500.0
    if cid in PROTECTED_IDS:
        return -3000.0

    disposable = disposable_evolution_score(state, cid)
    if disposable:
        return disposable
    if duplicate_in_hand(state, cid):
        return 650.0
    if cid in LOW_PRIORITY_DISCARD_IDS:
        return 600.0
    if name == "Basic Darkness Energy":
        return 260.0
    return -100.0 if source_name == "Secret Box" else 0.0


def score_generic_discard_cost_card(state: Any, cid: int, source_name: str = "") -> float:
    name = canonical_name_from_id(cid)
    if name == source_name:
        return -9999.0
    if duplicate_in_hand(state, cid):
        return 650.0
    if "Energy" in name:
        return 180.0
    return 0.0 if source_name != "Secret Box" else -50.0
