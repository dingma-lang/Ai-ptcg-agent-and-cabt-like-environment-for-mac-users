from __future__ import annotations

from typing import Any, Optional

from state_eval import OPT_ATTACK, OPT_CARD, active_pokemon, bench_space, card_id, card_id_from_option, option_type
from core.deck_operating_system import compute_deck_goal_state
from core.priority_tables import canonical_name_from_id, count_in_play, context_source_name, has_in_play


def score_call_for_family_option(state: Any, option: Any, base_score: float = 0.0) -> float:
    if option_type(option) != OPT_ATTACK:
        return 0.0
    active_name = canonical_name_from_id(card_id(active_pokemon(state)))
    if active_name != "Toxel":
        return 0.0
    attack_text = attack_label(state, option)
    if "call for family" not in attack_text:
        return 0.0
    if base_score >= 10000.0:
        return -5000.0
    if bench_space(state) <= 0:
        return -5000.0
    goal = compute_deck_goal_state(state)
    if goal.target_board_complete:
        return -1500.0
    score = 0.0
    if len(goal.missing_core_pieces) > 0:
        score += 3500.0
    if should_fetch_support_basic_before_ko(state):
        score += 3000.0
    return score or 1200.0


def score_call_for_family_target(state: Any, cid: Optional[int]) -> float:
    if context_source_name(state) != "Toxel":
        return 0.0
    name = canonical_name_from_id(cid)
    if not name:
        return 0.0
    if name == "Deino":
        return 7200.0 if count_in_play(state, "Deino") < 2 else 900.0
    if name == "Gastly":
        return 6800.0 if not has_in_play(state, "Gastly") else 800.0
    if name == "Toxel":
        return 4400.0 if not has_in_play(state, "Toxtricity") else 500.0
    if name == "Fezandipiti ex":
        return 6200.0 if should_fetch_support_basic_before_ko(state) else 3600.0
    if name == "Pecharunt ex":
        return 5200.0 if should_fetch_pecharunt(state) else 2600.0
    return 300.0


def attack_label(state: Any, option: Any) -> str:
    try:
        from card_db import get_db
        from state_eval import getv

        attack = get_db().get_attack(getv(option, "attackId"))
        return f"{getattr(attack, 'name', '')} {getattr(attack, 'text', '')}".lower()
    except Exception:
        return ""


def should_fetch_support_basic_before_ko(state: Any) -> bool:
    try:
        from core.danger_evaluator import evaluate_danger

        danger = evaluate_danger(state)
        return danger.severity in ("HIGH", "CRITICAL") or len(getattr(danger, "reasons", []) or []) > 0
    except Exception:
        return len(compute_deck_goal_state(state).missing_support_basics) > 0


def should_fetch_pecharunt(state: Any) -> bool:
    try:
        from core.pivot_planner import active_is_stuck_or_exposed, darkness_attacker_on_bench

        return active_is_stuck_or_exposed(state) or darkness_attacker_on_bench(state)
    except Exception:
        return False


def call_for_family_debug_reason(state: Any, option: Any, base_score: float = 0.0) -> str:
    score = score_call_for_family_option(state, option, base_score)
    if score <= -5000.0:
        return "Do not use Call for Family because damage/KO attack is available or Bench is full."
    if should_fetch_support_basic_before_ko(state):
        return "Use Call for Family to search support Basic ex before expected KO."
    return "Use Toxel Call for Family because Bench setup is incomplete."
