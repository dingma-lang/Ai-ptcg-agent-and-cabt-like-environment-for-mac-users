from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.pokepad_dragonite_planner import dratini_in_play, needed_non_rulebox_evolution_piece
from core.priority_tables import has_in_hand


@dataclass(frozen=True)
class PetrelSearchScore:
    score: float
    reason: str


def score_petrel_exact_target(state: Any, target_name: str) -> PetrelSearchScore:
    if target_name != "Poke Pad":
        return PetrelSearchScore(0.0, "")
    if has_in_hand(state, "Poke Pad"):
        return PetrelSearchScore(-7000.0, "Do not Petrel for Poké Pad because Poké Pad is already in hand.")
    needed = needed_non_rulebox_evolution_piece(state)
    if needed == "Palafin":
        return PetrelSearchScore(5200.0, "Use Petrel to find Poké Pad because we need a non-Rule Box evolution piece.")
    if needed == "Dragonair" and not dratini_in_play(state):
        return PetrelSearchScore(-7000.0, "Do not find Poké Pad for Dragonair before Dratini is actually in play.")
    if needed in {"Dratini", "Dragonair", "Tatsugiri"}:
        return PetrelSearchScore(4200.0, "Use Petrel to find Poké Pad because we need a non-Rule Box evolution piece.")
    return PetrelSearchScore(-7000.0, "Do not use Poké Pad for Rule Box evolution target.")


__all__ = ["PetrelSearchScore", "score_petrel_exact_target"]
