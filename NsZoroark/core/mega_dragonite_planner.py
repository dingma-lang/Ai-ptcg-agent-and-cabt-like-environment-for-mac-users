from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

from state_eval import OPT_ATTACK, OPT_ATTACH, OPT_EVOLVE, OPT_PLAY, card_id_from_option, option_type
from core.palafin_planner import score_palaking_option
from core.priority_tables import canonical_name_from_id


@dataclass(frozen=True)
class MegaDragonitePlan:
    should_act: bool
    option_index: Optional[int] = None
    score: float = 0.0
    reason: str = ""


def score_mega_dragonite_plan(state: Any, legal_options: Sequence[Any]) -> MegaDragonitePlan:
    best = MegaDragonitePlan(False, reason="No Mega Dragonite line action.")
    for idx, option in enumerate(legal_options):
        name = canonical_name_from_id(card_id_from_option(state, option))
        typ = option_type(option)
        if name not in {"Dratini", "Dragonair", "Mega Dragonite ex", "Basic Lightning Energy", "Basic Water Energy", "Crispin", "Hilda"} and typ != OPT_ATTACK:
            continue
        score = score_palaking_option(state, option, 0.0, idx)
        if score > best.score:
            reason = "Build Dragonite line in the background."
            if typ == OPT_ATTACH:
                reason = "Attach Lightning to the Dragonite line."
            elif typ == OPT_EVOLVE:
                reason = "Evolve the Dragonite line when useful."
            elif typ == OPT_ATTACK:
                reason = "Use Mega Dragonite ex only for KO, win, or major threat removal."
            best = MegaDragonitePlan(score > 0.0, idx, score, reason)
    return best


def score_mega_dragonite_option(state: Any, option: Any, option_index: int = 0) -> float:
    plan = score_mega_dragonite_plan(state, getattr(state, "options", []) or [])
    return plan.score if plan.option_index == option_index else 0.0
