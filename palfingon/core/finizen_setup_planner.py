from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

from card_db import get_db
from state_eval import OPT_PLAY, bench_space, card_id_from_option, option_type
from core.palafin_planner import FINIZEN, palafin_line_count
from core.priority_tables import canonical_name_from_id, count_in_play


@dataclass(frozen=True)
class FinizenSetupChoice:
    should_act: bool
    option_index: Optional[int] = None
    score: float = 0.0
    reason: str = ""


def choose_finizen_bench_before_search(state: Any, legal_options: Sequence[Any]) -> FinizenSetupChoice:
    if bench_space(state) <= 0:
        return FinizenSetupChoice(False, reason="Bench is full.")
    in_play = count_in_play(state, "Finizen")
    if in_play >= 2:
        return FinizenSetupChoice(False, reason="Finizen setup is stable; Poké Pad can now search Dragonite line.")
    for idx, option in enumerate(legal_options):
        if option_type(option) == OPT_PLAY and card_id_from_option(state, option) == FINIZEN:
            try:
                from core.turn_plan import controlled_basic_bench_score

                score = controlled_basic_bench_score(state, "Finizen")
            except Exception:
                score = 6500.0 if in_play == 0 else 5500.0
            if score < 900.0:
                return FinizenSetupChoice(False, idx, score, "Hold extra Finizen because Bench space or switch route is more valuable.")
            return FinizenSetupChoice(True, idx, score, "Bench Finizen from hand before using Poké Pad.")
    return FinizenSetupChoice(False, reason="No Finizen bench option.")


def score_finizen_setup_order(state: Any, option: Any) -> float:
    if bench_space(state) <= 0 or count_in_play(state, "Finizen") >= 2:
        return 0.0
    name = canonical_name_from_id(card_id_from_option(state, option))
    typ = option_type(option)
    if typ == OPT_PLAY and name == "Finizen":
        try:
            from core.turn_plan import controlled_basic_bench_score

            return controlled_basic_bench_score(state, "Finizen")
        except Exception:
            return 6500.0 if count_in_play(state, "Finizen") == 0 else 5500.0
    if typ == OPT_PLAY and name == "Poke Pad":
        return -4000.0
    return 0.0


def finizen_setup_stable(state: Any) -> bool:
    return count_in_play(state, "Finizen") >= 2 or palafin_line_count(state) >= 2


__all__ = ["FinizenSetupChoice", "choose_finizen_bench_before_search", "score_finizen_setup_order", "finizen_setup_stable"]
