from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

from action_classifier import ActionCategory, classify_legal_option
from state_eval import OPT_ABILITY, OPT_ATTACH, OPT_EVOLVE, OPT_PLAY, card_id_from_option, getv, option_type
from core.crispin_planner import score_crispin_option
from core.deck_operating_system import compute_deck_goal_state
from core.priority_tables import canonical_name_from_id, has_in_hand
from core.secret_box_planner import score_secret_box_option
from core.supporter_router import choose_best_supporter
from core.trainer_search_planner import score_petrel_play


@dataclass(frozen=True)
class StuckRecoveryDecision:
    is_stuck: bool
    option_index: Optional[int] = None
    score: float = 0.0
    reason: str = ""


def detect_stuck_recovery(state: Any, legal_options: Sequence[Any] | None = None, scores: Sequence[float] | None = None) -> StuckRecoveryDecision:
    del scores
    options = list(legal_options or getattr(state, "options", []) or [])
    goal = compute_deck_goal_state(state)
    if goal.target_board_complete:
        return StuckRecoveryDecision(False, reason="Target board complete.")

    checks = (
        force_poffin(state, options),
        force_petrel(state, options),
        force_secret_box(state, options),
        force_supporter(state, options, goal),
        force_crispin(state, options),
        force_toxtricity(state, options),
        force_evolution(state, options, scores),
        force_energy(state, options, scores),
    )
    best = max((item for item in checks if item.is_stuck), key=lambda item: item.score, default=None)
    if best is not None:
        return best
    return StuckRecoveryDecision(False, reason="No forced stuck recovery action.")


def force_poffin(state: Any, options: Sequence[Any]) -> StuckRecoveryDecision:
    if not has_in_hand(state, "Buddy-Buddy Poffin"):
        return StuckRecoveryDecision(False)
    try:
        from core.poffin_planner import should_use_poffin_now

        decision = should_use_poffin_now(state, options)
        if decision.should_act and decision.option_index is not None:
            return StuckRecoveryDecision(True, decision.option_index, decision.score + 2000.0, "Stuck detected: target board incomplete and Poffin is playable.")
    except Exception:
        pass
    return StuckRecoveryDecision(False)


def force_petrel(state: Any, options: Sequence[Any]) -> StuckRecoveryDecision:
    if bool(getv(state.current, "supporterPlayed", False)):
        return StuckRecoveryDecision(False)
    for idx, option in enumerate(options):
        score = score_petrel_play(state, option)
        if score >= 6500.0:
            return StuckRecoveryDecision(True, idx, score + 1200.0, "Stuck detected: Petrel can get exact setup Trainer.")
    return StuckRecoveryDecision(False)


def force_secret_box(state: Any, options: Sequence[Any]) -> StuckRecoveryDecision:
    for idx, option in enumerate(options):
        score = score_secret_box_option(state, option)
        if score >= 5200.0:
            return StuckRecoveryDecision(True, idx, score + 900.0, "Stuck detected: Secret Box can assemble setup package.")
    return StuckRecoveryDecision(False)


def force_supporter(state: Any, options: Sequence[Any], goal: Any) -> StuckRecoveryDecision:
    decision = choose_best_supporter(state, options, goal)
    if decision.should_use and decision.option_index is not None and decision.score >= 5000.0:
        return StuckRecoveryDecision(True, decision.option_index, decision.score + 700.0, f"Stuck detected: {decision.reason}")
    return StuckRecoveryDecision(False)


def force_crispin(state: Any, options: Sequence[Any]) -> StuckRecoveryDecision:
    for idx, option in enumerate(options):
        score = score_crispin_option(state, option)
        if score >= 4500.0:
            return StuckRecoveryDecision(True, idx, score + 1300.0, "Stuck detected: Hydreigon needs Crispin Energy fixing.")
    return StuckRecoveryDecision(False)


def force_toxtricity(state: Any, options: Sequence[Any]) -> StuckRecoveryDecision:
    try:
        from core.toxtricity_engine_planner import score_toxtricity_option

        for idx, option in enumerate(options):
            if option_type(option) == OPT_ABILITY and score_toxtricity_option(state, option, 0.0) >= 1800.0:
                return StuckRecoveryDecision(True, idx, 4200.0, "Stuck detected: use Toxtricity Sinister Surge on attacker line.")
    except Exception:
        pass
    return StuckRecoveryDecision(False)


def force_evolution(state: Any, options: Sequence[Any], scores: Sequence[float] | None = None) -> StuckRecoveryDecision:
    best_idx: Optional[int] = None
    best_score = -99999.0
    for idx, option in enumerate(options):
        if option_type(option) != OPT_EVOLVE:
            continue
        name = canonical_name_from_id(card_id_from_option(state, option))
        if name not in {"Hydreigon ex", "Mega Gengar ex", "Toxtricity", "Zweilous", "Haunter"}:
            continue
        score = scores[idx] if scores is not None and idx < len(scores) else 3800.0
        if score > best_score:
            best_idx = idx
            best_score = score
    if best_idx is not None and best_score >= 250.0:
        return StuckRecoveryDecision(True, best_idx, best_score + 600.0, "Stuck detected: evolution is legal and target board is incomplete.")
    return StuckRecoveryDecision(False)


def force_energy(state: Any, options: Sequence[Any], scores: Sequence[float] | None = None) -> StuckRecoveryDecision:
    best_idx: Optional[int] = None
    best_score = -99999.0
    for idx, option in enumerate(options):
        if option_type(option) != OPT_ATTACH:
            continue
        score = scores[idx] if scores is not None and idx < len(scores) else 0.0
        if score > best_score:
            best_idx = idx
            best_score = score
    if best_idx is not None and best_score >= 500.0:
        return StuckRecoveryDecision(True, best_idx, best_score + 300.0, "Stuck detected: useful Energy attachment exists.")
    return StuckRecoveryDecision(False)


def pass_block_score(state: Any) -> float:
    decision = detect_stuck_recovery(state, getattr(state, "options", []) or [])
    return -5000.0 if decision.is_stuck else 0.0
