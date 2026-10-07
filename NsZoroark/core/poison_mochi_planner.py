from __future__ import annotations

from typing import Any

from state_eval import OPT_ATTACH, OPT_PLAY, active_pokemon, attach_target_from_option, card_id, card_id_from_option, option_type, pokemon_hp
from core.damage_math_planner import modifier_changes_ko, zoroark_has_binding_mochi
from core.priority_tables import canonical_name_from_id
from core.target_board import BINDING_MOCHI_ID, PECHARUNT_EX, ZOROARK_EX, active_is_poisoned, has_name, opponent_active, pokemon_name, ready_zoroarks


def score_poison_mochi_option(state: Any, option: Any) -> float:
    name = canonical_name_from_id(card_id_from_option(state, option))
    if name != "Binding Mochi" and card_id_from_option(state, option) != BINDING_MOCHI_ID:
        return 0.0
    target = attach_target_from_option(state, option)
    if target is None:
        target = active_pokemon(state)
    target_name = pokemon_name(target)
    if target_name != ZOROARK_EX:
        return -4500.0
    if mochi_math_available(state):
        return 7200.0
    if has_name(state, PECHARUNT_EX) and ready_zoroarks(state):
        return 1800.0
    return -2200.0


def score_mochi_target_zoroark(state: Any, pokemon: Any) -> float:
    if pokemon_name(pokemon) != ZOROARK_EX:
        return -5000.0
    if mochi_math_available(state):
        return 7600.0
    if has_name(state, PECHARUNT_EX):
        return 1900.0
    return -1500.0


def mochi_math_available(state: Any) -> bool:
    target = opponent_active(state)
    hp = pokemon_hp(target)
    if not hp:
        return False
    return modifier_changes_ko(state, 250, 40, target) or (zoroark_has_binding_mochi(state) and active_is_poisoned(state) and hp <= 290)
