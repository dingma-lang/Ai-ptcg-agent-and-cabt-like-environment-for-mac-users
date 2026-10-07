from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from card_db import get_db
from state_eval import (
    OPT_ABILITY,
    OPT_ATTACH,
    OPT_PLAY,
    OPT_RETREAT,
    active_pokemon,
    attach_target_from_option,
    bench_pokemon,
    bench_space,
    card_id,
    card_id_from_option,
    discard_cards,
    getv,
    hand_cards,
    iter_in_play,
    option_type,
    pokemon_energy_count,
    prize_count,
)
from deck_profile import load_deck_ids
from core.priority_tables import canonical_name_from_id, count_in_play, has_in_hand, has_in_play


FINIZEN = 105
PALAFIN = 106
PALAFIN_EX = 107
TATSUGIRI = 122
DRATINI = 902
DRAGONAIR = 903
MEGA_DRAGONITE_EX = 904
WATER_ENERGY = 3
LIGHTNING_ENERGY = 4
AIR_BALLOON = 1174
SWITCH_CARDS = {"Surfing Beach", "Switch", "Kieran"}
PALAFIN_NAMES = {"Finizen", "Palafin", "Palafin ex"}
DRAGONITE_NAMES = {"Dratini", "Dragonair", "Mega Dragonite ex"}


@dataclass(frozen=True)
class MovementResources:
    sky_transport: bool = False
    free_retreat: bool = False
    switch_card_effects: int = 0
    stadium_switch: bool = False
    air_balloon_attach_to_active: bool = False

    @property
    def conservative_count(self) -> int:
        return (
            int(self.sky_transport)
            + int(self.free_retreat)
            + self.switch_card_effects
            + int(self.stadium_switch)
            + int(self.air_balloon_attach_to_active)
        )


@dataclass(frozen=True)
class ZeroToHeroRoute:
    can_start: bool = False
    can_attack_this_turn: bool = False
    movement_count: int = 0
    movements_needed_to_transform: int = 0
    movements_needed_to_attack: int = 0
    palafin_ex_in_deck: bool = False
    partial_is_useful: bool = False
    reason: str = ""


def active_name(state: Any) -> str:
    return canonical_name_from_id(card_id(active_pokemon(state)))


def attached_energy_ids(pokemon: Any) -> list[int]:
    for field in ("energyCards", "energies", "attachedEnergyCards", "attachedEnergies", "attachedEnergy", "attachedCards"):
        cards = getv(pokemon, field, [])
        if not isinstance(cards, list) or not cards:
            continue
        ids: list[int] = []
        for item in cards:
            cid = card_id(item)
            if cid is None:
                continue
            card = get_db().get_card(cid)
            item_type = str(getv(item, "type", "") or getv(item, "cardType", "") or "")
            item_name = str(getv(item, "name", "") or "")
            if field != "attachedCards" or (card and "Energy" in card.card_type) or "Energy" in item_type or "Energy" in item_name:
                ids.append(cid)
        if ids:
            return ids
    return []


def attached_energy_count_any(pokemon: Any) -> int:
    ids = attached_energy_ids(pokemon)
    if ids:
        return len(ids)
    return pokemon_energy_count(pokemon)


def attached_energy_count(pokemon: Any, energy_id: int) -> int:
    return sum(1 for cid in attached_energy_ids(pokemon) if cid == energy_id)


def has_air_balloon(pokemon: Any) -> bool:
    for field in ("tools", "toolCards", "attachedTools", "attachedCards"):
        cards = getv(pokemon, field, [])
        if not isinstance(cards, list):
            continue
        if any(card_id(item) == AIR_BALLOON for item in cards):
            return True
    return False


def palafin_ex_deck_available(state: Any) -> bool:
    total = deck_count(PALAFIN_EX)
    if total <= 0:
        return True
    return seen_count(state, PALAFIN_EX) < total


def deck_count(cid: int) -> int:
    try:
        return sum(1 for deck_cid in load_deck_ids() if deck_cid == cid)
    except Exception:
        return 0


def seen_count(state: Any, cid: int) -> int:
    seen = sum(1 for card in hand_cards(state) if card_id(card) == cid)
    seen += sum(1 for card in discard_cards(state) if card_id(card) == cid)
    for _, _, pokemon in iter_in_play(state):
        if card_id(pokemon) == cid:
            seen += 1
        pre_evolution = getv(pokemon, "preEvolution", [])
        if isinstance(pre_evolution, list):
            seen += sum(1 for card in pre_evolution if card_id(card) == cid)
    return seen


