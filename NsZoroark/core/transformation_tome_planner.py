from __future__ import annotations

from typing import Any, Optional

from card_db import get_db
from state_eval import OPT_CARD, OPT_PLAY, card_id, card_id_from_option, discard_cards, getv, hand_cards, option_type
from core.priority_tables import canonical_name, canonical_name_from_id, context_source_name, count_in_play
from core.target_board import PECHARUNT_EX, ZEKROM, ZORUA


def score_transformation_tome_option(state: Any, option: Any) -> float:
    if option_type(option) != OPT_PLAY or option_name(state, option) != "Transformation Tome":
        return 0.0
    if not tome_pair_available(state, option):
        return -6000.0
    if meaningful_basic_swap_exists(state):
        return 5400.0
    return -3500.0


def score_transformation_tome_selection_zoroark(state: Any, cid: Optional[int]) -> float:
    if context_source_name(state) != "Transformation Tome":
        return 0.0
    name = canonical_name_from_id(cid)
    if name == ZEKROM and count_in_play(state, ZEKROM) == 0:
        return 6800.0
    if name == ZORUA and count_in_play(state, ZORUA) < 2:
        return 6200.0
    if name == PECHARUNT_EX:
        return 3200.0
    card = get_db().get_card(cid)
    if card and card.card_type == "Pokemon" and card.basic:
        return 800.0
    return -2500.0


def tome_pair_available(state: Any, option: Any = None) -> bool:
    if option is not None:
        text = " ".join(str(getv(option, key, "") or "") for key in ("text", "label", "description", "name")).lower()
        if "two" in text or "2" in text or "pair" in text:
            return True
    return count_named_cards(hand_cards(state), "Transformation Tome") >= 2


def meaningful_basic_swap_exists(state: Any) -> bool:
    discard_names = {canonical_name_from_id(card_id(card)) for card in discard_cards(state)}
    if ZEKROM in discard_names and count_in_play(state, ZEKROM) == 0:
        return True
    if ZORUA in discard_names and count_in_play(state, ZORUA) < 2:
        return True
    return PECHARUNT_EX in discard_names


def count_named_cards(cards: Any, wanted: str) -> int:
    return sum(1 for card in cards if canonical_name_from_id(card_id(card)) == wanted or canonical_name(str(getv(card, "name", ""))) == wanted)


def option_name(state: Any, option: Any) -> str:
    name = canonical_name_from_id(card_id_from_option(state, option))
    if name:
        return name
    text = " ".join(str(getv(option, key, "") or "") for key in ("cardName", "name", "label", "text"))
    if "Transformation Tome" in text:
        return "Transformation Tome"
    return canonical_name(text)
