from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from state_eval import OPT_CARD, OPT_PLAY, attached_card_ids, card_id, card_id_from_option, iter_in_play, option_type, pokemon_energy_count
from core.energy_planner import ENERGY_TYPE_BY_ID, hydreigon_energy_counts
from core.priority_tables import canonical_name_from_id, has_in_play


@dataclass(frozen=True)
class CrispinPlan:
    should_use: bool
    score: float = 0.0
    reason: str = ""


def hydreigon_crispin_plan(state: Any) -> CrispinPlan:
    best = 0.0
    reason = "No Hydreigon Energy need."
    for _, _, pokemon in iter_in_play(state):
        name = canonical_name_from_id(card_id(pokemon))
        if name not in {"Hydreigon ex", "Deino", "Zweilous"}:
            continue
        score, local_reason = hydreigon_energy_gap_score(pokemon)
        if score > best:
            best = score
            reason = local_reason
    if best <= 0.0:
        return CrispinPlan(False, 0.0, reason)
    return CrispinPlan(True, best, reason)


def score_crispin_option(state: Any, option: Any) -> float:
    if option_type(option) != OPT_PLAY or canonical_name_from_id(card_id_from_option(state, option)) != "Crispin":
        return 0.0
    plan = hydreigon_crispin_plan(state)
    if plan.should_use:
        return plan.score
    if has_in_play(state, "Hydreigon ex"):
        return -3000.0
    return 0.0


def score_crispin_energy_selection(state: Any, cid: Optional[int]) -> float:
    energy_type = ENERGY_TYPE_BY_ID.get(cid)
    if not energy_type:
        return 0.0
    best = 0.0
    for _, _, pokemon in iter_in_play(state):
        name = canonical_name_from_id(card_id(pokemon))
        if name not in {"Hydreigon ex", "Deino", "Zweilous"}:
            continue
        counts = hydreigon_energy_counts(pokemon)
        total = sum(counts.values())
        if total >= 4 or counts[energy_type] >= 2:
            continue
        if counts[energy_type] == 0:
            best = max(best, {"metal": 6500.0, "psychic": 6400.0, "darkness": 5600.0}[energy_type])
        elif energy_type == "darkness" and total == 3 and all(counts[k] >= 1 for k in ("darkness", "psychic", "metal")):
            best = max(best, 6100.0)
    return best


def hydreigon_energy_gap_score(pokemon: Any) -> tuple[float, str]:
    name = canonical_name_from_id(card_id(pokemon))
    counts = hydreigon_energy_counts(pokemon)
    total = sum(counts.values())
    missing = [energy for energy in ("darkness", "psychic", "metal") if counts[energy] == 0]
    if name == "Hydreigon ex":
        if total >= 4:
            return 0.0, "Hydreigon already has enough Energy."
        if not missing and total == 3:
            return 6000.0, "Use Crispin because Hydreigon ex has exact types and needs fourth Energy."
        if "metal" in missing or "psychic" in missing:
            return 5200.0, "Use Crispin because Hydreigon ex lacks required Metal/Psychic Energy."
        if "darkness" in missing:
            return 4500.0, "Use Crispin because Hydreigon ex lacks Darkness Energy."
        return 3500.0, "Use Crispin because Hydreigon ex needs Energy."
    if name in {"Deino", "Zweilous"} and total < 3:
        return 3500.0, "Use Crispin because Hydreigon line needs Energy for the next attacker."
    return 0.0, "No Hydreigon Energy need."


def hydreigon_has_enough_energy(pokemon: Any) -> bool:
    ids = set(attached_card_ids(pokemon, "energyCards") + attached_card_ids(pokemon, "energies"))
    return len(ids) >= 4 or ({7, 8, 5}.issubset(ids) and pokemon_energy_count(pokemon) >= 4)
