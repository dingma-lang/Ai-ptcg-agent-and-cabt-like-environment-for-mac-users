from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from state_eval import OPT_PLAY, card_id_from_option, option_type
from core.priority_tables import canonical_name_from_id


@dataclass(frozen=True)
class CrispinPlan:
    should_use: bool
    score: float = 0.0
    reason: str = ""


def palaking_crispin_plan(state: Any) -> CrispinPlan:
    try:
        from core.palafin_planner import score_crispin_play

        score = score_crispin_play(state)
    except Exception:
        score = 0.0
    if score <= 0.0:
        return CrispinPlan(False, score, "Crispin has no Palaking Energy target right now.")
    return CrispinPlan(True, score, "Use Crispin for the current Palaking Energy plan.")


def score_crispin_option(state: Any, option: Any) -> float:
    if option_type(option) != OPT_PLAY or canonical_name_from_id(card_id_from_option(state, option)) != "Crispin":
        return 0.0
    return palaking_crispin_plan(state).score


def score_crispin_energy_selection(state: Any, cid: Optional[int]) -> float:
    try:
        from core.palafin_planner import score_crispin_target

        return score_crispin_target(state, cid, canonical_name_from_id(cid))
    except Exception:
        return 0.0
