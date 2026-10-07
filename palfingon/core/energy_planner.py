from __future__ import annotations

from typing import Any, Optional

from state_eval import attach_target_from_option, attached_card_ids, card_id, card_id_from_option
from core.priority_tables import canonical_name_from_id


ENERGY_TYPE_BY_ID = {
    3: "water",
    4: "lightning",
}


def score_energy_option(state: Any, option: Any) -> float:
    energy_cid = card_id_from_option(state, option)
    target = attach_target_from_option(state, option)
    return score_energy_attachment(state, energy_cid, target)


def score_energy_attachment(state: Any, energy_card: Any, target_pokemon: Any) -> float:
    energy_cid = energy_card if isinstance(energy_card, int) else card_id(energy_card)
    target_cid = card_id(target_pokemon)
    if energy_cid is None or target_cid is None:
        return 0.0

    try:
        from core.palafin_planner import score_energy_attachment as score_palaking_energy

        return score_palaking_energy(state, energy_cid, target_pokemon)
    except Exception:
        pass

    energy_name = canonical_name_from_id(energy_cid)
    target_name = canonical_name_from_id(target_cid)
    if energy_name == "Basic Water Energy":
        if target_name in {"Finizen", "Palafin", "Palafin ex"}:
            return 1200.0
        return -1200.0
    if energy_name == "Basic Lightning Energy":
        if target_name in {"Dratini", "Dragonair", "Mega Dragonite ex"}:
            return 1200.0
        return -3000.0
    return -300.0


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
    try:
        from core.palafin_planner import score_crispin_target

        return score_crispin_target(state, energy_cid, canonical_name_from_id(energy_cid))
    except Exception:
        return 0.0
