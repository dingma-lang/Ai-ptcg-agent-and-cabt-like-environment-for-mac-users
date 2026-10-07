from __future__ import annotations

from typing import Any, Optional

from card_db import get_db
from state_eval import active_pokemon, bench_pokemon, card_id, getv, pokemon_hp
from core.priority_tables import canonical_name_from_id


CERULEDGE_EX_ID = 320
CHARCADET_IDS = {204, 319, 796}
LUNATONE_ID = 675
SOLROCK_ID = 676
DRILBUR_IDS = {81, 526}


def is_ceruledge_matchup(state: Any) -> bool:
    names = set(visible_opponent_names(state))
    if "Ceruledge ex" in names or any(name == "Charcadet" for name in names):
        return True
    logs = getv(getattr(state, "obs", None), "logs", []) or []
    if isinstance(logs, list):
        text = " ".join(str(log) for log in logs[-30:]).lower()
        if "ceruledge" in text or "abyssal flames" in text:
            return True
    return False


def visible_opponent_names(state: Any) -> list[str]:
    names: list[str] = []
    for pokemon in [active_pokemon(state, state.opponent_index)] + bench_pokemon(state, state.opponent_index):
        name = canonical_name_from_id(card_id(pokemon))
        if name:
            names.append(name)
    return names


def ceruledge_engine_target_score(pokemon: Any) -> float:
    cid = card_id(pokemon)
    name = canonical_name_from_id(cid)
    if cid == LUNATONE_ID or name == "Lunatone":
        return 4200.0
    if cid == SOLROCK_ID or name == "Solrock":
        return 4000.0
    if cid in DRILBUR_IDS or name == "Drilbur":
        return 2600.0
    info = get_db().get_card(cid)
    text = ((getattr(info, "text", "") or "") + " " + " ".join(getattr(skill, "text", "") for skill in getattr(info, "skills", ()))).lower() if info else ""
    if "discard" in text and "energy" in text and "draw" in text:
        return 3200.0
    if "discard" in text and "energy" in text:
        return 1700.0
    if "draw" in text:
        return 900.0
    return 0.0


def is_bench_damage_protected(pokemon: Any) -> bool:
    info = get_db().get_card(card_id(pokemon))
    text = (getattr(info, "text", "") or "").lower() if info else ""
    return "prevent all damage done to this" in text and "bench" in text


def valuable_obsidian_bench_targets(state: Any) -> list[Any]:
    targets = []
    for pokemon in bench_pokemon(state, state.opponent_index):
        if is_bench_damage_protected(pokemon):
            continue
        if pokemon_hp(pokemon) <= 130 or ceruledge_engine_target_score(pokemon) > 0:
            targets.append(pokemon)
    return sorted(targets, key=ceruledge_engine_target_score, reverse=True)


def active_name(state: Any) -> str:
    return canonical_name_from_id(card_id(active_pokemon(state, state.opponent_index)))


def active_hp(state: Any) -> int:
    return pokemon_hp(active_pokemon(state, state.opponent_index))


def is_ceruledge_family_id(cid: Optional[int]) -> bool:
    return cid == CERULEDGE_EX_ID or cid in CHARCADET_IDS
