from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

from state_eval import OPT_CARD, OPT_EVOLVE, OPT_PLAY, card_id, card_id_from_option, getv, hand_cards, iter_in_play, option_type
from core.palafin_planner import FINIZEN, PALAFIN, SECRET_BOX
from core.priority_tables import canonical_name_from_id, context_source_name, count_in_play, has_in_hand


@dataclass(frozen=True)
class PalafinEvolutionGuard:
    should_evolve: bool
    option_index: Optional[int] = None
    score: float = 0.0
    reason: str = ""


def legal_palafin_evolution_choice(state: Any, legal_options: Sequence[Any]) -> PalafinEvolutionGuard:
    best = PalafinEvolutionGuard(False, reason="No legal Finizen to Palafin evolution.")
    for idx, option in enumerate(legal_options):
        if option_type(option) != OPT_EVOLVE or card_id_from_option(state, option) != PALAFIN:
            continue
        target = evolution_target(state, option)
        if canonical_name_from_id(card_id(target)) != "Finizen":
            continue
        score = 7000.0
        if target is not None and target is getv(state, "active"):
            score += 300.0
        best = PalafinEvolutionGuard(True, idx, score, "Evolve Finizen into Palafin before using Secret Box.")
    return best


def palafin_in_hand_count(state: Any) -> int:
    return sum(1 for card in hand_cards(state) if card_id(card) == PALAFIN)


def finizen_can_evolve_to_palafin(state: Any, legal_options: Sequence[Any] | None = None) -> bool:
    if legal_options is not None and legal_palafin_evolution_choice(state, legal_options).should_evolve:
        return True
    return has_in_hand(state, "Palafin") and count_in_play(state, "Finizen") > 0


def score_palafin_discard_guard(state: Any, cid: Optional[int]) -> float:
    if cid != PALAFIN:
        return 0.0
    source = context_source_name(state)
    if source != "Secret Box" and "discard" not in str(source).lower():
        source = source or "discard cost"
    if not finizen_can_evolve_to_palafin(state):
        return 0.0
    if palafin_in_hand_count(state) >= 2:
        return -1200.0
    return -9000.0


def score_before_palafin_evolution_guard(state: Any, option: Any, option_index: int = 0) -> float:
    del option_index
    if not finizen_can_evolve_to_palafin(state, getattr(state, "options", []) or []):
        return 0.0
    typ = option_type(option)
    name = canonical_name_from_id(card_id_from_option(state, option))
    if typ == OPT_EVOLVE and name == "Palafin":
        return 7000.0
    if typ == OPT_PLAY and name == "Lillie's Determination":
        return -5000.0
    if typ == OPT_PLAY and name == "Secret Box" and palafin_in_hand_count(state) <= 1:
        return -9000.0
    return 0.0


def evolution_target(state: Any, option: Any) -> Any:
    from state_eval import attach_target_from_option, get_pokemon_by_area

    target = attach_target_from_option(state, option)
    if target is not None:
        return target
    return get_pokemon_by_area(state, getv(option, "inPlayArea"), getv(option, "inPlayIndex"), state.your_index)


__all__ = [
    "PalafinEvolutionGuard",
    "legal_palafin_evolution_choice",
    "finizen_can_evolve_to_palafin",
    "score_palafin_discard_guard",
    "score_before_palafin_evolution_guard",
]
