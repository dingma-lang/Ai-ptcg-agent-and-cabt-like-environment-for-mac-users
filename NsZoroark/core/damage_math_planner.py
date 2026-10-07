from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

from card_db import get_db
from state_eval import active_pokemon, attached_card_ids, card_id, pokemon_hp
from core.target_board import BINDING_MOCHI_ID, ZOROARK_EX, active_is_poisoned, pokemon_name


@dataclass(frozen=True)
class DamageMath:
    base_damage: int = 0
    binding_mochi_bonus: int = 0
    black_belt_bonus: int = 0
    weakness_multiplier: int = 1
    resistance_penalty: int = 0
    final_damage: int = 0
    target_hp: int = 0
    is_ko: bool = False
    prize_value: int = 1
    reason: str = ""


def damage_with_modifiers(
    base_damage: int,
    binding_mochi: bool = False,
    black_belt: bool = False,
    target_ex: bool = False,
) -> int:
    damage = int(base_damage or 0)
    if binding_mochi:
        damage += 40
    if black_belt and target_ex:
        damage += 40
    return damage


def calculate_zoroark_damage(
    state: Any,
    copy_choice: Any,
    modifiers: Optional[Mapping[str, Any]] = None,
    target: Any = None,
) -> DamageMath:
    modifiers = modifiers or {}
    target = target if target is not None else active_pokemon(state, getattr(state, "opponent_index", 1))
    target_info = get_db().get_card(card_id(target))
    target_ex = bool(target_info and target_info.ex)
    base = int(getattr(copy_choice, "expected_damage", 0) or getattr(copy_choice, "base_damage", 0) or 0)

    attacking = active_pokemon(state)
    mochi_attached = attacking is not None and BINDING_MOCHI_ID in attached_card_ids(attacking, "tools")
    binding_mochi = bool(modifiers.get("binding_mochi", False) or (mochi_attached and active_is_poisoned(state)))
    black_belt = bool(modifiers.get("black_belt", False))
    before_weakness = damage_with_modifiers(base, binding_mochi, black_belt, target_ex)

    weakness_multiplier = 1
    resistance_penalty = 0
    if target_info:
        weakness = str(target_info.weakness or "").lower()
        resistance = str(target_info.resistance or "").lower()
        if "dark" in weakness or weakness == "d":
            weakness_multiplier = 2
        if "dark" in resistance or resistance == "d":
            resistance_penalty = 30

    final_damage = max(0, before_weakness * weakness_multiplier - resistance_penalty)
    hp = pokemon_hp(target)
    prize_value = target_info.prize_value if target_info else 1
    parts = [f"base {base}"]
    if binding_mochi:
        parts.append("+40 Binding Mochi")
    if black_belt and target_ex:
        parts.append("+40 Black Belt")
    if weakness_multiplier > 1:
        parts.append("weakness x2")
    if resistance_penalty:
        parts.append("-30 resistance")
    parts.append("KO" if hp and final_damage >= hp else "no KO")
    return DamageMath(
        base_damage=base,
        binding_mochi_bonus=40 if binding_mochi else 0,
        black_belt_bonus=40 if black_belt and target_ex else 0,
        weakness_multiplier=weakness_multiplier,
        resistance_penalty=resistance_penalty,
        final_damage=final_damage,
        target_hp=hp,
        is_ko=bool(hp and final_damage >= hp),
        prize_value=prize_value,
        reason=", ".join(parts),
    )


def modifier_changes_ko(state: Any, base_damage: int, bonus: int = 40, target: Any = None) -> bool:
    target = target if target is not None else active_pokemon(state, getattr(state, "opponent_index", 1))
    hp = pokemon_hp(target)
    return bool(hp and base_damage < hp <= base_damage + bonus)


def zoroark_has_binding_mochi(state: Any) -> bool:
    active = active_pokemon(state)
    return bool(active is not None and pokemon_name(active) == ZOROARK_EX and BINDING_MOCHI_ID in attached_card_ids(active, "tools"))
