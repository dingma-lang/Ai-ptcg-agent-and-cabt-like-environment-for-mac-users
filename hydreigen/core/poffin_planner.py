from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

from card_db import get_db
from state_eval import OPT_CARD, OPT_PLAY, bench_pokemon, bench_space, card_id_from_option, getv, option_type
from core.priority_tables import canonical_name_from_id, count_in_play, context_source_name, has_in_play
from core.setup_recovery_planner import call_for_family_bridge_needed, core_setup_basics_established, poffin_trainer_target_score


@dataclass(frozen=True)
class Decision:
    should_act: bool
    score: float = 0.0
    option_index: Optional[int] = None
    reason: str = ""


def should_use_poffin_now(state: Any, legal_options: Sequence[Any] | None = None) -> Decision:
    options = list(legal_options or getattr(state, "options", []) or [])
    idx = poffin_option_index(state, options)
    if idx is None:
        return Decision(False, reason="Buddy-Buddy Poffin is not legal.")
    if bench_space(state) <= 0:
        return Decision(False, reason="Bench is full.")

    bench_count = len(bench_pokemon(state))
    turn = int(getv(state.current, "turn", 0) or 0)
    if bench_count == 0:
        return Decision(True, 6500.0, idx, "Use Buddy-Buddy Poffin because Bench is not full.")
    if bench_count == 1:
        return Decision(True, 6200.0, idx, "Use Buddy-Buddy Poffin because Bench is not full.")
    if missing_setup_basic(state):
        return Decision(True, 5900.0, idx, "Use Buddy-Buddy Poffin because Bench is not full and setup targets remain.")
    if turn <= 4 and bench_count < 3:
        return Decision(True, 5600.0, idx, "Use Buddy-Buddy Poffin because Bench is not full.")
    if core_setup_basics_established(state) and bench_count >= 3:
        return Decision(False, poffin_trainer_target_score(state), idx, "Hold Buddy-Buddy Poffin because core Basics are already established.")
    score = poffin_trainer_target_score(state)
    if score <= 0.0:
        return Decision(False, score, idx, "Hold Buddy-Buddy Poffin because the Bench is already developed.")
    return Decision(True, score, idx, "Use Buddy-Buddy Poffin because setup targets remain.")


def score_poffin_play(state: Any, option: Any) -> float:
    if canonical_name_from_id(card_id_from_option(state, option)) != "Buddy-Buddy Poffin":
        return 0.0
    decision = should_use_poffin_now(state)
    return decision.score if decision.should_act else 0.0


def score_poffin_target(state: Any, cid: Optional[int]) -> float:
    if not is_poffin_eligible_target(cid):
        return -10000.0
    name = canonical_name_from_id(cid)
    if not name:
        return -10000.0
    has_deino = count_in_play(state, "Deino") > 0
    has_gastly = has_in_play(state, "Gastly")
    has_toxel = has_in_play(state, "Toxel") or has_in_play(state, "Toxtricity")
    bridge_needed = call_for_family_bridge_needed(state, require_no_basic_in_hand=False)
    if name == "Deino":
        if count_in_play(state, "Deino") == 0:
            return 4600.0
        if bridge_needed:
            return 500.0
        if not (has_gastly and has_toxel):
            return 2100.0
        if count_in_play(state, "Deino") == 1:
            return 3600.0
        return 1500.0
    if name == "Gastly":
        if not has_gastly:
            return 4400.0 if has_deino else 4300.0
        return 900.0
    if name == "Toxel":
        if bridge_needed:
            return 5400.0
        if not has_toxel:
            return 4300.0 if has_deino else 4200.0
        return 650.0
    return 300.0


def is_poffin_eligible_target(cid: Optional[int]) -> bool:
    card = get_db().get_card(cid)
    return bool(card and card.card_type == "Pokemon" and card.basic and 0 < card.hp <= 70)


def poffin_option_index(state: Any, options: Sequence[Any]) -> Optional[int]:
    for idx, option in enumerate(options):
        if option_type(option) == OPT_PLAY and canonical_name_from_id(card_id_from_option(state, option)) == "Buddy-Buddy Poffin":
            return idx
    return None


def missing_setup_basic(state: Any) -> bool:
    return (
        count_in_play(state, "Deino") < 1
        or not has_in_play(state, "Gastly")
        or not (has_in_play(state, "Toxel") or has_in_play(state, "Toxtricity"))
    )


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
