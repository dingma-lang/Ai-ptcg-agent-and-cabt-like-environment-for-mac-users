from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from card_db import get_db
from state_eval import OPT_ABILITY, OPT_ATTACK, OPT_CARD, OPT_EVOLVE, OPT_PLAY, active_pokemon, attach_target_from_option, card_id, card_id_from_option, get_pokemon_by_area, getv, iter_in_play, option_type, pokemon_energy_count, pokemon_hp, pokemon_max_hp
from core.energy_planner import hydreigon_darkness_acceleration_score
from core.priority_tables import CARD_IDS, canonical_name_from_id, context_source_name, has_in_play


@dataclass(frozen=True)
class ToxtricityPlan:
    score: float
    reason: str
    target_name: str = ""


def score_toxtricity_engine(state: Any, legal_options: Any = None) -> ToxtricityPlan:
    try:
        from core.prize_availability_tracker import infer_card_availability

        if infer_card_availability(state, None).toxel_availability_low:
            return ToxtricityPlan(-1800.0, "Toxel availability low; deprioritize Toxtricity engine.")
    except Exception:
        pass
    target = best_toxtricity_target(state)
    if target is None:
        return ToxtricityPlan(0.0, "No useful Darkness Energy acceleration target.")
    return ToxtricityPlan(1800.0, "Toxtricity is Energy engine, not damage dealer.", canonical_name_from_id(card_id(target)))


def score_toxtricity_option(state: Any, option: Any, base_score: float = 0.0) -> float:
    cid = card_id_from_option(state, option)
    name = canonical_name_from_id(cid)
    typ = option_type(option)
    bonus = 0.0
    try:
        from core.prize_availability_tracker import infer_card_availability

        if infer_card_availability(state, None).toxel_availability_low and name in {"Toxel", "Toxtricity"}:
            bonus -= 2500.0
    except Exception:
        pass

    if typ == OPT_PLAY and name == "Toxel":
        if not (has_in_play(state, "Toxel") or has_in_play(state, "Toxtricity")):
            bonus += 900.0

    if typ == OPT_EVOLVE and name == "Toxtricity":
        target = attach_target_from_option(state, option)
        if target is None:
            target = get_pokemon_by_area(state, getv(option, "inPlayArea"), getv(option, "inPlayIndex"), state.your_index)
        if canonical_name_from_id(card_id(target)) == "Toxel" and best_toxtricity_target(state) is not None:
            bonus += 1800.0

    if typ == OPT_ABILITY and name == "Toxtricity":
        target = best_toxtricity_target(state)
        if target is not None and not toxtricity_target_would_be_bad(target):
            target_name = canonical_name_from_id(card_id(target))
            if target_name == "Mega Gengar ex":
                bonus += 2200.0
            elif target_name == "Hydreigon ex":
                bonus += 2600.0 if hydreigon_darkness_acceleration_score(target) else 1800.0
            elif target_name in {"Haunter", "Gastly"}:
                bonus += 1200.0
            elif target_name in {"Zweilous", "Deino"}:
                bonus += 1000.0
        else:
            bonus -= 4200.0

    if typ == OPT_ATTACK and canonical_name_from_id(card_id(active_pokemon(state))) == "Toxtricity":
        bonus -= 12000.0

    source = context_source_name(state)
    if typ == OPT_CARD and source in {"Buddy-Buddy Poffin", "Poke Pad"}:
        if name == "Toxel" and not (has_in_play(state, "Toxel") or has_in_play(state, "Toxtricity")):
            bonus += 800.0
        if source == "Poke Pad" and name == "Toxtricity" and has_in_play(state, "Toxel"):
            bonus += 1600.0
    return bonus


def best_toxtricity_target(state: Any) -> Any:
    best = None
    best_score = -9999
    for _, _, pokemon in iter_in_play(state):
        name = canonical_name_from_id(card_id(pokemon))
        score = target_priority(pokemon)
        if score > best_score:
            best_score = score
            best = pokemon
    return best if best_score > 0 else None


def target_priority(pokemon: Any) -> float:
    name = canonical_name_from_id(card_id(pokemon))
    energy = pokemon_energy_count(pokemon)
    if name in {"Toxel", "Toxtricity", "Pecharunt ex", "Fezandipiti ex"}:
        return -2000.0
    if name == "Mega Gengar ex":
        return 5000.0 if energy < 2 else 500.0
    if name in {"Haunter", "Gastly"}:
        return 3000.0
    if name == "Hydreigon ex":
        dark_need = hydreigon_darkness_acceleration_score(pokemon)
        if dark_need:
            return dark_need
        return 600.0 if energy < 4 else 0.0
    if name in {"Zweilous", "Deino"}:
        return 1800.0
    card = get_db().get_card(card_id(pokemon))
    if card and any("D" in "".join(attack.cost or []) for attack in card.attacks):
        return 600.0
    return 0.0


def toxtricity_target_would_be_bad(pokemon: Any) -> bool:
    hp = pokemon_hp(pokemon)
    max_hp = pokemon_max_hp(pokemon)
    return bool(max_hp and hp <= 20)
