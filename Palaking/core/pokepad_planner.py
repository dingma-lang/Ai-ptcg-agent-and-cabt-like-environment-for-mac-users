from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

from state_eval import OPT_CARD, OPT_PLAY, card_id_from_option, option_type
from core.priority_tables import canonical_name_from_id, context_source_name, count_in_play, has_in_hand
from core.strategy_scope import use_palaking_strategy


@dataclass(frozen=True)
class Decision:
    should_act: bool
    score: float = 0.0
    option_index: Optional[int] = None
    reason: str = ""


def should_use_pokepad_now(state: Any, legal_options: Sequence[Any] | None = None) -> Decision:
    options = list(legal_options or getattr(state, "options", []) or [])
    idx = pokepad_option_index(state, options)
    if idx is None:
        return Decision(False, reason="Poke Pad is not legal.")
    score = pokepad_need_score(state)
    if score <= 0:
        return Decision(False, score, idx, "No Palaking non-Rule Box target needed.")
    return Decision(True, score, idx, "Use Poke Pad for Palafin, Finizen, Dratini, or Dragonair.")


def score_pokepad_play(state: Any, option: Any) -> float:
    if canonical_name_from_id(card_id_from_option(state, option)) != "Poke Pad":
        return 0.0
    decision = should_use_pokepad_now(state)
    return decision.score if decision.should_act else 0.0


def score_pokepad_target(state: Any, cid: Optional[int]) -> float:
    if use_palaking_strategy(state):
        from core.palafin_planner import score_pokepad_target as palaking_pokepad_target

        return palaking_pokepad_target(state, cid, canonical_name_from_id(cid))
    return 0.0


def pokepad_need_score(state: Any) -> float:
    from core.palafin_planner import dragonite_line_count, has_ready_finizen_for_palafin, palafin_line_count, supporter_access_needed

    if dragonite_line_count(state) == 0 and not has_in_hand(state, "Dratini"):
        return 7600.0
    if has_ready_finizen_for_palafin(state):
        return 6200.0
    if palafin_line_count(state) == 0:
        return 5200.0
    if count_in_play(state, "Dratini") > 0 and count_in_play(state, "Dragonair") == 0:
        return 3900.0
    if supporter_access_needed(state):
        return 2500.0
    return 0.0


def pokepad_option_index(state: Any, options: Sequence[Any]) -> Optional[int]:
    for idx, option in enumerate(options):
        if option_type(option) == OPT_PLAY and canonical_name_from_id(card_id_from_option(state, option)) == "Poke Pad":
            return idx
    return None


def is_pokepad_search_context(state: Any) -> bool:
    return context_source_name(state) == "Poke Pad"


def pokepad_search_has_setup_target(state: Any) -> bool:
    if not is_pokepad_search_context(state):
        return False
    for option in getattr(state, "options", []) or []:
        if option_type(option) != OPT_CARD:
            continue
        if score_pokepad_target(state, card_id_from_option(state, option)) > 0:
            return True
    return False
