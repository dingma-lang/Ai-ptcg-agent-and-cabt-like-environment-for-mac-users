from __future__ import annotations

from typing import Any

from action_classifier import ActionCategory, classify_legal_option
from state_eval import CTX_DAMAGE, CTX_DAMAGE_COUNTER, CTX_DAMAGE_COUNTER_ANY, CTX_EFFECT_TARGET, card_id, pokemon_from_card_option
from core.ceruledge_matchup import ceruledge_engine_target_score, is_bench_damage_protected


def score_bench_target_option(state: Any, option: Any, option_index: int = 0) -> float:
    if state.context not in (CTX_DAMAGE, CTX_DAMAGE_COUNTER, CTX_DAMAGE_COUNTER_ANY, CTX_EFFECT_TARGET):
        return 0.0
    action = classify_legal_option(state, option, option_index)
    if action.category not in (ActionCategory.CHOOSE_ATTACK_TARGET, ActionCategory.CHOOSE_EFFECT_TARGET):
        return 0.0
    pokemon = pokemon_from_card_option(state, option)
    if pokemon is None:
        return 0.0
    if is_bench_damage_protected(pokemon):
        return -4200.0
    score = ceruledge_engine_target_score(pokemon)
    if score:
        return score
    return 0.0
