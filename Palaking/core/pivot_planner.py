from __future__ import annotations

from typing import Any

from action_classifier import ActionCategory, classify_legal_option
from card_db import get_db
from state_eval import OPT_ABILITY, OPT_ATTACH, OPT_PLAY, OPT_RETREAT, active_pokemon, attach_target_from_option, bench_pokemon, bench_space, card_id, card_id_from_option, getv, option_type, player_has_condition, pokemon_energy_count, pokemon_hp, pokemon_max_hp, prize_count
from core.danger_evaluator import CRITICAL, HIGH, evaluate_danger
from core.energy_planner import pokemon_uses_energy_type
from core.priority_tables import CARD_IDS, canonical_name_from_id


PECHARUNT_EX_ID = CARD_IDS["Pecharunt ex"]
AIR_BALLOON_ID = CARD_IDS["Air Balloon"]


def score_pivot_option(state: Any, option: Any) -> float:
    cid = card_id_from_option(state, option)
    typ = option_type(option)
    if cid == PECHARUNT_EX_ID and typ == OPT_ABILITY:
        return score_pecharunt_ability(state)
    if cid == PECHARUNT_EX_ID and typ == OPT_PLAY:
        return score_pecharunt_bench(state)
    if cid == AIR_BALLOON_ID and typ in (OPT_ATTACH, OPT_PLAY):
        return score_air_balloon(state, option)
    if typ == OPT_RETREAT:
        return score_retreat_pivot(state)
    return 0.0


def score_pecharunt_ability(state: Any) -> float:
    target = best_darkness_pivot_target(state)
    if target is None:
        return -1300.0
    target_can_attack = can_attack_now(target)
    target_takes_ko = can_take_visible_ko(state, target)
    danger = evaluate_danger(state)
    active_stuck = active_is_stuck_or_exposed(state)
    target_card = get_db().get_card(card_id(target))
    if (
        prize_count(state, state.opponent_index) <= 2
        and target_card
        and target_card.prize_value >= 2
        and not target_can_attack
        and not target_takes_ko
    ):
        return -2200.0
    if poisoned_target_would_be_unsafe(state, target) and not target_can_attack:
        return -1700.0
    if not (target_can_attack or target_takes_ko or danger.severity in (HIGH, CRITICAL) or active_stuck):
        return -2600.0
    score = 100.0
    if target_can_attack:
        score += 1000.0
    if target_takes_ko:
        score += 1400.0
    if danger.severity in (HIGH, CRITICAL):
        score += 650.0
    if active_stuck:
        score += 500.0
    return score


def score_pecharunt_bench(state: Any) -> float:
    if bench_space(state) <= 0:
        return -5000.0
    if count_pecharunt_in_play(state) > 0:
        return -1000.0
    danger = evaluate_danger(state)
    if prize_count(state, state.opponent_index) <= 2 and danger.severity not in (HIGH, CRITICAL):
        return -1600.0
    if danger.bench_count == 0 and not safer_basic_option_available(state):
        return 3100.0
    if danger.bench_count <= 1 and (active_is_stuck_or_exposed(state) or darkness_attacker_on_bench(state)):
        return 2600.0
    return -600.0


def score_air_balloon(state: Any, option: Any) -> float:
    target = attach_target_from_option(state, option) or active_pokemon(state)
    target_id = card_id(target)
    name = canonical_name_from_id(target_id)
    if name in {"Pecharunt ex", "Fezandipiti ex"}:
        return -1600.0
    danger = evaluate_danger(state)
    score = 180.0
    if target is active_pokemon(state):
        score += 250.0
    if name in {"Gastly", "Haunter"}:
        score += 2800.0
    if name in {"Hydreigon ex", "Mega Gengar ex", "Pecharunt ex", "Fezandipiti ex"}:
        score += 220.0
    if active_is_stuck_or_exposed(state):
        score += 600.0
    if danger.severity in (HIGH, CRITICAL) and target is active_pokemon(state):
        score += 900.0
    return score


