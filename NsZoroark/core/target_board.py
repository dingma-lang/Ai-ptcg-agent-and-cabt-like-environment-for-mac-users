from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, List, Optional

from state_eval import (
    active_pokemon,
    attached_card_ids,
    bench_pokemon,
    bench_space,
    card_id,
    discard_cards,
    getv,
    hand_cards,
    iter_in_play,
    pokemon_energy_count,
    prize_count,
)
from core.priority_tables import canonical_name_from_id


ZORUA = "N's Zorua"
ZOROARK_EX = "N's Zoroark ex"
ZEKROM = "N's Zekrom"
RESHIRAM = "N's Reshiram"
DARUMAKA = "N's Darumaka"
DARMANITAN = "N's Darmanitan"
BUDEW = "Budew"
YVELTAL = "Yveltal"
MUNKIDORI = "Munkidori"
PECHARUNT_EX = "Pecharunt ex"
FEZANDIPITI_EX = "Fezandipiti ex"
BINDING_MOCHI = "Binding Mochi"
DARKNESS_ENERGY_ID = 7
BINDING_MOCHI_ID = 1162
NS_POKEMON = {ZORUA, ZOROARK_EX, ZEKROM, RESHIRAM, DARUMAKA, DARMANITAN}
COPY_SOURCE_NAMES = {ZEKROM, RESHIRAM, DARMANITAN, DARUMAKA}
SUPPORT_ONLY_NAMES = {BUDEW, FEZANDIPITI_EX}


@dataclass(frozen=True)
class TargetBoardReport:
    zorua_count: int = 0
    zoroark_ex_count: int = 0
    ready_zoroark_count: int = 0
    zoroark_energy_counts: List[int] = field(default_factory=list)
    has_backup_zorua_or_zoroark: bool = False
    has_n_zekrom: bool = False
    has_n_reshiram: bool = False
    has_darumaka: bool = False
    has_darmanitan: bool = False
    has_pecharunt_ex: bool = False
    has_binding_mochi_on_zoroark: bool = False
    has_fezandipiti_ex: bool = False
    has_budew: bool = False
    open_bench_slots: int = 0
    missing_core_pieces: List[str] = field(default_factory=list)
    next_best_setup_piece: str = ""
    board_stage: str = "EARLY"
    reason: str = ""


def evaluate_target_board(state: Any) -> TargetBoardReport:
    names = [pokemon_name(pokemon) for pokemon in our_pokemon(state)]
    zoroarks = [pokemon for pokemon in our_pokemon(state) if pokemon_name(pokemon) == ZOROARK_EX]
    zoroark_energy = [pokemon_energy_count(pokemon) for pokemon in zoroarks]
    ready_zoroarks = [count for count in zoroark_energy if count >= 2]
    has_backup = names.count(ZORUA) + names.count(ZOROARK_EX) >= 2
    missing: List[str] = []

    if ZORUA not in names and ZOROARK_EX not in names:
        missing.append(ZORUA)
    if len([name for name in names if name in {ZORUA, ZOROARK_EX}]) < 2:
        missing.append(f"backup {ZORUA}")
    if ZOROARK_EX not in names:
        missing.append(ZOROARK_EX)
    if not ready_zoroarks:
        missing.append("2 Darkness on Zoroark")
    if ZEKROM not in names and RESHIRAM not in names:
        missing.append(f"{ZEKROM} or {RESHIRAM}")

    stage = board_stage(state, bool(ready_zoroarks), ZEKROM in names or RESHIRAM in names)
    next_piece = next_best_piece(names, bool(ready_zoroarks))
    reason = (
        f"{stage}: Zorua={names.count(ZORUA)}, Zoroark ex={len(zoroarks)}, "
        f"ready Zoroark={len(ready_zoroarks)}, copy source={'yes' if has_copy_source(state) else 'no'}."
    )
    return TargetBoardReport(
        zorua_count=names.count(ZORUA),
        zoroark_ex_count=len(zoroarks),
        ready_zoroark_count=len(ready_zoroarks),
        zoroark_energy_counts=zoroark_energy,
        has_backup_zorua_or_zoroark=has_backup,
        has_n_zekrom=ZEKROM in names,
        has_n_reshiram=RESHIRAM in names,
        has_darumaka=DARUMAKA in names,
        has_darmanitan=DARMANITAN in names,
        has_pecharunt_ex=PECHARUNT_EX in names,
        has_binding_mochi_on_zoroark=any(has_tool(pokemon, BINDING_MOCHI_ID) for pokemon in zoroarks),
        has_fezandipiti_ex=FEZANDIPITI_EX in names,
        has_budew=BUDEW in names,
        open_bench_slots=bench_space(state),
        missing_core_pieces=missing,
        next_best_setup_piece=next_piece,
        board_stage=stage,
        reason=reason,
    )


