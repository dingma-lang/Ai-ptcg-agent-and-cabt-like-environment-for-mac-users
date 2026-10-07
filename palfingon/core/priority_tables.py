from __future__ import annotations

from typing import Any, Iterable, List, Optional

from card_db import get_db
from state_eval import active_pokemon, bench_pokemon, card_id, getv, hand_cards, iter_in_play


CARD_IDS = {
    "Finizen": 105,
    "Palafin": 106,
    "Palafin TEF 49": 51,
    "Palafin ex": 107,
    "Tatsugiri": 122,
    "Dratini": 902,
    "Dragonair": 903,
    "Mega Dragonite ex": 904,
    "Buddy-Buddy Poffin": 1086,
    "Poke Pad": 1152,
    "Poké Pad": 1152,
    "Lillie's Determination": 1227,
    "Crispin": 1198,
    "Boss's Orders": 1182,
    "Boss’s Orders": 1182,
    "Secret Box": 1092,
    "Switch": 1123,
    "Night Stretcher": 1097,
    "Energy Retrieval": 1118,
    "Surfing Beach": 1262,
    "Air Balloon": 1174,
    "Team Rocket's Petrel": 1219,
    "Hilda": 1225,
    "Judge": 1213,
    "Battle Cage": 1264,
    "Basic Water Energy": 3,
    "Basic Lightning Energy": 4,
}

ENERGY_NAMES_BY_ID = {
    3: "Basic Water Energy",
    4: "Basic Lightning Energy",
}

PALAFIN_LINE_IDS = {51, 105, 106, 107}
DRAGONITE_LINE_IDS = {902, 903, 904}
PALAKING_SETUP_BASIC_IDS = {105, 902, 122}
SETUP_BASIC_IDS = {105, 902, 122}
SUPPORT_LIABILITY_IDS = set()
PROTECTED_IDS = {51, 105, 106, 107, 902, 903, 904, 3, 4, 1092, 1118, 1097, 1174, 1198, 1225, 1262}
LOW_PRIORITY_DISCARD_IDS = {1174, 1219, 1086}
RULE_BOX_IDS = {107, 904}


def canonical_name_from_id(cid: Optional[int]) -> str:
    if cid is None:
        return ""
    # Strategy identity differs even though both variants share a printed name.
    if cid == 51:
        return "Palafin TEF 49"
    if cid in ENERGY_NAMES_BY_ID:
        return ENERGY_NAMES_BY_ID[cid]
    card = get_db().get_card(cid)
    if not card:
        return ""
    return canonical_name(card.name)


def canonical_name(name: str) -> str:
    text = str(name or "")
    replacements = {
        "Basic {W} Energy": "Basic Water Energy",
        "Basic {L} Energy": "Basic Lightning Energy",
        "Boss’s Orders": "Boss's Orders",
        "Poké Pad": "Poke Pad",
    }
    return replacements.get(text, text)


def card_id_for_name(name: str) -> Optional[int]:
    return CARD_IDS.get(name) or CARD_IDS.get(canonical_name(name))


def hand_ids(state: Any) -> List[int]:
    return [cid for cid in (card_id(card) for card in hand_cards(state)) if cid is not None]


def hand_names(state: Any) -> List[str]:
    return [canonical_name_from_id(cid) for cid in hand_ids(state)]


def in_play_ids(state: Any, player_index: Optional[int] = None) -> List[int]:
    return [cid for cid in (card_id(pokemon) for _, _, pokemon in iter_in_play(state, player_index)) if cid is not None]


def in_play_names(state: Any, player_index: Optional[int] = None) -> List[str]:
    return [canonical_name_from_id(cid) for cid in in_play_ids(state, player_index)]


def count_in_play(state: Any, name_or_id: Any) -> int:
    wanted = name_or_id if isinstance(name_or_id, int) else card_id_for_name(str(name_or_id))
    if wanted is None:
        return 0
    return sum(1 for cid in in_play_ids(state) if cid == wanted)


def has_in_play(state: Any, name_or_id: Any) -> bool:
    return count_in_play(state, name_or_id) > 0


def has_in_hand(state: Any, name_or_id: Any) -> bool:
    wanted = name_or_id if isinstance(name_or_id, int) else card_id_for_name(str(name_or_id))
    return wanted in hand_ids(state) if wanted is not None else False


def bench_is_weak(state: Any) -> bool:
    ids = in_play_ids(state)
    return 105 not in ids or len([cid for cid in ids if cid in SETUP_BASIC_IDS]) == 0


def option_card_name(state: Any, option: Any, cid: Optional[int]) -> str:
    if cid is None:
        return ""
    return canonical_name_from_id(cid)


def context_source_name(state: Any) -> str:
    for key in ("effect", "contextCard", "effectCard", "sourceCard", "source", "card"):
        cid = card_id(getv(state.select, key))
        if cid is not None:
            return canonical_name_from_id(cid)
    for key in ("effectCardId", "contextCardId", "sourceCardId", "sourceId", "cardId"):
        cid = card_id(getv(state.select, key))
        if cid is not None:
            return canonical_name_from_id(cid)
    for key in ("effectName", "contextCardName", "sourceCardName", "sourceName", "cardName", "name"):
        value = getv(state.select, key)
        if value:
            return canonical_name(str(value))
    logs = getv(state.obs, "logs", []) or []
    if isinstance(logs, list):
        for log in reversed(logs):
            cid = getv(log, "cardId")
            if cid is not None:
                return canonical_name_from_id(int(cid))
    return ""


def active_name(state: Any) -> str:
    return canonical_name_from_id(card_id(active_pokemon(state)))


def bench_names(state: Any) -> List[str]:
    return [canonical_name_from_id(card_id(pokemon)) for pokemon in bench_pokemon(state)]


def any_name(names: Iterable[str], wanted: Iterable[str]) -> bool:
    wanted_set = {canonical_name(name) for name in wanted}
    return any(canonical_name(name) in wanted_set for name in names)
