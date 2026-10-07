from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, List, Optional, Tuple


AREA_DECK = 1
AREA_HAND = 2
AREA_DISCARD = 3
AREA_ACTIVE = 4
AREA_BENCH = 5
AREA_PRIZE = 6
AREA_STADIUM = 7
AREA_ENERGY = 8
AREA_TOOL = 9
AREA_PRE_EVOLUTION = 10
AREA_PLAYER = 11
AREA_LOOKING = 12

SELECT_MAIN = 0
SELECT_CARD = 1
SELECT_ATTACHED_CARD = 2
SELECT_CARD_OR_ATTACHED_CARD = 3
SELECT_ENERGY = 4
SELECT_SKILL = 5
SELECT_ATTACK = 6
SELECT_EVOLVE = 7
SELECT_COUNT = 8
SELECT_YES_NO = 9
SELECT_SPECIAL_CONDITION = 10

CTX_MAIN = 0
CTX_SETUP_ACTIVE = 1
CTX_SETUP_BENCH = 2
CTX_SWITCH = 3
CTX_TO_ACTIVE = 4
CTX_TO_BENCH = 5
CTX_TO_FIELD = 6
CTX_TO_HAND = 7
CTX_DISCARD = 8
CTX_TO_DECK = 9
CTX_TO_DECK_BOTTOM = 10
CTX_TO_PRIZE = 11
CTX_NOT_MOVE = 12
CTX_DAMAGE_COUNTER = 13
CTX_DAMAGE_COUNTER_ANY = 14
CTX_DAMAGE = 15
CTX_REMOVE_DAMAGE_COUNTER = 16
CTX_HEAL = 17
CTX_EVOLVES_FROM = 18
CTX_EVOLVES_TO = 19
CTX_DEVOLVE = 20
CTX_ATTACH_FROM = 21
CTX_ATTACH_TO = 22
CTX_DETACH_FROM = 23
CTX_LOOK = 24
CTX_EFFECT_TARGET = 25
CTX_DISCARD_ENERGY_CARD = 26
CTX_DISCARD_TOOL_CARD = 27
CTX_SWITCH_ENERGY_CARD = 28
CTX_DISCARD_CARD_OR_ATTACHED_CARD = 29
CTX_DISCARD_ENERGY = 30
CTX_TO_HAND_ENERGY = 31
CTX_TO_DECK_ENERGY = 32
CTX_SWITCH_ENERGY = 33
CTX_SKILL_ORDER = 34
CTX_ATTACK = 35
CTX_DISABLE_ATTACK = 36
CTX_EVOLVE = 37
CTX_DRAW_COUNT = 38
CTX_DAMAGE_COUNTER_COUNT = 39
CTX_REMOVE_DAMAGE_COUNTER_COUNT = 40
CTX_IS_FIRST = 41
CTX_MULLIGAN = 42
CTX_ACTIVATE = 43
CTX_FIRST_EFFECT = 44
CTX_MORE_DEVOLVE = 45
CTX_COIN_HEAD = 46
CTX_AFFECT_SPECIAL_CONDITION = 47
CTX_RECOVER_SPECIAL_CONDITION = 48

OPT_NUMBER = 0
OPT_YES = 1
OPT_NO = 2
OPT_CARD = 3
OPT_TOOL_CARD = 4
OPT_ENERGY_CARD = 5
OPT_ENERGY = 6
OPT_PLAY = 7
OPT_ATTACH = 8
OPT_EVOLVE = 9
OPT_ABILITY = 10
OPT_DISCARD = 11
OPT_RETREAT = 12
OPT_ATTACK = 13
OPT_END = 14
OPT_SKILL = 15
OPT_SPECIAL_CONDITION = 16


