from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

from state_eval import (
    OPT_ATTACH,
    OPT_PLAY,
    active_pokemon,
    attach_target_from_option,
    attached_card_ids,
    bench_pokemon,
    card_id,
    card_id_from_option,
    option_type,
    pokemon_energy_count,
)
from core.target_board import (
    DARKNESS_ENERGY_ID,
    FEZANDIPITI_EX,
    SUPPORT_ONLY_NAMES,
    ZOROARK_EX,
    ZORUA,
    evaluate_target_board,
    pokemon_name,
)
from core.priority_tables import canonical_name_from_id, context_source_name


@dataclass(frozen=True)
class EnergyScore:
    score: float = 0.0
    reason: str = ""
    target_name: str = ""
    energy_name: str = ""


def score_energy_option_zoroark(state: Any, option: Any) -> float:
    if option_type(option) == OPT_ATTACH:
        return score_energy_attachment_zoroark(state, card_id_from_option(state, option), attach_target_from_option(state, option)).score
    if option_type(option) == OPT_PLAY and canonical_name_from_id(card_id_from_option(state, option)) == "N's PP Up":
        return score_ns_pp_up_option(state, option)
    return 0.0


def score_energy_attachment_zoroark(state: Any, energy_card: Any, target: Any) -> EnergyScore:
    energy_cid = energy_card if isinstance(energy_card, int) else card_id(energy_card)
    energy_name = canonical_name_from_id(energy_cid)
    target_name = pokemon_name(target)
    if energy_cid != DARKNESS_ENERGY_ID:
        return EnergyScore(-7000.0, "Only Darkness Energy belongs in the N's Zoroark list.", target_name, energy_name)
    if target is None:
        return EnergyScore(0.0, "No visible target for Energy.", target_name, energy_name)

    before = darkness_energy_count(target)
    report = evaluate_target_board(state)
    if target_name == ZOROARK_EX:
        if before == 0:
            return EnergyScore(5500.0 + active_bonus(state, target), "Attach first Darkness to Zoroark line.", target_name, energy_name)
        if before == 1:
            return EnergyScore(7000.0 + active_bonus(state, target), "Attach second Darkness to Zoroark ex; this enables Night Joker.", target_name, energy_name)
        return EnergyScore(-6000.0, "Do not attach third Darkness to Zoroark; deck only has 7 Darkness.", target_name, energy_name)

    if target_name == ZORUA:
        if before >= 2:
            return EnergyScore(-5200.0, "Do not overattach to Zorua before evolution.", target_name, energy_name)
        if report.ready_zoroark_count == 0:
            return EnergyScore(5200.0 - before * 400.0, "Attach Darkness to Zorua that can become first Zoroark.", target_name, energy_name)
        return EnergyScore(5000.0 - before * 300.0, "Attach Darkness to backup Zorua line after first Zoroark is ready.", target_name, energy_name)

    if target_name in SUPPORT_ONLY_NAMES or target_name == FEZANDIPITI_EX:
        return EnergyScore(-7000.0, f"Do not attach Energy to support-only {target_name}.", target_name, energy_name)

    return EnergyScore(-7000.0, "Do not attach Energy outside the N's Zorua/Zoroark line; Bench Pokemon are copy sources only.", target_name, energy_name)


def score_attach_target_zoroark(state: Any, pokemon: Any) -> float:
    source = context_source_name(state)
    base = score_energy_attachment_zoroark(state, DARKNESS_ENERGY_ID, pokemon).score
    if source == "N's PP Up":
        if pokemon not in bench_pokemon(state):
            return -7000.0
        if pokemon_name(pokemon) not in {ZOROARK_EX, ZORUA}:
            return -6500.0
        return base + 900.0
    return base


def score_ns_pp_up_option(state: Any, option: Any) -> float:
    if canonical_name_from_id(card_id_from_option(state, option)) != "N's PP Up":
        return 0.0
    if darkness_in_discard(state) <= 0:
        return -7000.0
    best = best_pp_up_target_score(state)
    if best.score <= 0.0:
        return -7000.0
    if best.score >= 6000.0:
        return 6500.0
    return max(1800.0, best.score)


def best_pp_up_target_score(state: Any) -> EnergyScore:
    best = EnergyScore(-99999.0, "No Benched Zorua/Zoroark target benefits from N's PP Up.")
    for pokemon in bench_pokemon(state):
        if pokemon_name(pokemon) not in {ZOROARK_EX, ZORUA}:
            continue
        score = score_energy_attachment_zoroark(state, DARKNESS_ENERGY_ID, pokemon)
        if score.score > best.score:
            best = score
    return best


def darkness_energy_count(pokemon: Any) -> int:
    ids = attached_card_ids(pokemon, "energyCards") + attached_card_ids(pokemon, "energies")
    if ids:
        return sum(1 for cid in ids if cid == DARKNESS_ENERGY_ID)
    return pokemon_energy_count(pokemon)


def darkness_in_discard(state: Any) -> int:
    try:
        from state_eval import discard_cards

        return sum(1 for card in discard_cards(state) if card_id(card) == DARKNESS_ENERGY_ID)
    except Exception:
        return 0


def active_bonus(state: Any, target: Any) -> float:
    return 250.0 if target is active_pokemon(state) else 0.0


def ready_zoroark_available(state: Any) -> bool:
    for pokemon in [active_pokemon(state)] + list(bench_pokemon(state)):
        if pokemon_name(pokemon) == ZOROARK_EX and darkness_energy_count(pokemon) >= 2:
            return True
    return False
