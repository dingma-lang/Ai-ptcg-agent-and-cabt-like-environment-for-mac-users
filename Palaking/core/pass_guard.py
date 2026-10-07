from __future__ import annotations

from typing import Any, Sequence

from action_classifier import ActionCategory, classify_legal_option
from card_db import get_db
from state_eval import OPT_ATTACK, OPT_ATTACH, OPT_END, OPT_EVOLVE, OPT_PLAY, bench_space, card_id_from_option, option_type
from core.priority_tables import canonical_name_from_id
from core.strategy_scope import use_palaking_strategy


def end_turn_penalty_if_useful_action_exists(state: Any, scores: Sequence[float]) -> float:
    if use_palaking_strategy(state):
        try:
            from core.giga_impact_planner import choose_giga_impact_priority_action

            giga = choose_giga_impact_priority_action(state, state.options, scores)
            if giga.should_act:
                if giga.score >= 8000.0:
                    return -10000.0
                return -7000.0
        except Exception:
            pass
        try:
            from core.palafin_planner import score_palaking_end_penalty

            palaking_penalty = score_palaking_end_penalty(state, scores)
            if palaking_penalty:
                return palaking_penalty
        except Exception:
            pass

    penalty = 0.0
    try:
        from core.resource_planner import should_attach_energy_this_turn, should_spend_supporter_this_turn

        supporter = should_spend_supporter_this_turn(state)
        energy = should_attach_energy_this_turn(state)
        if supporter.should_spend:
            penalty -= 3000.0
        if energy.should_spend:
            penalty -= 2500.0
    except Exception:
        pass

    try:
        from core.poffin_planner import should_use_poffin_now
        from core.pokepad_planner import should_use_pokepad_now

        if should_use_poffin_now(state, state.options).should_act:
            penalty -= 5000.0
        if should_use_pokepad_now(state, state.options).should_act:
            penalty -= 4000.0
    except Exception:
        pass

    try:
        from core.mega_gengar_planner import score_mega_gengar_option
        from core.toxtricity_engine_planner import score_toxtricity_option

        for option in state.options:
            if score_mega_gengar_option(state, option, 0.0) >= 1800.0:
                penalty -= 3000.0
                break
        for option in state.options:
            if score_toxtricity_option(state, option, 0.0) >= 1800.0:
                penalty -= 2500.0
                break
    except Exception:
        pass

    try:
        if bench_empty_and_basic_available(state) or basic_from_hand_available(state):
            penalty -= 3000.0
    except Exception:
        pass

    try:
        from core.fezandipiti_planner import fezandipiti_recovery_available

        if fezandipiti_recovery_available(state):
            penalty -= 2500.0
    except Exception:
        pass

    try:
        from core.stuck_recovery import pass_block_score

        penalty += pass_block_score(state)
    except Exception:
        pass

    try:
        hard = pre_end_resource_action_penalty(state, scores)
        penalty += hard
    except Exception:
        pass

    try:
        from core.danger_evaluator import CRITICAL, HIGH, evaluate_danger
        from core.pivot_planner import pivot_protective_action_available

        danger = evaluate_danger(state)
        if danger.severity in (HIGH, CRITICAL) and (danger.protective_action_available or pivot_protective_action_available(state)):
            penalty -= 2000.0
    except Exception:
        pass

    if penalty < 0.0:
        return penalty
    if useful_action_exists(state, scores):
        return -2000.0
    return 200.0


def useful_action_exists(state: Any, scores: Sequence[float]) -> bool:
    if use_palaking_strategy(state):
        try:
            from core.palafin_planner import useful_palaking_action_exists

            return useful_palaking_action_exists(state, scores)
        except Exception:
            pass
    for idx, option in enumerate(state.options):
        if option_type(option) == OPT_END:
            continue
        if basic_play_option_available(state, option):
            return True
        action = classify_legal_option(state, option, idx)
        if idx < len(scores) and scores[idx] >= 250.0:
            return True
        if action.category in (
            ActionCategory.EVOLVE,
            ActionCategory.RARE_CANDY_EVOLVE,
            ActionCategory.DRAW_OR_SEARCH,
            ActionCategory.PLAY_BASIC_TO_BENCH,
        ):
            return True
        if action.category == ActionCategory.PLAY_SUPPORTER and idx < len(scores) and scores[idx] >= 100.0:
            return True
        if action.category in (ActionCategory.ATTACH_ENERGY, ActionCategory.USE_ABILITY) and idx < len(scores) and scores[idx] >= 250.0:
            return True
        if option_type(option) == OPT_ATTACK and idx < len(scores) and scores[idx] > 50.0:
            return True
        name = canonical_name_from_id(card_id_from_option(state, option))
        if name in {"Buddy-Buddy Poffin", "Poke Pad", "Ultra Ball", "Rare Candy", "Lillie's Determination", "Crispin"}:
            return True
    return False


def pre_end_resource_action_penalty(state: Any, scores: Sequence[float]) -> float:
    penalty = 0.0
    for idx, option in enumerate(state.options):
        if option_type(option) == OPT_END:
            continue
        action = classify_legal_option(state, option, idx)
        score = scores[idx] if idx < len(scores) else 0.0
        name = action.card_name or canonical_name_from_id(card_id_from_option(state, option))
        if action.category in (ActionCategory.EVOLVE, ActionCategory.RARE_CANDY_EVOLVE) or option_type(option) == OPT_EVOLVE:
            penalty -= 6500.0
        elif action.category == ActionCategory.PLAY_SUPPORTER and score >= 100.0:
            penalty -= 5500.0
        elif action.category in (ActionCategory.PLAY_ITEM, ActionCategory.DRAW_OR_SEARCH) and useful_item_score(name, score):
            penalty -= 5000.0
        elif action.category == ActionCategory.ATTACH_ENERGY or option_type(option) == OPT_ATTACH:
            if score >= 500.0:
                penalty -= 4500.0
    return penalty


def useful_item_score(name: str, score: float) -> bool:
    if score >= 250.0:
        return True
    return name in {"Buddy-Buddy Poffin", "Poke Pad", "Ultra Ball", "Rare Candy", "Secret Box", "Surfing Beach", "Switch"} and score > 0.0


def basic_play_option_available(state: Any, option: Any) -> bool:
    if bench_space(state) <= 0 or option_type(option) != OPT_PLAY:
        return False
    card = get_db().get_card(card_id_from_option(state, option))
    return bool(card and card.card_type == "Pokemon" and card.basic)


def basic_from_hand_available(state: Any) -> bool:
    try:
        from core.basic_bench_planner import basic_bench_available

        return basic_bench_available(state)
    except Exception:
        return False


def bench_empty_and_basic_available(state: Any) -> bool:
    try:
        from state_eval import bench_pokemon

        if bench_pokemon(state):
            return False
    except Exception:
        return False
    for idx, option in enumerate(state.options):
        if basic_play_option_available(state, option):
            return True
        action = classify_legal_option(state, option, idx)
        name = canonical_name_from_id(card_id_from_option(state, option))
        if action.category == ActionCategory.PLAY_BASIC_TO_BENCH:
            return True
        if name in {"Buddy-Buddy Poffin", "Poke Pad", "Ultra Ball"}:
            return True
    return False