def movement_resources(state: Any) -> MovementResources:
    active = active_pokemon(state)
    free_retreat = False
    if active is not None and active_name(state) != "Mega Dragonite ex":
        info = get_db().get_card(card_id(active))
        retreat_cost = int(getattr(info, "retreat_cost", 0) or 0) if info else 0
        free_retreat = retreat_cost <= 0 or has_air_balloon(active)

    sky_transport = False
    switch_card_effects = 0
    stadium_switch = False
    air_balloon_attach_to_active = False
    own_stadium = own_stadium_name(state)
    if own_stadium == "Surfing Beach":
        stadium_switch = True

    for option in getattr(state, "options", []) or []:
        typ = option_type(option)
        name = canonical_name_from_id(card_id_from_option(state, option))
        if typ == OPT_ABILITY and name == "Mega Dragonite ex":
            sky_transport = True
        elif typ == OPT_PLAY and name in SWITCH_CARDS:
            if name == "Surfing Beach":
                stadium_switch = True
            else:
                switch_card_effects += 1
        elif typ == OPT_ATTACH and name == "Air Balloon":
            target = attach_target_from_option(state, option)
            if target is not None and target_is_active(state, target):
                air_balloon_attach_to_active = True
        elif typ == OPT_RETREAT and active is not None and active_name(state) != "Mega Dragonite ex":
            if attached_energy_count_any(active) == 0 or has_air_balloon(active):
                free_retreat = True
    return MovementResources(
        sky_transport=sky_transport,
        free_retreat=free_retreat,
        switch_card_effects=switch_card_effects,
        stadium_switch=stadium_switch,
        air_balloon_attach_to_active=air_balloon_attach_to_active,
    )


def own_stadium_name(state: Any) -> str:
    stadium = getv(getv(state, "current"), "stadium", []) or getv(state.current, "stadium", [])
    if isinstance(stadium, list) and stadium:
        return canonical_name_from_id(card_id(stadium[0]))
    return ""


def target_is_active(state: Any, target: Any) -> bool:
    active = active_pokemon(state)
    if target is None or active is None:
        return False
    if target is active:
        return True
    for key in ("serial", "instanceId", "instance_id", "uid", "localId"):
        target_value = getv(target, key)
        active_value = getv(active, key)
        if target_value is not None and active_value is not None and target_value == active_value:
            return True
    return False


def zero_to_hero_route(state: Any) -> ZeroToHeroRoute:
    resources = movement_resources(state)
    movement_count = resources.conservative_count
    active = active_name(state)
    ex_in_deck = palafin_ex_deck_available(state)
    has_pivot = bool(bench_pokemon(state))
    partial_useful = False
    transform_needed = 0
    attack_needed = 0

    if active == "Palafin":
        transform_needed = 1
        attack_needed = 2
        partial_useful = has_pivot and ex_in_deck
    elif any(canonical_name_from_id(card_id(pokemon)) == "Palafin" for pokemon in bench_pokemon(state)):
        transform_needed = 2
        attack_needed = 3
        partial_useful = movement_count >= transform_needed and ex_in_deck
    else:
        return ZeroToHeroRoute(False, False, movement_count, 0, 0, ex_in_deck, False, "No normal Palafin is positioned for Zero to Hero.")

    can_start = ex_in_deck and has_pivot and movement_count >= transform_needed and (movement_count >= attack_needed or partial_useful)
    can_attack = can_start and movement_count >= attack_needed
    reason = (
        f"Zero to Hero movement plan: {movement_count} available, "
        f"{transform_needed} to transform, {attack_needed} to attack this turn."
    )
    if not ex_in_deck:
        reason = "Hold Zero to Hero route because no Palafin ex is likely left in deck."
    return ZeroToHeroRoute(can_start, can_attack, movement_count, transform_needed, attack_needed, ex_in_deck, partial_useful, reason)


def locked_palafin_reset_ready(state: Any) -> bool:
    if active_name(state) != "Palafin ex" or not palafin_ex_giga_locked(state):
        return False
    if benched_ready_palafin_ex(state):
        return movement_resources(state).conservative_count >= 1
    if tatsugiri_air_balloon_pivot_ready(state):
        resources = movement_resources(state)
        return resources.sky_transport or resources.switch_card_effects > 0 or resources.stadium_switch
    if benched_normal_palafin_ready(state):
        if not palafin_ex_deck_available(state):
            return False
        resources = movement_resources(state)
        if resources.conservative_count >= 2:
            return True
        return any(
            canonical_name_from_id(card_id(pokemon)) == "Palafin" and attached_energy_count_any(pokemon) > 0
            for pokemon in bench_pokemon(state)
        )
    return False


def palafin_ex_giga_locked(state: Any) -> bool:
    try:
        from core.palafin_attack_state import track_giga_impact_lock

        return bool(track_giga_impact_lock(state, None).restriction_applies_now)
    except Exception:
        return False


def benched_ready_palafin_ex(state: Any) -> bool:
    return any(
        canonical_name_from_id(card_id(pokemon)) == "Palafin ex" and attached_energy_count_any(pokemon) >= 1
        for pokemon in bench_pokemon(state)
    )


