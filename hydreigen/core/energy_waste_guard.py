from __future__ import annotations

from typing import Any

from state_eval import OPT_ATTACH, OPT_CARD, active_pokemon, attach_target_from_option, card_id, option_type, pokemon_energy_count
from core.priority_tables import canonical_name_from_id


WASTE_TARGET_NAMES = {"Toxel", "Toxtricity", "Pecharunt ex", "Fezandipiti ex"}
ATTACKER_LINE_NAMES = {"Deino", "Zweilous", "Hydreigon ex", "Gastly", "Haunter", "Mega Gengar ex"}


def score_energy_waste_option(state: Any, option: Any) -> float:
    typ = option_type(option)
    if typ == OPT_ATTACH:
        target = attach_target_from_option(state, option)
    elif typ == OPT_CARD:
        try:
            from state_eval import CTX_ATTACH_TO, pokemon_from_card_option

            if getattr(state, "context", None) != CTX_ATTACH_TO:
                return 0.0
            target = pokemon_from_card_option(state, option)
        except Exception:
            return 0.0
    else:
        return 0.0
    return score_energy_target_guard(state, target)


def score_energy_target_guard(state: Any, target: Any) -> float:
    name = canonical_name_from_id(card_id(target))
    if not name:
        return 0.0
    if name in WASTE_TARGET_NAMES and not support_energy_exception(state, target):
        return -9000.0
    if name in ATTACKER_LINE_NAMES:
        return 1200.0
    return 0.0


def support_energy_exception(state: Any, target: Any) -> bool:
    if target is active_pokemon(state) and must_retreat_or_survive(state, target):
        return True
    return can_take_immediate_ko(state, target)


def must_retreat_or_survive(state: Any, target: Any) -> bool:
    del state
    return pokemon_energy_count(target) == 0


def can_take_immediate_ko(state: Any, target: Any) -> bool:
    try:
        from policy import can_pokemon_take_ko

        return bool(can_pokemon_take_ko(state, target))
    except Exception:
        return False


def energy_guard_reason(state: Any, target: Any) -> str:
    name = canonical_name_from_id(card_id(target))
    if name == "Pecharunt ex":
        return "Block Energy attachment to Pecharunt ex because no attack/retreat purpose exists."
    if name in {"Toxel", "Toxtricity"}:
        return f"Block Energy attachment to {name} because it is Energy engine, not attacker."
    if name == "Fezandipiti ex":
        return "Block Energy attachment to Fezandipiti ex because no attack/retreat purpose exists."
    return "Energy attachment is allowed."
