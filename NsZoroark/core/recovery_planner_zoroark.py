from __future__ import annotations

from typing import Any, Optional

from state_eval import OPT_PLAY, card_id, card_id_from_option, discard_cards, option_type
from core.energy_planner_zoroark import darkness_in_discard
from core.priority_tables import canonical_name_from_id, count_in_play, context_source_name
from core.target_board import DARKNESS_ENERGY_ID, DARMANITAN, DARUMAKA, PECHARUNT_EX, ZEKROM, ZOROARK_EX, ZORUA


def score_recovery_option_zoroark(state: Any, option: Any) -> float:
    if option_type(option) != OPT_PLAY:
        return 0.0
    name = canonical_name_from_id(card_id_from_option(state, option))
    if name == "Night Stretcher":
        return score_night_stretcher_play(state)
    if name == "Sacred Ash":
        return score_sacred_ash_play(state)
    if name == "N's PP Up":
        try:
            from core.energy_planner_zoroark import score_ns_pp_up_option

            return score_ns_pp_up_option(state, option)
        except Exception:
            return 0.0
    return 0.0


def score_recovery_selection_zoroark(state: Any, cid: Optional[int]) -> float:
    name = canonical_name_from_id(cid)
    source = context_source_name(state)
    if source == "Night Stretcher":
        if cid == DARKNESS_ENERGY_ID:
            return 6200.0 if darkness_in_discard(state) > 0 and zoroark_needs_energy(state) else 600.0
        if name == ZOROARK_EX:
            return 7000.0 if count_in_play(state, ZORUA) > count_in_play(state, ZOROARK_EX) else 1800.0
        if name == ZORUA:
            return 6200.0 if count_in_play(state, ZORUA) == 0 else 1400.0
        if name == ZEKROM:
            return 5600.0 if count_in_play(state, ZEKROM) == 0 else 900.0
        if name in {DARUMAKA, DARMANITAN}:
            return 2800.0
        if name == PECHARUNT_EX:
            return 2600.0
    if source == "Sacred Ash":
        if name in {ZORUA, ZOROARK_EX, ZEKROM, DARUMAKA, DARMANITAN}:
            return 5200.0
        return 900.0
    return 0.0


def score_night_stretcher_play(state: Any) -> float:
    if exact_recovery_needed(state):
        return 5200.0
    return -900.0


def score_sacred_ash_play(state: Any) -> float:
    pokemon_count = pokemon_discard_count(state)
    if pokemon_count >= 4 or key_line_lost(state):
        return 4800.0
    return -2600.0


def exact_recovery_needed(state: Any) -> bool:
    return (
        zoroark_needs_energy(state) and darkness_in_discard(state) > 0
        or count_in_play(state, ZORUA) == 0 and discard_count_by_name(state, ZORUA) > 0
        or count_in_play(state, ZEKROM) == 0 and discard_count_by_name(state, ZEKROM) > 0
    )


def zoroark_needs_energy(state: Any) -> bool:
    try:
        from core.energy_planner_zoroark import ready_zoroark_available

        return not ready_zoroark_available(state)
    except Exception:
        return True


def pokemon_discard_count(state: Any) -> int:
    return sum(1 for card in discard_cards(state) if (getattr(get_db_card(card_id(card)), "card_type", "") == "Pokemon"))


def key_line_lost(state: Any) -> bool:
    return discard_count_by_name(state, ZORUA) >= 3 or discard_count_by_name(state, ZOROARK_EX) >= 3 or discard_count_by_name(state, ZEKROM) >= 2


def discard_count_by_name(state: Any, name: str) -> int:
    return sum(1 for card in discard_cards(state) if canonical_name_from_id(card_id(card)) == name)


def get_db_card(cid: Optional[int]) -> Any:
    from card_db import get_db

    return get_db().get_card(cid)
