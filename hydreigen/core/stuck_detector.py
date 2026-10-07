from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

from action_classifier import ActionCategory, classify_legal_option
from core.action_intent import ActionIntent, ActionIntentType
from state_eval import bench_pokemon, getv
from core.mega_gengar_planner import score_mega_gengar_option
from core.poffin_planner import should_use_poffin_now
from core.pokepad_planner import should_use_pokepad_now
from core.toxtricity_engine_planner import score_toxtricity_option
from core.priority_tables import count_in_play, has_in_play


@dataclass(frozen=True)
class StuckReport:
    is_stuck: bool
    reason: str = ""
    forced_recovery_priority: Optional[ActionIntent] = None


def detect_stalled_setup(memory: Any, state: Any, legal_options: Sequence[Any] | None = None) -> StuckReport:
    del memory
    options = list(legal_options or getattr(state, "options", []) or [])

    poffin = should_use_poffin_now(state, options)
    if poffin.should_act and poffin.option_index is not None:
        return stuck(poffin.option_index, "Buddy-Buddy Poffin", "Stuck detected: setup card available but no board progress.", poffin.score)

    pokepad = should_use_pokepad_now(state, options)
    if pokepad.should_act and pokepad.option_index is not None:
        return stuck(pokepad.option_index, "Poke Pad", "Stuck detected: setup card available but no board progress.", pokepad.score)

    if len(bench_pokemon(state)) < 2 and int(getv(state.current, "turn", 0) or 0) > 4:
        idx = first_category(state, options, ActionCategory.PLAY_BASIC_TO_BENCH)
        if idx is not None:
            return stuck(idx, "Basic Pokemon", "Stuck detected: setup card available but no board progress.", 1600.0)

    if count_in_play(state, "Deino") == 0 and not has_in_play(state, "Gastly") and int(getv(state.current, "turn", 0) or 0) > 4:
        idx = first_category(state, options, ActionCategory.DRAW_OR_SEARCH)
        if idx is not None:
            return stuck(idx, "Search", "Stuck detected: setup card available but no board progress.", 1400.0)

    best_idx = None
    best_score = 0.0
    for idx, option in enumerate(options):
        score = score_mega_gengar_option(state, option, 0.0) + score_toxtricity_option(state, option, 0.0)
        if score > best_score:
            best_idx = idx
            best_score = score
    if best_idx is not None and best_score >= 1800.0:
        return stuck(best_idx, "Recovery plan", "Stuck detected: setup card available but no board progress.", best_score)

    return StuckReport(False)


def stuck(index: int, source: str, reason: str, score: float) -> StuckReport:
    return StuckReport(
        True,
        reason,
        ActionIntent(
            intent_type=ActionIntentType.PLAY_CARD_FROM_HAND,
            selected_option_indices=[int(index)],
            source_card_name=source,
            priority_score=float(score),
            reason="Forced recovery: use Poffin/Poké Pad before passing." if "Poffin" in source or "Pad" in source else reason,
            submission_safe=True,
        ),
    )


def first_category(state: Any, options: Sequence[Any], category: str) -> Optional[int]:
    for idx, option in enumerate(options):
        if classify_legal_option(state, option, idx).category == category:
            return idx
    return None
