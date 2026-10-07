from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

from state_eval import OPT_ABILITY, OPT_ATTACH, OPT_EVOLVE, OPT_PLAY, card_id_from_option, option_type
from core.priority_tables import canonical_name_from_id


@dataclass(frozen=True)
class StuckRecoveryDecision:
    is_stuck: bool
    option_index: Optional[int] = None
    score: float = 0.0
    reason: str = ""


def detect_stuck_recovery(state: Any, legal_options: Sequence[Any] | None = None, scores: Sequence[float] | None = None) -> StuckRecoveryDecision:
    del scores
    options = list(legal_options or getattr(state, "options", []) or [])
    return detect_palaking_stuck_recovery(state, options)


def pass_block_score(state: Any) -> float:
    decision = detect_stuck_recovery(state, getattr(state, "options", []) or [])
    return -5000.0 if decision.is_stuck else 0.0


def detect_palaking_stuck_recovery(state: Any, options: Sequence[Any]) -> StuckRecoveryDecision:
    try:
        from core.palafin_planner import score_palaking_option, palafin_reason_for_option
    except Exception:
        return StuckRecoveryDecision(False)

    best = StuckRecoveryDecision(False, reason="No Palaking stuck action.")
    for idx, option in enumerate(options):
        score = score_palaking_option(state, option, 0.0, idx)
        if score < 3000.0:
            continue
        name = canonical_name_from_id(card_id_from_option(state, option))
        typ = option_type(option)
        forced = typ in (OPT_PLAY, OPT_EVOLVE, OPT_ATTACH, OPT_ABILITY) or name in {
            "Buddy-Buddy Poffin",
            "Poke Pad",
            "Secret Box",
            "Surfing Beach",
            "Switch",
            "Hilda",
            "Crispin",
            "Lillie's Determination",
        }
        if not forced:
            continue
        if score > best.score:
            best = StuckRecoveryDecision(True, idx, score + 900.0, f"Palaking stuck recovery: {palafin_reason_for_option(state, option)}")
    return best
