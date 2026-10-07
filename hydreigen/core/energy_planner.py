from __future__ import annotations

from typing import Any, Optional

from state_eval import attach_target_from_option, attached_card_ids, card_id, card_id_from_option, iter_in_play, pokemon_energy_count
from core.opponent_model import infer_opponent_next_turn_threat
from core.priority_tables import HYDREIGON_LINE_IDS, canonical_name_from_id, has_in_hand

ENERGY_TYPE_BY_ID = {
    7: "darkness",
    5: "psychic",
    8: "metal",
}

HYDREIGON_STAGE_RANK = {
    227: 1,
    228: 2,
    229: 3,
}

GENGAR_STAGE_RANK = {
    59: 1,
    771: 2,
    772: 3,
}

SUPPORT_ENERGY_DENY_NAMES = {"Fezandipiti ex", "Pecharunt ex", "Toxel", "Toxtricity"}


def score_energy_option(state: Any, option: Any) -> float:
    energy_cid = card_id_from_option(state, option)
    target = attach_target_from_option(state, option)
    return score_energy_attachment(state, energy_cid, target)


def score_energy_attachment(state: Any, energy_card: Any, target_pokemon: Any) -> float:
    energy_cid = energy_card if isinstance(energy_card, int) else card_id(energy_card)
    target_cid = card_id(target_pokemon)
    energy_name = canonical_name_from_id(energy_cid)
    target_name = canonical_name_from_id(target_cid)
    if energy_cid is None or target_cid is None:
        return 0.0

    if target_name in SUPPORT_ENERGY_DENY_NAMES:
        return -5200.0

    if target_cid in HYDREIGON_LINE_IDS:
        return score_hydreigon_line_energy(state, energy_cid, target_pokemon)

    if energy_name == "Basic Metal Energy":
        return -5200.0

    if energy_name == "Basic Psychic Energy":
        return -5200.0

    if energy_name == "Basic Darkness Energy":
        if target_cid in GENGAR_STAGE_RANK:
            return score_gengar_line_energy(state, target_pokemon)
        return -300.0

    return 0.0


def score_gengar_line_energy(state: Any, target_pokemon: Any) -> float:
    target_cid = card_id(target_pokemon)
    target_rank = GENGAR_STAGE_RANK.get(target_cid, 0)
    if not target_rank:
        return 0.0
    energy_count = pokemon_energy_count(target_pokemon)
    if energy_count >= 2:
        return -5200.0
    max_rank = highest_gengar_stage_rank(state)
    if max_rank and target_rank < max_rank:
        return -1400.0

    target_name = canonical_name_from_id(target_cid)
    score = 520.0 + target_rank * 330.0
    if energy_count == 1:
        score += 1500.0
    if target_name == "Mega Gengar ex":
        score += 1150.0
    elif target_name == "Haunter" and has_in_hand(state, "Mega Gengar ex"):
        score += 950.0
    elif target_name == "Gastly" and (has_in_hand(state, "Haunter") or has_in_hand(state, "Mega Gengar ex")):
        score += 650.0
    try:
        threat = infer_opponent_next_turn_threat(state)
        if threat.has_rulebox_attacker or threat.likely_ex_heavy:
            score += 1050.0
    except Exception:
        pass
    return score


def highest_gengar_stage_rank(state: Any) -> int:
    best = 0
    for _, _, pokemon in iter_in_play(state):
        best = max(best, GENGAR_STAGE_RANK.get(card_id(pokemon), 0))
    return best


def score_hydreigon_line_energy(state: Any, energy_cid: int, target_pokemon: Any) -> float:
    target_cid = card_id(target_pokemon)
    if target_cid not in HYDREIGON_STAGE_RANK:
        return 0.0
    max_rank = highest_hydreigon_stage_rank(state)
    target_rank = HYDREIGON_STAGE_RANK[target_cid]
    if max_rank and target_rank < max_rank:
        return -1400.0

    energy_type = ENERGY_TYPE_BY_ID.get(energy_cid)
    if energy_type is None:
        return -300.0

    counts = hydreigon_energy_counts(target_pokemon)
    total = sum(counts.values())
    if counts[energy_type] >= 2:
        return -5200.0
    has_required = all(counts[name] >= 1 for name in ("darkness", "psychic", "metal"))
    if has_required and total >= 4:
        return -4800.0

    stage_bonus = target_rank * 220.0
    if counts[energy_type] == 0:
        required_bonus = {"metal": 1120.0, "psychic": 1100.0, "darkness": 1060.0}[energy_type]
        return required_bonus + stage_bonus
    if has_required and total < 4:
        if energy_type == "darkness":
            return 980.0 + stage_bonus
        return 180.0 + stage_bonus * 0.25
    return 360.0 + stage_bonus * 0.5