def benched_normal_palafin_ready(state: Any) -> bool:
    return any(
        canonical_name_from_id(card_id(pokemon)) == "Palafin" and (
            attached_energy_count(pokemon, WATER_ENERGY) >= 1
            or (not bool(getv(state.current, "energyAttached", False)) and has_in_hand(state, "Basic Water Energy"))
        )
        for pokemon in bench_pokemon(state)
    )


def tatsugiri_air_balloon_pivot_ready(state: Any) -> bool:
    return any(canonical_name_from_id(card_id(pokemon)) == "Tatsugiri" and has_air_balloon(pokemon) for pokemon in bench_pokemon(state))


def sky_transport_available(state: Any) -> bool:
    return movement_resources(state).sky_transport


def switch_item_should_yield_to_sky(state: Any, option_name: str) -> bool:
    if option_name not in {"Switch", "Kieran"}:
        return False
    if not sky_transport_available(state):
        return False
    active = active_name(state)
    if active == "Palafin":
        return zero_to_hero_route(state).can_start
    if active == "Palafin ex" and locked_palafin_reset_ready(state):
        return True
    return False


def retreat_should_yield_to_sky(state: Any) -> bool:
    if not sky_transport_available(state):
        return False
    active = active_name(state)
    return active in {"Palafin", "Palafin ex"} and (zero_to_hero_route(state).can_start or locked_palafin_reset_ready(state))


def controlled_basic_bench_score(state: Any, name: str) -> float:
    if bench_space(state) <= 0:
        return -9000.0
    space = bench_space(state)
    palafin_count = count_in_play(state, "Finizen") + count_in_play(state, "Palafin") + count_in_play(state, "Palafin ex")
    dragonite_count = count_in_play(state, "Dratini") + count_in_play(state, "Dragonair") + count_in_play(state, "Mega Dragonite ex")

    if name == "Finizen":
        if palafin_count == 0:
            return 7600.0
        if palafin_count == 1:
            return 6600.0
        if has_in_hand(state, "Palafin") and count_in_play(state, "Finizen") > 0:
            return 4200.0
        if space <= 1 and needs_open_switch_space(state):
            return -900.0
        return 900.0
    if name == "Dratini":
        if dragonite_count == 0:
            return 5200.0 if palafin_count >= 1 else 3000.0
        if has_in_hand(state, "Dragonair") and count_in_play(state, "Dratini") > 0:
            return 3600.0
        if space <= 1 and needs_open_switch_space(state):
            return -1200.0
        return 350.0
    if name == "Tatsugiri":
        if has_in_play(state, "Tatsugiri"):
            return -800.0
        if active_name(state) == "Tatsugiri":
            return -1200.0
        if supporter_access_needed(state):
            return 4200.0
        if dragonite_count > 0 and space >= 2:
            return 3000.0
        if space <= 1:
            return -700.0
        return 1100.0
    return -300.0


def poffin_need_score(state: Any) -> float:
    if bench_space(state) <= 0:
        return -7000.0
    if not poffin_targets_likely_remaining(state):
        return -1200.0
    palafin_count = count_in_play(state, "Finizen") + count_in_play(state, "Palafin") + count_in_play(state, "Palafin ex")
    has_tatsugiri = has_in_play(state, "Tatsugiri")
    space = bench_space(state)
    if palafin_count == 0:
        return 8200.0
    if palafin_count == 1:
        return 7600.0
    if len(bench_pokemon(state)) <= 1 and not has_tatsugiri:
        return 6200.0
    if not has_tatsugiri and supporter_access_needed(state) and space >= 2:
        return 5200.0
    if palafin_count < 3 and space >= 2 and not needs_open_switch_space(state):
        return 2600.0
    return -4200.0 if len(bench_pokemon(state)) >= 3 else 900.0


def poffin_target_score(state: Any, cid: Optional[int], name: str) -> float:
    card = get_db().get_card(cid)
    if not card or card.card_type != "Pokemon" or not card.basic or card.hp > 70:
        return -10000.0
    if name == "Finizen":
        return controlled_basic_bench_score(state, name) + 1600.0
    if name == "Tatsugiri":
        return controlled_basic_bench_score(state, name) + 1300.0
    return -500.0


def poffin_targets_likely_remaining(state: Any) -> bool:
    for cid in (FINIZEN, TATSUGIRI):
        total = deck_count(cid)
        if total > 0 and seen_count(state, cid) < total:
            return True
    return False


def needs_open_switch_space(state: Any) -> bool:
    if active_name(state) == "Palafin" and palafin_ex_deck_available(state):
        return True
    if active_name(state) == "Palafin ex" and palafin_ex_giga_locked(state):
        return True
    return count_in_play(state, "Palafin") > 0 and count_in_play(state, "Palafin ex") == 0


