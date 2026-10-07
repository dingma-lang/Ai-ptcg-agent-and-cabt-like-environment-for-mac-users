from __future__ import annotations

from typing import Any

from state_eval import OPT_ATTACH, active_pokemon, attach_target_from_option, card_id, option_type
from core.priority_tables import canonical_name_from_id


def score_sequence_guard_option(state: Any, option: Any) -> float:
    if option_type(option) != OPT_ATTACH:
        return 0.0
    target = attach_target_from_option(state, option)
    if target is None:
        return 0.0
    target_name = canonical_name_from_id(card_id(target))
    if target is active_pokemon(state) and target_name not in {"Hydreigon ex", "Mega Gengar ex", "Zweilous", "Haunter"}:
        if bench_attacker_line_exists(state):
            return -1800.0
    return 0.0


def bench_attacker_line_exists(state: Any) -> bool:
    try:
        from state_eval import bench_pokemon

        for pokemon in bench_pokemon(state):
            if canonical_name_from_id(card_id(pokemon)) in {"Deino", "Zweilous", "Hydreigon ex", "Gastly", "Haunter", "Mega Gengar ex"}:
                return True
    except Exception:
        pass
    return False