def highest_hydreigon_stage_rank(state: Any) -> int:
    best = 0
    for _, _, pokemon in iter_in_play(state):
        best = max(best, HYDREIGON_STAGE_RANK.get(card_id(pokemon), 0))
    return best


def hydreigon_energy_counts(pokemon: Any) -> dict[str, int]:
    counts = {"darkness": 0, "psychic": 0, "metal": 0}
    for cid in attached_card_ids(pokemon, "energyCards") + attached_card_ids(pokemon, "energies"):
        energy_type = ENERGY_TYPE_BY_ID.get(cid)
        if energy_type:
            counts[energy_type] += 1
    return counts


def hydreigon_darkness_acceleration_score(pokemon: Any) -> float:
    """Value of attaching a Darkness Energy by effect to Hydreigon ex."""
    if canonical_name_from_id(card_id(pokemon)) != "Hydreigon ex":
        return 0.0
    counts = hydreigon_energy_counts(pokemon)
    total = sum(counts.values())
    if total >= 4 or counts["darkness"] >= 2:
        return 0.0
    missing_required = [name for name in ("darkness", "psychic", "metal") if counts[name] == 0]
    if counts["darkness"] == 0:
        if total >= 2:
            return 7200.0
        return 5200.0
    if not missing_required and total == 3:
        return 6800.0
    if total < 4:
        return 2600.0
    return 0.0


def has_attached_energy(pokemon: Any, energy_cid: int) -> bool:
    return energy_cid in attached_card_ids(pokemon, "energyCards") or energy_cid in attached_card_ids(pokemon, "energies")


def pokemon_uses_energy_type(pokemon: Any, energy_symbol: str) -> bool:
    from card_db import get_db

    info = get_db().get_card(card_id(pokemon))
    if not info:
        return False
    wanted = energy_symbol.upper()
    for attack in info.attacks:
        cost = "".join(str(part).upper() for part in (attack.cost or []))
        if wanted in cost:
            return True
    return False


def crispin_energy_selection_score(state: Any, energy_cid: Optional[int]) -> float:
    energy_name = canonical_name_from_id(energy_cid)
    score = 0.0
    hydreigon_need = crispin_hydreigon_energy_selection_need(state, energy_cid)
    gengar_need = crispin_gengar_energy_selection_need(state, energy_cid)
    score = max(score, hydreigon_need, gengar_need)
    if energy_name == "Basic Metal Energy":
        return max(score, 900.0)
    if energy_name == "Basic Psychic Energy":
        return max(score, 875.0)
    if energy_name == "Basic Darkness Energy":
        return max(score, 700.0)
    return 0.0


def crispin_hydreigon_energy_selection_need(state: Any, energy_cid: Optional[int]) -> float:
    energy_type = ENERGY_TYPE_BY_ID.get(energy_cid)
    if not energy_type:
        return 0.0
    best = 0.0
    for _, _, pokemon in iter_in_play(state):
        cid = card_id(pokemon)
        if cid not in HYDREIGON_STAGE_RANK:
            continue
        counts = hydreigon_energy_counts(pokemon)
        total = sum(counts.values())
        if total >= 4 or counts[energy_type] >= 2:
            continue
        if counts[energy_type] == 0:
            best = max(best, {"metal": 1220.0, "psychic": 1200.0, "darkness": 950.0}[energy_type])
        elif energy_type == "darkness" and all(counts[name] >= 1 for name in ("darkness", "psychic", "metal")):
            best = max(best, 1020.0)
    return best


def crispin_gengar_energy_selection_need(state: Any, energy_cid: Optional[int]) -> float:
    if energy_cid != 7:
        return 0.0
    best = 0.0
    try:
        threat = infer_opponent_next_turn_threat(state)
        ex_pressure = bool(threat.has_rulebox_attacker or threat.likely_ex_heavy)
    except Exception:
        ex_pressure = False
    for _, _, pokemon in iter_in_play(state):
        name = canonical_name_from_id(card_id(pokemon))
        if name not in {"Mega Gengar ex", "Haunter", "Gastly"}:
            continue
        energy_count = pokemon_energy_count(pokemon)
        if energy_count >= 2:
            continue
        score = 1120.0
        if name == "Mega Gengar ex":
            score += 500.0 if energy_count == 1 else 150.0
        elif name == "Haunter" and has_in_hand(state, "Mega Gengar ex"):
            score += 300.0
        if ex_pressure:
            score += 350.0
        best = max(best, score)
    return best
