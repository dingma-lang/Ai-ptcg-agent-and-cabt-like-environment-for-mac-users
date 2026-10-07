from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

from action_classifier import ActionCategory, classify_legal_option
from state_eval import card_id_from_option, getv, hand_count
from core.crispin_planner import hydreigon_crispin_plan, score_crispin_option
from core.deck_operating_system import DeckGoalState, compute_deck_goal_state
from core.priority_tables import canonical_name_from_id, has_in_hand
from core.trainer_search_planner import best_petrel_trainer_need, score_petrel_play


@dataclass(frozen=True)
class SupporterDecision:
    should_use: bool
    option_index: Optional[int] = None
    supporter_name: str = ""
    score: float = 0.0
    reason: str = ""


def choose_best_supporter(state: Any, legal_options: Sequence[Any], deck_goal: Optional[DeckGoalState] = None) -> SupporterDecision:
    if bool(getv(state.current, "supporterPlayed", False)):
        return SupporterDecision(False, reason="Supporter already used.")
    deck_goal = deck_goal or compute_deck_goal_state(state)
    best = SupporterDecision(False, reason="No legal Supporter option.")
    for idx, option in enumerate(legal_options):
        action = classify_legal_option(state, option, idx)
        if action.category != ActionCategory.PLAY_SUPPORTER:
            continue
        name = action.card_name or canonical_name_from_id(card_id_from_option(state, option))
        score, reason = score_supporter_by_function(state, option, name, deck_goal)
        if score > best.score:
            best = SupporterDecision(score > 0.0, idx, name, score, reason)
    return best


def score_supporter_by_function(state: Any, option: Any, name: str, deck_goal: DeckGoalState) -> tuple[float, str]:
    turn = int(getv(state.current, "turn", 0) or 0)
    if name == "Crispin":
        score = score_crispin_option(state, option)
        return score, "Use Crispin because Hydreigon ex is evolved and lacks required Energy."
    if name == "Team Rocket's Petrel":
        if has_in_hand(state, "Buddy-Buddy Poffin") and deck_goal.open_bench_slots > 0:
            return -2200.0, "Poffin already in hand, do not Petrel for Poffin."
        need = best_petrel_trainer_need(state)
        return (score_petrel_play(state, option), need.reason if need.name else "No exact Trainer need.")
    if name == "Dawn":
        if deck_goal.missing_core_pieces or deck_goal.missing_evolution_pieces or deck_goal.missing_support_basics:
            return 5200.0 + min(deck_goal.setup_urgency, 2600.0), "Use Dawn because Pokemon pieces are missing."
        return 600.0, "Dawn has low value because Pokemon package is mostly complete."
    if name == "Lillie's Determination":
        from state_eval import deck_count

        if deck_count(state) <= 3:
            return -9000.0, "Do not use Lillie because deck-out risk is too high."
        try:
            from core.prize_availability_tracker import infer_card_availability
            from core.recovery_goal_planner import recovery_card_legal

            if infer_card_availability(state, None).all_deino_in_discard and recovery_card_legal(state):
                return -5000.0, "Do not use Lillie because Deino recovery is available now."
        except Exception:
            pass
        try:
            from core.lillie_guard import useful_action_before_lillie

            precheck = useful_action_before_lillie(state)
            if precheck.should_wait:
                return -2600.0, precheck.reason
        except Exception:
            pass
        base = 9800.0 if hand_count(state) <= 4 or (turn <= 4 and not deck_goal.target_board_complete) else 7600.0
        return base + min(deck_goal.setup_urgency, 1800.0), "Use Lillie's Determination as the preferred Supporter after checking useful hand actions."
    if name == "Boss's Orders":
        return 350.0, "Use Boss only if it improves prize route."
    if name == "Special Red Card":
        return 500.0 if deck_goal.target_board_complete else -700.0, "Use disruption only after setup is stable."
    return 0.0, "Unknown Supporter function."


def score_supporter_router_option(state: Any, option: Any) -> float:
    decision = choose_best_supporter(state, getattr(state, "options", []) or [], compute_deck_goal_state(state))
    if decision.option_index is None:
        return 0.0
    try:
        idx = list(getattr(state, "options", []) or []).index(option)
    except ValueError:
        return 0.0
    return decision.score if idx == decision.option_index and decision.should_use else 0.0


def legal_supporter_exists(state: Any, name: str) -> bool:
    for idx, option in enumerate(getattr(state, "options", []) or []):
        action = classify_legal_option(state, option, idx)
        if action.category == ActionCategory.PLAY_SUPPORTER and (action.card_name or canonical_name_from_id(card_id_from_option(state, option))) == name:
            return True
    return False


def supporter_debug(state: Any) -> dict[str, Any]:
    decision = choose_best_supporter(state, getattr(state, "options", []) or [], compute_deck_goal_state(state))
    return {
        "supporter_slot": "used" if bool(getv(state.current, "supporterPlayed", False)) else "unused",
        "best_supporter": decision.supporter_name,
        "reason": decision.reason,
    }
