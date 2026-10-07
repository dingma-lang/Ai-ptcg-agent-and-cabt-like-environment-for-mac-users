from __future__ import annotations

from typing import Any, Optional

from state_eval import OPT_EVOLVE, active_pokemon, attach_target_from_option, attached_card_ids, card_id, card_id_from_option, get_pokemon_by_area, getv, option_type, pokemon_energy_count, pokemon_hp, pokemon_max_hp
from core.priority_tables import canonical_name_from_id, has_in_hand, has_in_play


def score_evolution_option(state: Any, option: Any) -> float:
    evolve_cid = card_id_from_option(state, option)
    evolve_name = canonical_name_from_id(evolve_cid)
    target = attach_target_from_option(state, option)
    if target is None:
        target = get_pokemon_by_area(state, getv(option, "inPlayArea"), getv(option, "inPlayIndex"), state.your_index)
    target_name = canonical_name_from_id(card_id(target))
    score = score_evolution_names(state, evolve_name, target_name)
    if score and target is not None:
        if pokemon_energy_count(target) > 0:
            score += 150.0
        if evolve_name == "Hydreigon ex":
            score += hydreigon_attack_readiness_bonus(state, target, target_name)
        score += same_name_energy_target_bonus(state, option, evolve_cid, target)
        if pokemon_hp(target) <= max(40, pokemon_max_hp(target) * 0.35):
            score += 200.0
    return score


def hydreigon_attack_readiness_bonus(state: Any, target: Any, target_name: str) -> float:
    if target_name not in {"Deino", "Zweilous", "Hydreigon ex"}:
        return 0.0
    energy_count = pokemon_energy_count(target)
    attached = set(attached_card_ids(target, "energyCards") + attached_card_ids(target, "energies"))
    score = energy_count * 520.0
    if target_name == "Zweilous":
        score += 700.0
    if 7 in attached and energy_count >= 2:
        score += 650.0
    if {7, 8, 5}.issubset(attached) and energy_count >= 3:
        score += 900.0
    if target is active_pokemon(state) and energy_count >= 2:
        score += 300.0
    return score


def same_name_energy_target_bonus(state: Any, option: Any, evolve_cid: Optional[int], target: Any) -> float:
    """Prefer evolving the same-name Pokemon that already carries more Energy."""
    target_name = canonical_name_from_id(card_id(target))
    evolve_name = canonical_name_from_id(evolve_cid)
    if not target_name or not evolve_name:
        return 0.0

    candidate_energy: list[int] = []
    for candidate in getattr(state, "options", []) or []:
        if option_type(candidate) != OPT_EVOLVE:
            continue
        if canonical_name_from_id(card_id_from_option(state, candidate)) != evolve_name:
            continue
        candidate_target = attach_target_from_option(state, candidate)
        if candidate_target is None:
            candidate_target = get_pokemon_by_area(state, getv(candidate, "inPlayArea"), getv(candidate, "inPlayIndex"), state.your_index)
        if canonical_name_from_id(card_id(candidate_target)) == target_name:
            candidate_energy.append(pokemon_energy_count(candidate_target))

    if len(candidate_energy) < 2 or max(candidate_energy) == min(candidate_energy):
        return 0.0
    return pokemon_energy_count(target) * 450.0


def score_rare_candy_play(state: Any, option: Any) -> float:
    del option
    if has_in_play(state, "Deino") and has_in_hand(state, "Hydreigon ex"):
        return 1200.0
    if has_in_play(state, "Deino"):
        return 450.0
    return -250.0


def score_evolution_names(state: Any, evolve_name: str, target_name: str) -> float:
    if evolve_name == "Hydreigon ex" and target_name == "Deino":
        return 1200.0
    if evolve_name == "Hydreigon ex" and target_name == "Zweilous":
        return 1300.0
    if evolve_name == "Hydreigon ex":
        return 1000.0
    if evolve_name == "Zweilous" and target_name == "Deino":
        if has_in_hand(state, "Rare Candy") and has_in_hand(state, "Hydreigon ex"):
            return 150.0
        return 350.0
    if evolve_name == "Haunter" and target_name == "Gastly":
        if has_in_hand(state, "Mega Gengar ex"):
            return 3000.0
        return 900.0
    if evolve_name == "Toxtricity" and target_name == "Toxel":
        return 250.0
    return 0.0


def rare_candy_line_ready(state: Any) -> bool:
    return has_in_play(state, "Deino") and has_in_hand(state, "Rare Candy") and has_in_hand(state, "Hydreigon ex")


def hydreigon_evolution_available(state: Any) -> bool:
    return has_in_hand(state, "Hydreigon ex") and (has_in_play(state, "Zweilous") or rare_candy_line_ready(state))
