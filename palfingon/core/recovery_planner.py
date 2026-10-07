from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from state_eval import OPT_PLAY, card_id_from_option, option_type
from core.palafin_planner import score_recovery_play
from core.priority_tables import canonical_name_from_id


@dataclass(frozen=True)
class RecoveryPlan:
    should_use: bool
    score: float = 0.0
    reason: str = ""


def score_recovery_option(state: Any, option: Any) -> float:
    if option_type(option) != OPT_PLAY:
        return 0.0
    name = canonical_name_from_id(card_id_from_option(state, option))
    if name not in {"Energy Retrieval", "Night Stretcher", "Sacred Ash"}:
        return 0.0
    return score_recovery_play(state, name)


def recovery_plan(state: Any, option: Any) -> RecoveryPlan:
    score = score_recovery_option(state, option)
    name = canonical_name_from_id(card_id_from_option(state, option))
    if score <= 0:
        return RecoveryPlan(False, score, f"Hold {name}; recovery threshold not met.")
    return RecoveryPlan(True, score, f"Use {name} because it restores Palafin/Dragonite attack resources.")
