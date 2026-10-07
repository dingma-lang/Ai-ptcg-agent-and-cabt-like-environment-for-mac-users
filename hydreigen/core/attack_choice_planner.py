from __future__ import annotations

from typing import Any

from card_db import get_db
from state_eval import OPT_ATTACK, active_pokemon, bench_pokemon, getv, option_type, pokemon_hp
from core.ceruledge_matchup import is_bench_damage_protected, is_ceruledge_matchup, valuable_obsidian_bench_targets


def score_attack_choice_option(state: Any, option: Any, base_score: float = 0.0) -> float:
    if option_type(option) != OPT_ATTACK:
        return 0.0
    attack = get_db().get_attack(getv(option, "attackId"))
    name = str(getattr(attack, "name", "") or "")
    if "Obsidian" in name:
        return score_obsidian_choice(state, base_score)
    if "Crashing Headbutt" in name:
        return score_crashing_headbutt_choice(state)
    return 0.0


def score_obsidian_choice(state: Any, base_score: float = 0.0) -> float:
    opponent = active_pokemon(state, state.opponent_index)
    active_ko = bool(opponent is not None and pokemon_hp(opponent) <= 130)
    valuable_targets = valuable_obsidian_bench_targets(state)
    if active_ko:
        return 1800.0 + len(valuable_targets) * 900.0
    if len(valuable_targets) >= 2:
        return 3600.0
    if is_ceruledge_matchup(state) and valuable_targets:
        return 2200.0
    if obsidian_bench_damage_low_value(state):
        return -3600.0
    return 0.0


def score_crashing_headbutt_choice(state: Any) -> float:
    opponent = active_pokemon(state, state.opponent_index)
    if opponent is None:
        return 0.0
    active_ko = pokemon_hp(opponent) <= 200
    if active_ko and obsidian_bench_damage_low_value(state):
        return 4200.0
    if active_ko and is_ceruledge_matchup(state):
        return 2600.0
    return 0.0


def obsidian_bench_damage_low_value(state: Any) -> bool:
    bench = bench_pokemon(state, state.opponent_index)
    if not bench:
        return True
    useful = [pokemon for pokemon in bench if not is_bench_damage_protected(pokemon) and pokemon_hp(pokemon) <= 130]
    return len(useful) == 0
