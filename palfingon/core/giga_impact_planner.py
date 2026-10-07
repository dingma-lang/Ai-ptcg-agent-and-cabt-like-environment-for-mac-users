from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

from card_db import get_db
from state_eval import OPT_ATTACK, OPT_ATTACH, OPT_PLAY, active_pokemon, attach_target_from_option, bench_pokemon, card_id, card_id_from_option, getv, option_type, pokemon_hp, prize_count
from core.palafin_attack_state import track_giga_impact_lock
from core.palafin_planner import BOSS, KIERAN, PALAFIN_EX, WATER_ENERGY, attached_energy_count_any, benched_palafin_ex_ready_to_attack
from core.switch_reset_planner import find_palafin_reset_line, reset_line_available_next_turn
from core.priority_tables import canonical_name_from_id


@dataclass(frozen=True)
class AttackScore:
    score: float
    reason: str


@dataclass(frozen=True)
class GigaImpactChoice:
    should_act: bool
    option_index: Optional[int] = None
    score: float = 0.0
    reason: str = ""


def is_giga_impact_option(option: Any) -> bool:
    if option_type(option) != OPT_ATTACK:
        return False
    attack = get_db().get_attack(getv(option, "attackId"))
    if attack is None:
        return False
    return "giga impact" in str(getattr(attack, "name", "") or "").lower()


def score_giga_impact_attack(state: Any, attack_option: Any, opponent_model: Any = None) -> AttackScore:
    del opponent_model
    if not is_giga_impact_option(attack_option):
        return AttackScore(0.0, "")
    active = active_pokemon(state)
    if canonical_name_from_id(card_id(active)) != "Palafin ex":
        return AttackScore(0.0, "")
    status = track_giga_impact_lock(state, None)
    if status.restriction_applies_now:
        return AttackScore(-9000.0, "Giga Impact lock applies only to this Palafin ex.")
    opponent = active_pokemon(state, state.opponent_index)
    opp_hp = pokemon_hp(opponent)
    from policy import estimate_attack_damage, prize_value_for_card

    attack = get_db().get_attack(getv(attack_option, "attackId"))
    damage = estimate_attack_damage(state, attack, active, opponent)
    if damage <= 0:
        return AttackScore(-20000.0, "Avoid Giga Impact: the visible target prevents its damage.")
    prize_value = prize_value_for_card(card_id(opponent))
    if opp_hp > 0 and damage >= opp_hp:
        if prize_count(state) <= prize_value:
            return AttackScore(10000.0, "Giga Impact takes final prizes.")
        if prize_value >= 2:
            return AttackScore(8500.0, "Giga Impact takes a two-prize Pokémon ex KO.")
        return AttackScore(8500.0, "Giga Impact takes a KO.")
    if opponent_can_win_by_return_ko(state):
        return AttackScore(900.0, "Giga Impact damage is not worth exposing a two-prize attacker without a KO.")
    if opp_hp > 0 and damage >= max(140, int(opp_hp * 0.55)):
        if reset_line_available_next_turn(state) or benched_palafin_ex_ready_to_attack(state):
            return AttackScore(6000.0, "Giga Impact pressure is strong and the downside can be reset by switching.")
        return AttackScore(2500.0, "Giga Impact is meaningful damage even without a visible reset.")
    return AttackScore(500.0, "Giga Impact is low-pressure into this target.")


def choose_giga_impact_priority_action(state: Any, legal_options: Sequence[Any], scores: Sequence[float] | None = None) -> GigaImpactChoice:
    del scores
    reset = find_palafin_reset_line(state, legal_options)
    if reset.available and reset.option_index is not None:
        return GigaImpactChoice(True, reset.option_index, reset.score, reset.reason)

    kieran_idx = kieran_for_giga_ko_index(state, legal_options)
    if kieran_idx is not None:
        return GigaImpactChoice(True, kieran_idx, 9000.0, "Use Kieran because +30 makes Giga Impact take a KO.")
    boss_idx = boss_for_giga_route_index(state, legal_options)
    if boss_idx is not None:
        return GigaImpactChoice(True, boss_idx, 8800.0, "Use Boss's Orders because Giga Impact creates a prize route.")
    attach_idx = water_attach_for_giga_index(state, legal_options)
    if attach_idx is not None:
        return GigaImpactChoice(True, attach_idx, 8000.0, "Attach Water because it enables Giga Impact.")

    best = GigaImpactChoice(False, reason="No valuable Giga Impact line.")
    for idx, option in enumerate(legal_options):
        score = score_giga_impact_attack(state, option).score
        reason = score_giga_impact_attack(state, option).reason
        if score > best.score:
            best = GigaImpactChoice(score >= 2500.0, idx, score, reason)
    return best


def water_attach_for_giga_index(state: Any, legal_options: Sequence[Any]) -> Optional[int]:
    active = active_pokemon(state)
    if canonical_name_from_id(card_id(active)) != "Palafin ex" or attached_energy_count_any(active) > 0:
        return None
    for idx, option in enumerate(legal_options):
        target = attach_target_from_option(state, option)
        if (
            option_type(option) == OPT_ATTACH
            and card_id_from_option(state, option) == WATER_ENERGY
            and target is not None
            and target is active
        ):
            return idx
    return None


def kieran_for_giga_ko_index(state: Any, legal_options: Sequence[Any]) -> Optional[int]:
    active = active_pokemon(state)
    if canonical_name_from_id(card_id(active)) != "Palafin ex" or attached_energy_count_any(active) <= 0:
        return None
    opponent = active_pokemon(state, state.opponent_index)
    hp = pokemon_hp(opponent)
    if not (250 < hp <= 280):
        return None
    for idx, option in enumerate(legal_options):
        if option_type(option) == OPT_PLAY and card_id_from_option(state, option) == KIERAN:
            return idx
    return None


def boss_for_giga_route_index(state: Any, legal_options: Sequence[Any]) -> Optional[int]:
    active = active_pokemon(state)
    if canonical_name_from_id(card_id(active)) != "Palafin ex" or attached_energy_count_any(active) <= 0:
        return None
    from core.expert_battle_planner import ko_damage

    current_target = active_pokemon(state, state.opponent_index)
    current_info = get_db().get_card(card_id(current_target))
    current_prizes = current_info.prize_value if current_info and 0 < pokemon_hp(current_target) <= ko_damage(state, active, current_target) else 0
    if not any(0 < pokemon_hp(p) <= ko_damage(state, active, p)
               and get_db().get_card(card_id(p)).prize_value > current_prizes
               for p in bench_pokemon(state, state.opponent_index) if get_db().get_card(card_id(p))):
        return None
    for idx, option in enumerate(legal_options):
        if option_type(option) == OPT_PLAY and card_id_from_option(state, option) == BOSS:
            return idx
    return None


def opponent_is_ex(pokemon: Any) -> bool:
    info = get_db().get_card(card_id(pokemon))
    return bool(info and getattr(info, "ex", False))


def opponent_can_win_by_return_ko(state: Any) -> bool:
    try:
        return prize_count(state, state.opponent_index) <= 2
    except Exception:
        return False


__all__ = [
    "AttackScore",
    "GigaImpactChoice",
    "score_giga_impact_attack",
    "choose_giga_impact_priority_action",
    "is_giga_impact_option",
]
