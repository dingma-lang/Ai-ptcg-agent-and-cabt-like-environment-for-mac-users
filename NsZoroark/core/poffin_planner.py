from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

from card_db import get_db
from state_eval import OPT_CARD, OPT_PLAY, bench_space, card_id_from_option, option_type
from core.priority_tables import canonical_name_from_id, count_in_play, context_source_name, has_in_play
from core.strategy_scope import use_ns_zoroark_strategy, use_palaking_strategy


@dataclass(frozen=True)
class Decision:
    should_act: bool
    score: float = 0.0
    option_index: Optional[int] = None
    reason: str = ""


def should_use_poffin_now(state: Any, legal_options: Sequence[Any] | None = None) -> Decision:
    if use_ns_zoroark_strategy(state):
        try:
            from core.search_planner_zoroark import should_use_poffin_zoroark

            decision = should_use_poffin_zoroark(state, legal_options)
            return Decision(decision.should_act, decision.score, decision.option_index, decision.reason)
        except Exception:
            pass
    if use_palaking_strategy(state):
        options = list(legal_options or getattr(state, "options", []) or [])
        idx = poffin_option_index(state, options)
        if idx is None:
            return Decision(False, reason="Buddy-Buddy Poffin is not legal.")
        if bench_space(state) <= 0:
            return Decision(False, reason="Bench is full.")
        try:
            from core.palafin_planner import poffin_targets_likely_remaining

            if not poffin_targets_likely_remaining(state):
                return Decision(False, -900.0, idx, "Hold Buddy-Buddy Poffin; no likely Finizen/Tatsugiri targets remain.")
        except Exception:
            pass
        line_count = count_in_play(state, "Finizen") + count_in_play(state, "Palafin") + count_in_play(state, "Palafin ex")
        if line_count == 0:
            return Decision(True, 7800.0, idx, "Use Buddy-Buddy Poffin for first Finizen.")
        if line_count == 1:
            return Decision(True, 7200.0, idx, "Use Buddy-Buddy Poffin for second Finizen.")
        if line_count < 4:
            return Decision(True, 6100.0, idx, "Use Buddy-Buddy Poffin while Bench has room for more Finizen.")
        if not has_in_play(state, "Tatsugiri") and bench_space(state) > 0:
            return Decision(True, 5400.0, idx, "Use Buddy-Buddy Poffin for Tatsugiri support/pivot.")
        return Decision(True, 2600.0, idx, "Use Buddy-Buddy Poffin while Bench is not full and targets remain.")

    options = list(legal_options or getattr(state, "options", []) or [])
    idx = poffin_option_index(state, options)
    if idx is None:
        return Decision(False, reason="Buddy-Buddy Poffin is not legal.")
    if bench_space(state) <= 0:
        return Decision(False, reason="Bench is full.")

    return Decision(True, 500.0, idx, "Use Buddy-Buddy Poffin when Bench space and legal targets exist.")


def score_poffin_play(state: Any, option: Any) -> float:
    if canonical_name_from_id(card_id_from_option(state, option)) != "Buddy-Buddy Poffin":
        return 0.0
    decision = should_use_poffin_now(state)
    return decision.score if decision.should_act else 0.0


def score_poffin_target(state: Any, cid: Optional[int]) -> float:
    if use_ns_zoroark_strategy(state):
        try:
            from core.search_planner_zoroark import score_poffin_target_zoroark

            return score_poffin_target_zoroark(state, cid)
        except Exception:
            pass
    if use_palaking_strategy(state):
        from core.palafin_planner import score_poffin_target as palaking_poffin_target

        return palaking_poffin_target(state, cid, canonical_name_from_id(cid))

    return 300.0 if is_poffin_eligible_target(cid) else -10000.0


def is_poffin_eligible_target(cid: Optional[int]) -> bool:
    card = get_db().get_card(cid)
    return bool(card and card.card_type == "Pokemon" and card.basic and 0 < card.hp <= 70)


def poffin_option_index(state: Any, options: Sequence[Any]) -> Optional[int]:
    for idx, option in enumerate(options):
        if option_type(option) == OPT_PLAY and canonical_name_from_id(card_id_from_option(state, option)) == "Buddy-Buddy Poffin":
            return idx
    return None


def missing_setup_basic(state: Any) -> bool:
    if use_ns_zoroark_strategy(state):
        try:
            from core.target_board import evaluate_target_board

            report = evaluate_target_board(state)
            return report.zorua_count < 2
        except Exception:
            return count_in_play(state, "N's Zorua") < 2
    if use_palaking_strategy(state):
        try:
            from core.palafin_planner import poffin_targets_likely_remaining

            return poffin_targets_likely_remaining(state)
        except Exception:
            return count_in_play(state, "Finizen") + count_in_play(state, "Palafin") + count_in_play(state, "Palafin ex") < 4 or not has_in_play(state, "Tatsugiri")
    return bench_space(state) > 0


def is_poffin_search_context(state: Any) -> bool:
    return context_source_name(state) == "Buddy-Buddy Poffin"


def poffin_search_has_setup_target(state: Any) -> bool:
    if not is_poffin_search_context(state):
        return False
    for option in getattr(state, "options", []) or []:
        if option_type(option) != OPT_CARD:
            continue
        if score_poffin_target(state, card_id_from_option(state, option)) > 0:
            return True
    return False


def poffin_selection_limit(state: Any) -> Optional[int]:
    if not is_poffin_search_context(state):
        return None
    return max(0, min(2, bench_space(state)))
