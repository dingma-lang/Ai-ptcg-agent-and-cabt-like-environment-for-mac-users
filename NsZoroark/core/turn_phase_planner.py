from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from state_eval import bench_pokemon, getv, prize_count
from core.danger_evaluator import evaluate_danger
from core.round_plan import EARLY, LATE, MID, build_round_plan


@dataclass(frozen=True)
class TurnPhase:
    stage: str
    turn_number: int
    bench_count: int
    danger_level: str
    is_opening: bool
    is_rebuild: bool
    is_late: bool


def plan_turn_phase(state: Any) -> TurnPhase:
    round_plan = build_round_plan(state, None, None)
    turn = int(getv(state.current, "turn", 0) or 0)
    danger = evaluate_danger(state)
    bench_count = len(bench_pokemon(state))
    return TurnPhase(
        stage=round_plan.game_stage,
        turn_number=turn,
        bench_count=bench_count,
        danger_level=danger.severity,
        is_opening=round_plan.game_stage == EARLY or turn <= 4,
        is_rebuild=danger.ko_last_turn,
        is_late=round_plan.game_stage == LATE or prize_count(state) <= 2 or prize_count(state, state.opponent_index) <= 2,
    )
