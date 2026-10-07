from __future__ import annotations

from typing import Any, Iterable, List, Optional

from card_db import get_db
from state_eval import active_pokemon, bench_pokemon, card_id, getv, hand_cards, iter_in_play


CARD_IDS = {
    "N's Zorua": 292,
    "N’s Zorua": 292,
    "N's Zoroark ex": 293,
    "N’s Zoroark ex": 293,
    "N's Zekrom": 906,
    "N’s Zekrom": 906,
    "N's Reshiram": 303,
    "N’s Reshiram": 303,
    "N's Darumaka": 257,
    "N’s Darumaka": 257,
    "N's Darmanitan": 258,
    "N’s Darmanitan": 258,
    "Yveltal": 689,
    "Munkidori": 112,
    "Fezandipiti ex": 140,
    "Pecharunt ex": 141,
    "Buddy-Buddy Poffin": 1086,
    "Poke Pad": 1152,
    "Poké Pad": 1152,
    "Lillie's Determination": 1227,
    "Cyrano": 1205,
    "Ciphermaniac's Codebreaking": 1188,
    "Ciphermaniac’s Codebreaking": 1188,
    "Black Belt's Training": 1211,
    "Black Belt’s Training": 1211,
    "Boss's Orders": 1182,
    "Boss’s Orders": 1182,
    "Night Stretcher": 1097,
    "Air Balloon": 1174,
    "Tool Scrapper": 1137,
    "Unfair Stamp": 1080,
    "N's PP Up": 1113,
    "N’s PP Up": 1113,
    "Binding Mochi": 1162,
    "N's Castle": 1253,
    "N’s Castle": 1253,
    "Team Rocket's Watchtower": 1256,
    "Team Rocket’s Watchtower": 1256,
    "Basic Darkness Energy": 7,
}

ENERGY_NAMES_BY_ID = {
    7: "Basic Darkness Energy",
}

NS_ZOROARK_LINE_IDS = {292, 293}
NS_COPY_SOURCE_IDS = {906, 303, 257, 258}
SETUP_BASIC_IDS = {292, 906, 303, 257, 689, 112}
SUPPORT_LIABILITY_IDS = {140, 141}
PROTECTED_IDS = {292, 293, 906, 303, 1113, 1253, 7, 1080}
LOW_PRIORITY_DISCARD_IDS = {1174, 7, 1086}
RULE_BOX_IDS = {293, 140, 141}


def canonical_name_from_id(cid: Optional[int]) -> str:
    if cid is None:
        return ""
    if cid in ENERGY_NAMES_BY_ID:
        return ENERGY_NAMES_BY_ID[cid]
    card = get_db().get_card(cid)
    if not card:
        return ""
    return canonical_name(card.name)


def canonical_name(name: str) -> str:
    text = str(name or "").replace("’", "'")
    replacements = {
        "Basic {D} Energy": "Basic Darkness Energy",
        "Boss’s Orders": "Boss's Orders",
        "Poké Pad": "Poke Pad",
        "N’s Zorua": "N's Zorua",
        "N’s Zoroark ex": "N's Zoroark ex",
        "N’s Zekrom": "N's Zekrom",
        "N’s Reshiram": "N's Reshiram",
        "N’s Darumaka": "N's Darumaka",
        "N’s Darmanitan": "N's Darmanitan",
        "N’s PP Up": "N's PP Up",
        "N’s Castle": "N's Castle",
        "Team Rocket’s Watchtower": "Team Rocket's Watchtower",
        "Ciphermaniac’s Codebreaking": "Ciphermaniac's Codebreaking",
        "Black Belt’s Training": "Black Belt's Training",
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
    return 292 not in ids or len([cid for cid in ids if cid in SETUP_BASIC_IDS]) == 0


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