@dataclass
class NormalizedState:
    obs: Any
    select: Any
    current: Any
    your_index: int
    opponent_index: int

    @property
    def context(self) -> int:
        return enum_int(getv(self.select, "context", CTX_MAIN), CTX_MAIN)

    @property
    def select_type(self) -> int:
        return enum_int(getv(self.select, "type", SELECT_MAIN), SELECT_MAIN)

    @property
    def options(self) -> List[Any]:
        value = getv(self.select, "option", [])
        return value if isinstance(value, list) else []

    @property
    def min_count(self) -> int:
        return max(0, int_or(getv(self.select, "minCount", 0), 0))

    @property
    def max_count(self) -> int:
        option_count = len(self.options)
        raw = int_or(getv(self.select, "maxCount", self.min_count), self.min_count)
        return max(self.min_count, min(option_count, raw))


def normalize_state(obs: Any) -> NormalizedState:
    select = getv(obs, "select")
    current = getv(obs, "current")
    your_index = int_or(getv(current, "yourIndex", 0), 0)
    if your_index not in (0, 1):
        your_index = 0
    return NormalizedState(
        obs=obs,
        select=select,
        current=current,
        your_index=your_index,
        opponent_index=1 - your_index,
    )


def getv(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def int_or(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(getattr(value, "value"))
        except Exception:
            return default


def enum_int(value: Any, default: int = -1) -> int:
    return int_or(value, default)


def option_type(option: Any) -> int:
    return enum_int(getv(option, "type"), -1)


def option_number(option: Any) -> int:
    return int_or(getv(option, "number"), 0)


def player_state(state: NormalizedState, player_index: Optional[int] = None) -> Any:
    current = state.current
    players = getv(current, "players", [])
    idx = state.your_index if player_index is None else player_index
    if isinstance(players, list) and 0 <= idx < len(players):
        return players[idx]
    return None


def active_pokemon(state: NormalizedState, player_index: Optional[int] = None) -> Any:
    player = player_state(state, player_index)
    active = getv(player, "active", [])
    if isinstance(active, list) and active:
        return active[0]
    return None


def bench_pokemon(state: NormalizedState, player_index: Optional[int] = None) -> List[Any]:
    player = player_state(state, player_index)
    bench = getv(player, "bench", [])
    return bench if isinstance(bench, list) else []


def hand_cards(state: NormalizedState, player_index: Optional[int] = None) -> List[Any]:
    player = player_state(state, player_index)
    hand = getv(player, "hand", [])
    return hand if isinstance(hand, list) else []


def discard_cards(state: NormalizedState, player_index: Optional[int] = None) -> List[Any]:
    player = player_state(state, player_index)
    discard = getv(player, "discard", [])
    return discard if isinstance(discard, list) else []


def prize_cards(state: NormalizedState, player_index: Optional[int] = None) -> List[Any]:
    player = player_state(state, player_index)
    prize = getv(player, "prize", [])
    return prize if isinstance(prize, list) else []


def prize_count(state: NormalizedState, player_index: Optional[int] = None) -> int:
    return len(prize_cards(state, player_index))


def deck_count(state: NormalizedState, player_index: Optional[int] = None) -> int:
    player = player_state(state, player_index)
    return int_or(getv(player, "deckCount", 0), 0)


def hand_count(state: NormalizedState, player_index: Optional[int] = None) -> int:
    player = player_state(state, player_index)
    return int_or(getv(player, "handCount", len(hand_cards(state, player_index))), 0)


def bench_space(state: NormalizedState, player_index: Optional[int] = None) -> int:
    player = player_state(state, player_index)
    bench = bench_pokemon(state, player_index)
    bench_max = int_or(getv(player, "benchMax", 5), 5)
    return max(0, bench_max - len(bench))


def card_id(card_or_pokemon: Any) -> Optional[int]:
    if isinstance(card_or_pokemon, int):
        return card_or_pokemon
    if isinstance(card_or_pokemon, str) and card_or_pokemon.isdigit():
        return int(card_or_pokemon)
    value = getv(card_or_pokemon, "id")
    if value is None:
        value = getv(card_or_pokemon, "cardId")
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def pokemon_hp(pokemon: Any) -> int:
    return int_or(getv(pokemon, "hp"), 0)


def pokemon_max_hp(pokemon: Any) -> int:
    return int_or(getv(pokemon, "maxHp"), 0)


def pokemon_damage(pokemon: Any) -> int:
    max_hp = pokemon_max_hp(pokemon)
    hp = pokemon_hp(pokemon)
    return max(0, max_hp - hp) if max_hp else 0


def pokemon_energy_count(pokemon: Any) -> int:
    energies = getv(pokemon, "energies", [])
    if isinstance(energies, list) and energies:
        return len(energies)
    energy_cards = getv(pokemon, "energyCards", [])
    return len(energy_cards) if isinstance(energy_cards, list) else 0


def attached_card_ids(pokemon: Any, attr: str) -> List[int]:
    cards = getv(pokemon, attr, [])
    if not isinstance(cards, list):
        return []
    ids = []
    for card in cards:
        cid = card_id(card)
        if cid is not None:
            ids.append(cid)
    return ids


def iter_in_play(state: NormalizedState, player_index: Optional[int] = None) -> Iterable[Tuple[int, int, Any]]:
    idx = state.your_index if player_index is None else player_index
    active = active_pokemon(state, idx)
    if active is not None:
        yield (AREA_ACTIVE, 0, active)
    for bench_index, pokemon in enumerate(bench_pokemon(state, idx)):
        yield (AREA_BENCH, bench_index, pokemon)


def get_pokemon_by_area(state: NormalizedState, area: Any, index: Any, player_index: Optional[int] = None) -> Any:
    area_int = enum_int(area, -1)
    idx = int_or(index, 0)
    player_idx = state.your_index if player_index is None else player_index
    if area_int == AREA_ACTIVE:
        active = active_pokemon(state, player_idx)
        return active if idx == 0 else None
    if area_int == AREA_BENCH:
        bench = bench_pokemon(state, player_idx)
        return bench[idx] if 0 <= idx < len(bench) else None
    return None


def get_card_from_area(state: NormalizedState, area: Any, index: Any, player_index: Optional[int] = None) -> Any:
    area_int = enum_int(area, -1)
    idx = int_or(index, 0)
    player_idx = state.your_index if player_index is None else player_index
    if area_int == AREA_HAND:
        cards = hand_cards(state, player_idx)
    elif area_int == AREA_DISCARD:
        cards = discard_cards(state, player_idx)
    elif area_int == AREA_PRIZE:
        cards = prize_cards(state, player_idx)
    elif area_int == AREA_STADIUM:
        cards = getv(state.current, "stadium", [])
    elif area_int == AREA_DECK:
        cards = getv(state.select, "deck", []) or []
    elif area_int == AREA_LOOKING:
        cards = getv(state.current, "looking", []) or []
    elif area_int in (AREA_ACTIVE, AREA_BENCH):
        return get_pokemon_by_area(state, area_int, idx, player_idx)
    else:
        cards = []
    if isinstance(cards, list) and 0 <= idx < len(cards):
        return cards[idx]
    return None


def card_id_from_option(state: NormalizedState, option: Any) -> Optional[int]:
    for key in ("cardId", "cardID", "card_id", "sourceCardId", "sourceId", "contextCardId", "effectCardId"):
        explicit = getv(option, key)
        if explicit is not None:
            return int_or(explicit, 0)
    if option_type(option) in (OPT_PLAY, OPT_ATTACH, OPT_EVOLVE, OPT_CARD):
        explicit_id = getv(option, "id")
        if explicit_id is not None:
            parsed = int_or(explicit_id, -1)
            if parsed >= 0:
                return parsed
    for key in ("card", "sourceCard", "contextCard", "effectCard", "pokemon", "item"):
        cid = card_id(getv(option, key))
        if cid is not None:
            return cid
    player_idx = getv(option, "playerIndex")
    if player_idx is None:
        player_idx = state.your_index
    area = getv(option, "area")
    if area is None and option_type(option) in (OPT_PLAY, OPT_ATTACH, OPT_EVOLVE):
        area = AREA_HAND
    card = get_card_from_area(state, area, getv(option, "index"), int_or(player_idx, state.your_index))
    cid = card_id(card)
    if cid is not None:
        return cid
    if option_type(option) in (OPT_PLAY, OPT_CARD):
        for key in ("cardName", "name", "label", "text"):
            cid = card_id_from_text(getv(option, key))
            if cid is not None:
                return cid
    return None


def card_id_from_text(value: Any) -> Optional[int]:
    text = str(value or "").strip()
    if not text:
        return None
    lowered = text.lower()
    try:
        from card_db import get_db

        cards = sorted(get_db().cards.values(), key=lambda info: len(info.name), reverse=True)
        exact = {card.name.lower(): card.card_id for card in cards}
        if lowered in exact:
            return exact[lowered]
        for card in cards:
            name = card.name.lower()
            if name and name in lowered:
                return card.card_id
    except Exception:
        pass
    try:
        from core.priority_tables import CARD_IDS, canonical_name

        canonical = canonical_name(text)
        if canonical in CARD_IDS:
            return CARD_IDS[canonical]
        lowered_canonical = canonical.lower()
        for name, cid in sorted(CARD_IDS.items(), key=lambda item: len(item[0]), reverse=True):
            if name.lower() in lowered_canonical:
                return cid
    except Exception:
        pass
    return None


def pokemon_from_card_option(state: NormalizedState, option: Any) -> Any:
    player_idx = int_or(getv(option, "playerIndex", state.your_index), state.your_index)
    return get_pokemon_by_area(state, getv(option, "area"), getv(option, "index"), player_idx)


def attach_target_from_option(state: NormalizedState, option: Any) -> Any:
    player_idx = state.your_index
    return get_pokemon_by_area(state, getv(option, "inPlayArea"), getv(option, "inPlayIndex"), player_idx)


def attached_card_id_from_option(state: NormalizedState, option: Any) -> Optional[int]:
    pokemon = pokemon_from_card_option(state, option)
    if pokemon is None:
        pokemon = active_pokemon(state)
    if pokemon is None:
        return None
    opt_type = option_type(option)
    if opt_type == OPT_TOOL_CARD:
        idx = int_or(getv(option, "toolIndex"), 0)
        tools = getv(pokemon, "tools", [])
        if isinstance(tools, list) and 0 <= idx < len(tools):
            return card_id(tools[idx])
    if opt_type in (OPT_ENERGY_CARD, OPT_ENERGY):
        idx = int_or(getv(option, "energyIndex"), 0)
        energy_cards = getv(pokemon, "energyCards", [])
        if isinstance(energy_cards, list) and 0 <= idx < len(energy_cards):
            return card_id(energy_cards[idx])
    return None


def count_card_in_cards(cards: Iterable[Any], wanted_id: int) -> int:
    return sum(1 for card in cards if card_id(card) == wanted_id)


def count_card_in_discard(state: NormalizedState, wanted_id: int, player_index: Optional[int] = None) -> int:
    return count_card_in_cards(discard_cards(state, player_index), wanted_id)


def count_seen_card(state: NormalizedState, wanted_id: int, player_index: Optional[int] = None) -> int:
    idx = state.your_index if player_index is None else player_index
    count = 0
    count += count_card_in_cards(hand_cards(state, idx), wanted_id)
    count += count_card_in_cards(discard_cards(state, idx), wanted_id)
    count += count_card_in_cards([c for c in prize_cards(state, idx) if c is not None], wanted_id)
    for _, _, pokemon in iter_in_play(state, idx):
        if card_id(pokemon) == wanted_id:
            count += 1
        count += sum(1 for cid in attached_card_ids(pokemon, "energyCards") if cid == wanted_id)
        count += sum(1 for cid in attached_card_ids(pokemon, "tools") if cid == wanted_id)
        pre_evolution = getv(pokemon, "preEvolution", [])
        if isinstance(pre_evolution, list):
            count += count_card_in_cards(pre_evolution, wanted_id)
    stadium = getv(state.current, "stadium", [])
    if isinstance(stadium, list):
        count += count_card_in_cards(stadium, wanted_id)
    return count


def player_has_condition(state: NormalizedState, condition_name: str, player_index: Optional[int] = None) -> bool:
    player = player_state(state, player_index)
    return bool(getv(player, condition_name, False))
