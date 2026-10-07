from __future__ import annotations

from typing import Any

from state_eval import OPT_CARD, OPT_PLAY, card_id, card_id_from_option, discard_cards, option_type
from core.priority_tables import CARD_IDS, canonical_name_from_id


ENERGY_IDS = {CARD_IDS["Basic Darkness Energy"], CARD_IDS["Basic Metal Energy"], CARD_IDS["Basic Psychic Energy"]}
KEY_POKEMON_IDS = {
    CARD_IDS["Deino"],
    CARD_IDS["Zweilous"],
    CARD_IDS["Hydreigon ex"],
    CARD_IDS["Gastly"],
    CARD_IDS["Haunter"],
    CARD_IDS["Mega Gengar ex"],
    CARD_IDS["Toxel"],
    CARD_IDS["Toxtricity"],
}


def score_recovery_timing_option(state: Any, option: Any) -> float:
    if option_type(option) == OPT_CARD:
        return 0.0
    if option_type(option) != OPT_PLAY:
        return 0.0
    name = canonical_name_from_id(card_id_from_option(state, option))
    if name == "Energy Recycler":
        return score_energy_recycler(state)
    if name == "Sacred Ash":
        return score_sacred_ash(state)
    if name == "Night Stretcher":
        return score_night_stretcher(state)
    return 0.0


def score_energy_recycler(state: Any) -> float:
    count = energy_discard_count(state)
    if count >= 5:
        return 5000.0
    if count >= 4:
        return 4000.0
    if exact_energy_needed_from_discard(state):
        return 3200.0
    return -2500.0


def score_sacred_ash(state: Any) -> float:
    count = pokemon_discard_count(state)
    if key_line_lost(state):
        return 4500.0
    if count >= 4:
        return 4000.0
    if count <= 2:
        return -3000.0
    return 800.0


def score_night_stretcher(state: Any) -> float:
    return 4500.0 if exact_resource_needed_from_discard(state) else -1500.0


def energy_discard_count(state: Any) -> int:
    return sum(1 for card in discard_cards(state) if card_id(card) in ENERGY_IDS)


def pokemon_discard_count(state: Any) -> int:
    return sum(1 for card in discard_cards(state) if is_pokemon_id(card_id(card)))


def is_pokemon_id(cid: Any) -> bool:
    return cid in KEY_POKEMON_IDS or cid in {CARD_IDS["Fezandipiti ex"], CARD_IDS["Pecharunt ex"]}


def key_line_lost(state: Any) -> bool:
    discard_ids = [card_id(card) for card in discard_cards(state)]
    deino_lost = discard_ids.count(CARD_IDS["Deino"]) >= 3
    gengar_lost = any(cid in discard_ids for cid in (CARD_IDS["Gastly"], CARD_IDS["Haunter"], CARD_IDS["Mega Gengar ex"]))
    tox_lost = any(cid in discard_ids for cid in (CARD_IDS["Toxel"], CARD_IDS["Toxtricity"]))
    attacker_lost = any(cid in discard_ids for cid in (CARD_IDS["Hydreigon ex"], CARD_IDS["Mega Gengar ex"]))
    return deino_lost or (attacker_lost and (gengar_lost or tox_lost))


def exact_energy_needed_from_discard(state: Any) -> bool:
    try:
        from state_eval import deck_count

        return deck_count(state) <= 3 and bool({card_id(card) for card in discard_cards(state)} & ENERGY_IDS)
    except Exception:
        return False


def exact_resource_needed_from_discard(state: Any) -> bool:
    discard_ids = {card_id(card) for card in discard_cards(state)}
    return bool(discard_ids & (ENERGY_IDS | KEY_POKEMON_IDS))


def recovery_threshold_debug(state: Any) -> dict[str, Any]:
    return {
        "energy_discard_count": energy_discard_count(state),
        "pokemon_discard_count": pokemon_discard_count(state),
        "key_line_lost": key_line_lost(state),
    }