def score_retreat_pivot(state: Any) -> float:
    if best_retreat_target(state) is None:
        return -600.0
    danger = evaluate_danger(state)
    score = 250.0
    if danger.severity in (HIGH, CRITICAL):
        score += 700.0
    if active_is_stuck_or_exposed(state):
        score += 550.0
    return score


def score_post_ko_promotion_pivot(state: Any, pokemon: Any) -> float:
    name = canonical_name_from_id(card_id(pokemon))
    if name == "Haunter":
        return 2500.0
    if name == "Gastly":
        return 2300.0
    return 0.0


def pivot_protective_action_available(state: Any) -> bool:
    for option in state.options:
        if score_pivot_option(state, option) >= 650.0:
            return True
    return False


def best_darkness_pivot_target(state: Any) -> Any:
    best = None
    best_score = -9999
    for pokemon in bench_pokemon(state):
        if card_id(pokemon) == PECHARUNT_EX_ID:
            continue
        if not pokemon_uses_energy_type(pokemon, "D"):
            continue
        score = pokemon_energy_count(pokemon) * 120 + pokemon_hp(pokemon)
        if can_attack_now(pokemon):
            score += 700
        if can_take_visible_ko(state, pokemon):
            score += 1200
        if score > best_score:
            best = pokemon
            best_score = score
    return best


def best_retreat_target(state: Any) -> Any:
    best = None
    best_score = -9999
    for pokemon in bench_pokemon(state):
        score = pokemon_hp(pokemon)
        can_attack = can_attack_now(pokemon)
        card = get_db().get_card(card_id(pokemon))
        free_retreat = bool(card and card.retreat_cost == 0)
        if not can_attack and not free_retreat:
            continue
        if can_attack:
            score += 650
        if free_retreat:
            score += 250
        if card and card.prize_value > 1 and pokemon_hp(pokemon) <= max(40, pokemon_max_hp(pokemon) * 0.25):
            score -= 500
        if score > best_score:
            best = pokemon
            best_score = score
    return best


def active_is_stuck_or_exposed(state: Any) -> bool:
    active = active_pokemon(state)
    if active is None:
        return False
    if player_has_condition(state, "asleep") or player_has_condition(state, "paralyzed"):
        return True
    if not can_attack_now(active):
        return True
    hp = pokemon_hp(active)
    max_hp = pokemon_max_hp(active)
    return bool(max_hp and hp <= max(60, max_hp * 0.3))


def can_attack_now(pokemon: Any) -> bool:
    card = get_db().get_card(card_id(pokemon))
    if not card:
        return False
    energy = pokemon_energy_count(pokemon)
    return any(energy >= len(attack.cost or []) and int(getattr(attack, "damage", 0) or 0) > 0 for attack in card.attacks)


def can_take_visible_ko(state: Any, pokemon: Any) -> bool:
    opponent = active_pokemon(state, state.opponent_index)
    if opponent is None:
        return False
    hp = pokemon_hp(opponent)
    if hp <= 0:
        return False
    card = get_db().get_card(card_id(pokemon))
    if not card:
        return False
    energy = pokemon_energy_count(pokemon)
    return any(energy >= len(attack.cost or []) and int(getattr(attack, "damage", 0) or 0) >= hp for attack in card.attacks)


def poisoned_target_would_be_unsafe(state: Any, pokemon: Any) -> bool:
    del state
    return pokemon_hp(pokemon) <= 20


def darkness_attacker_on_bench(state: Any) -> bool:
    return any(pokemon_uses_energy_type(pokemon, "D") for pokemon in bench_pokemon(state))


def count_pecharunt_in_play(state: Any) -> int:
    return sum(1 for pokemon in [active_pokemon(state)] + bench_pokemon(state) if card_id(pokemon) == PECHARUNT_EX_ID)


def safer_basic_option_available(state: Any) -> bool:
    for idx, option in enumerate(state.options):
        action = classify_legal_option(state, option, idx)
        if action.category == ActionCategory.PLAY_BASIC_TO_BENCH and action.card_id in {227, 59, 833}:
            return True
    return False