def supporter_access_needed(state: Any) -> bool:
    if bool(getv(state.current, "supporterPlayed", False)):
        return False
    for option in getattr(state, "options", []) or []:
        if option_type(option) != OPT_PLAY:
            continue
        card = get_db().get_card(card_id_from_option(state, option))
        if card and card.card_type == "Supporter":
            return False
    return True


def palaking_energy_breakpoint_score(state: Any, energy_cid: Optional[int], target: Any) -> float:
    if energy_cid is None or target is None:
        return 0.0
    name = canonical_name_from_id(card_id(target))
    current = attached_energy_count_any(target)
    water = attached_energy_count(target, WATER_ENERGY)
    lightning = attached_energy_count(target, LIGHTNING_ENERGY)
    energy_used = bool(getv(state.current, "energyAttached", False))
    if name in PALAFIN_NAMES and energy_cid != WATER_ENERGY:
        return -100000.0
    if name == "Palafin ex":
        if current >= 1:
            return -100000.0
        return 7600.0 if energy_cid == WATER_ENERGY else -100000.0
    if name == "Palafin":
        if energy_cid != WATER_ENERGY:
            return -100000.0
        if current == 0:
            route = zero_to_hero_route(state)
            return 6200.0 if route.can_start or active_name(state) == "Palafin" else 4200.0
        return -2500.0
    if name == "Finizen":
        if energy_cid != WATER_ENERGY:
            return -100000.0
        if current == 0 and (has_in_hand(state, "Palafin") or count_in_play(state, "Palafin") > 0):
            return 4400.0
        return 1200.0 if current == 0 and not energy_used else -1800.0
    if name in {"Dratini", "Dragonair", "Mega Dragonite ex"}:
        if current >= 3:
            return -7000.0
        if name == "Dragonair" and current == 0:
            return 7200.0
        if name == "Dratini" and current == 0 and has_in_hand(state, "Dragonair"):
            return 5600.0
        if energy_cid == LIGHTNING_ENERGY:
            if lightning >= 2:
                return -2600.0
            return 6000.0 if dragonite_attack_plan_exists(state) else 3600.0
        if energy_cid == WATER_ENERGY:
            if palafin_attackers_are_satisfied(state):
                return 5400.0 if name in {"Dragonair", "Mega Dragonite ex"} else 4200.0
            if name == "Dragonair" and current == 0:
                return 6400.0
            return -900.0
    if name == "Tatsugiri":
        return -100000.0
    return -2500.0


def palafin_attackers_are_satisfied(state: Any) -> bool:
    found = False
    for _, _, pokemon in iter_in_play(state):
        if canonical_name_from_id(card_id(pokemon)) != "Palafin ex":
            continue
        found = True
        if attached_energy_count(pokemon, WATER_ENERGY) != 1 or attached_energy_count_any(pokemon) != 1:
            return False
    return found


def dragonite_attack_plan_exists(state: Any) -> bool:
    return any(canonical_name_from_id(card_id(pokemon)) in DRAGONITE_NAMES for _, _, pokemon in iter_in_play(state)) or has_in_hand(state, "Mega Dragonite ex")


def dragonair_guidance_is_productive_now(state: Any) -> bool:
    if not dragonair_has_energy(state):
        return False
    if count_in_play(state, "Dragonair") > 0 and not has_in_hand(state, "Mega Dragonite ex") and count_in_play(state, "Mega Dragonite ex") == 0:
        return True
    if count_in_play(state, "Finizen") > 0 and not has_in_hand(state, "Palafin") and count_in_play(state, "Palafin") == 0:
        return True
    if count_in_play(state, "Dratini") > 0 and count_in_play(state, "Dragonair") == 0:
        return True
    return False


def dragonair_guidance_should_wait_for_refresh(state: Any) -> bool:
    if not dragonair_has_energy(state) or dragonair_search_can_be_played_immediately(state):
        return False
    if has_in_hand(state, "Lillie's Determination") or has_in_hand(state, "Cyrano"):
        return True
    return False


def dragonair_search_can_be_played_immediately(state: Any) -> bool:
    if count_in_play(state, "Dragonair") > 0 and not has_in_hand(state, "Mega Dragonite ex") and count_in_play(state, "Mega Dragonite ex") == 0:
        return True
    if count_in_play(state, "Finizen") > 0 and not has_in_hand(state, "Palafin") and count_in_play(state, "Palafin") == 0:
        return True
    return False


def dragonair_has_energy(state: Any) -> bool:
    return any(
        canonical_name_from_id(card_id(pokemon)) == "Dragonair" and attached_energy_count_any(pokemon) > 0
        for _, _, pokemon in iter_in_play(state)
    )


def mega_dragonite_prize_liability_too_high(state: Any) -> bool:
    try:
        return prize_count(state, state.opponent_index) <= 3
    except Exception:
        return False