def board_stage(state: Any, ready_zoroark: bool, has_zekrom: bool) -> str:
    if prize_count(state) <= 2 or prize_count(state, getattr(state, "opponent_index", 1)) <= 2:
        return "LATE"
    if ready_zoroark and has_zekrom:
        return "MID"
    return "EARLY"


def next_best_piece(names: List[str], ready_zoroark: bool) -> str:
    if ZORUA not in names and ZOROARK_EX not in names:
        return ZORUA
    if len([name for name in names if name in {ZORUA, ZOROARK_EX}]) < 2:
        return f"second {ZORUA}"
    if ZOROARK_EX not in names:
        return ZOROARK_EX
    if not ready_zoroark:
        return "Darkness Energy"
    if ZEKROM not in names:
        return ZEKROM
    if RESHIRAM not in names:
        return RESHIRAM
    if DARMANITAN not in names and DARUMAKA not in names:
        return DARUMAKA
    return "backup Zoroark line"


def our_pokemon(state: Any) -> List[Any]:
    return [pokemon for _area, _index, pokemon in iter_in_play(state)]


def our_benched_pokemon(state: Any) -> List[Any]:
    return list(bench_pokemon(state))


def pokemon_name(pokemon: Any) -> str:
    return canonical_name_from_id(card_id(pokemon))


def count_name(state: Any, name: str) -> int:
    return sum(1 for pokemon in our_pokemon(state) if pokemon_name(pokemon) == name)


def has_name(state: Any, name: str) -> bool:
    return count_name(state, name) > 0


def hand_has_name(state: Any, name: str) -> bool:
    return any(canonical_name_from_id(card_id(card)) == name for card in hand_cards(state))


def discard_has_name(state: Any, name: str) -> bool:
    return any(canonical_name_from_id(card_id(card)) == name for card in discard_cards(state))


def has_copy_source(state: Any) -> bool:
    return any(pokemon_name(pokemon) in COPY_SOURCE_NAMES for pokemon in our_benched_pokemon(state))


def ready_zoroarks(state: Any) -> List[Any]:
    return [pokemon for pokemon in our_pokemon(state) if pokemon_name(pokemon) == ZOROARK_EX and pokemon_energy_count(pokemon) >= 2]


def best_zoroark_energy_count(state: Any) -> int:
    counts = [pokemon_energy_count(pokemon) for pokemon in our_pokemon(state) if pokemon_name(pokemon) == ZOROARK_EX]
    return max(counts, default=0)


def darkness_in_discard(state: Any) -> int:
    return sum(1 for card in discard_cards(state) if card_id(card) == DARKNESS_ENERGY_ID)


def basic_energy_in_opponent_discard(state: Any) -> int:
    basic_ids = set(range(1, 9))
    return sum(1 for card in discard_cards(state, getattr(state, "opponent_index", 1)) if card_id(card) in basic_ids)


def has_tool(pokemon: Any, tool_id: int) -> bool:
    return tool_id in attached_card_ids(pokemon, "tools")


def active_is_poisoned(state: Any) -> bool:
    players = getv(state.current, "players", [])
    player = None
    if isinstance(players, list):
        idx = getattr(state, "your_index", 0)
        player = players[idx] if 0 <= idx < len(players) else None
    return bool(getv(player, "poisoned", False) or getv(active_pokemon(state), "poisoned", False))


def names_in_hand(state: Any) -> List[str]:
    return [canonical_name_from_id(card_id(card)) for card in hand_cards(state)]


def names_in_discard(state: Any) -> List[str]:
    return [canonical_name_from_id(card_id(card)) for card in discard_cards(state)]


def pokemon_with_name(state: Any, name: str) -> List[Any]:
    return [pokemon for pokemon in our_pokemon(state) if pokemon_name(pokemon) == name]


def opponent_active(state: Any) -> Any:
    return active_pokemon(state, getattr(state, "opponent_index", 1))


def opponent_bench(state: Any) -> List[Any]:
    return list(bench_pokemon(state, getattr(state, "opponent_index", 1)))


def count_in_cards_by_name(cards: Iterable[Any], name: str) -> int:
    return sum(1 for card in cards if canonical_name_from_id(card_id(card)) == name)
