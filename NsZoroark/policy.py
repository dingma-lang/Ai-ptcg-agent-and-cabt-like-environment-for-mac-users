from __future__ import annotations

import math
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from action_reasoner import ActionClass, classify_option, turn_rules
from action_classifier import ActionCategory, ClassifiedAction, classify_legal_option
from card_db import AttackInfo, CardInfo, get_db
from deck_profile import card_priority, list_value, load_deck_ids, load_profile
from memory import begin_decision_timer, finish_decision
from turn_sequencer import apply_turn_sequence
from state_eval import (
    AREA_ACTIVE,
    AREA_BENCH,
    AREA_PRIZE,
    CTX_ACTIVATE,
    CTX_ATTACH_FROM,
    CTX_ATTACH_TO,
    CTX_AFFECT_SPECIAL_CONDITION,
    CTX_ATTACK,
    CTX_COIN_HEAD,
    CTX_DAMAGE,
    CTX_DAMAGE_COUNTER,
    CTX_DAMAGE_COUNTER_ANY,
    CTX_DAMAGE_COUNTER_COUNT,
    CTX_DISCARD,
    CTX_DISCARD_CARD_OR_ATTACHED_CARD,
    CTX_DISCARD_ENERGY,
    CTX_DISCARD_ENERGY_CARD,
    CTX_DISCARD_TOOL_CARD,
    CTX_DRAW_COUNT,
    CTX_EFFECT_TARGET,
    CTX_EVOLVE,
    CTX_EVOLVES_FROM,
    CTX_EVOLVES_TO,
    CTX_FIRST_EFFECT,
    CTX_HEAL,
    CTX_IS_FIRST,
    CTX_LOOK,
    CTX_MAIN,
    CTX_MORE_DEVOLVE,
    CTX_MULLIGAN,
    CTX_NOT_MOVE,
    CTX_REMOVE_DAMAGE_COUNTER,
    CTX_REMOVE_DAMAGE_COUNTER_COUNT,
    CTX_RECOVER_SPECIAL_CONDITION,
    CTX_SETUP_ACTIVE,
    CTX_SETUP_BENCH,
    CTX_SWITCH,
    CTX_TO_ACTIVE,
    CTX_TO_BENCH,
    CTX_TO_DECK,
    CTX_TO_DECK_BOTTOM,
    CTX_TO_FIELD,
    CTX_TO_HAND,
    CTX_TO_HAND_ENERGY,
    CTX_TO_PRIZE,
    OPT_ABILITY,
    OPT_ATTACH,
    OPT_CARD,
    OPT_DISCARD,
    OPT_END,
    OPT_ENERGY,
    OPT_ENERGY_CARD,
    OPT_EVOLVE,
    OPT_NUMBER,
    OPT_PLAY,
    OPT_RETREAT,
    OPT_SKILL,
    OPT_TOOL_CARD,
    OPT_ATTACK,
    OPT_YES,
    OPT_NO,
    SELECT_ATTACK,
    active_pokemon,
    attach_target_from_option,
    attached_card_id_from_option,
    attached_card_ids,
    bench_pokemon,
    bench_space,
    card_id,
    card_id_from_option,
    count_card_in_discard,
    count_seen_card,
    deck_count,
    discard_cards,
    enum_int,
    get_card_from_area,
    get_pokemon_by_area,
    getv,
    hand_count,
    hand_cards,
    int_or,
    iter_in_play,
    normalize_state,
    option_number,
    option_type,
    player_has_condition,
    pokemon_damage,
    pokemon_energy_count,
    pokemon_from_card_option,
    pokemon_hp,
    pokemon_max_hp,
    prize_count,
)


WINNING_ATTACK_SCORE = 20000.0
KO_ATTACK_SCORE = 10000.0
OPPONENT_DECK_PRESSURE_THRESHOLD = 15


class MomentType:
    SETUP = "setup moment"
    OUR_MAIN_TURN = "our main turn"
    ATTACK_SELECTION = "attack-selection moment"
    EFFECT_RESOLUTION = "effect-resolution moment"
    PRIZE_SELECTION = "prize-selection moment"
    FORCED_REPLACEMENT = "forced-replacement moment"
    OPPONENT_TURN_RESPONSE = "opponent-turn response moment"
    UNKNOWN = "unknown moment"


MANDATORY_PROMPT_CATEGORIES = {
    ActionCategory.SETUP_CHOOSE_ACTIVE,
    ActionCategory.SETUP_CHOOSE_BENCH,
    ActionCategory.MULLIGAN_DECISION,
    ActionCategory.GO_FIRST_SECOND_DECISION,
    ActionCategory.PRIZE_SELECTION,
    ActionCategory.PROMOTE_AFTER_KO,
    ActionCategory.DISCARD_COST,
    ActionCategory.COUNT_SELECTION,
    ActionCategory.SPECIAL_CONDITION_CHECK,
}

MAIN_TURN_CATEGORIES = {
    ActionCategory.DRAW_OR_SEARCH,
    ActionCategory.PLAY_BASIC_TO_BENCH,
    ActionCategory.EVOLVE,
    ActionCategory.RARE_CANDY_EVOLVE,
    ActionCategory.ATTACH_ENERGY,
    ActionCategory.PLAY_ITEM,
    ActionCategory.PLAY_SUPPORTER,
    ActionCategory.PLAY_STADIUM,
    ActionCategory.USE_ABILITY,
    ActionCategory.RETREAT,
    ActionCategory.SWITCH_ACTIVE,
    ActionCategory.ATTACK,
    ActionCategory.END_TURN,
}

EFFECT_RESOLUTION_CONTEXTS = {
    CTX_ACTIVATE,
    CTX_AFFECT_SPECIAL_CONDITION,
    CTX_ATTACH_FROM,
    CTX_ATTACH_TO,
    CTX_COIN_HEAD,
    CTX_DAMAGE,
    CTX_DAMAGE_COUNTER,
    CTX_DAMAGE_COUNTER_ANY,
    CTX_DAMAGE_COUNTER_COUNT,
    CTX_DISCARD,
    CTX_DISCARD_CARD_OR_ATTACHED_CARD,
    CTX_DISCARD_ENERGY,
    CTX_DISCARD_ENERGY_CARD,
    CTX_DISCARD_TOOL_CARD,
    CTX_DRAW_COUNT,
    CTX_EFFECT_TARGET,
    CTX_EVOLVE,
    CTX_EVOLVES_FROM,
    CTX_EVOLVES_TO,
    CTX_FIRST_EFFECT,
    CTX_HEAL,
    CTX_LOOK,
    CTX_MORE_DEVOLVE,
    CTX_NOT_MOVE,
    CTX_RECOVER_SPECIAL_CONDITION,
    CTX_REMOVE_DAMAGE_COUNTER,
    CTX_REMOVE_DAMAGE_COUNTER_COUNT,
    CTX_SWITCH,
    CTX_TO_BENCH,
    CTX_TO_DECK,
    CTX_TO_DECK_BOTTOM,
    CTX_TO_FIELD,
    CTX_TO_HAND,
    CTX_TO_HAND_ENERGY,
}


def choose_action(obs_dict: dict) -> List[int]:
    started_at = begin_decision_timer()
    try:
        if not isinstance(obs_dict, dict):
            return []

        select = parse_select(obs_dict)
        if "select" in obs_dict and select is None and obs_dict.get("current") is None:
            return load_deck_ids()
        if select is None:
            return []

        state = parse_state(obs_dict)
        options = classify_all_options(state, select)
        if not state.options:
            return []

        moment = identify_moment_type(state, select, options)
        try:
            setattr(state, "moment_type", moment)
        except Exception:
            pass

        if is_mandatory_prompt(select, options):
            return choose_mandatory_action(state, select, options)

        if is_setup_phase(state, select, options):
            return choose_setup_action(state, select, options)

        if is_opponent_turn_prompt(state, select, options):
            return choose_reaction_action(state, select, options)

        if moment == MomentType.EFFECT_RESOLUTION:
            return choose_effect_resolution_action(state, select, options)

        if is_our_main_turn(state, select, options):
            return choose_main_turn_action(state, select, options)

        return safe_fallback(select, state)
    except Exception:
        return emergency_fallback(obs_dict)
    finally:
        try:
            finish_decision(obs_dict, started_at)
        except Exception:
            pass


def parse_state(obs_dict: dict) -> Any:
    return normalize_state(obs_dict)


def parse_select(obs_dict: dict) -> Any:
    if not isinstance(obs_dict, dict) or "select" not in obs_dict:
        return None
    return obs_dict.get("select")


def classify_all_options(state: Any, select: Any) -> List[ClassifiedAction]:
    options = getv(select, "option", []) or []
    if not isinstance(options, list):
        return []
    return [classify_legal_option(state, option, idx) for idx, option in enumerate(options)]


def identify_moment_type(state: Any, select: Any, options: Sequence[ClassifiedAction]) -> str:
    context = int_or(getv(select, "context", -1), -1)
    categories = {option.category for option in options}
    turn_player = current_turn_player_index(state)

    if ActionCategory.PRIZE_SELECTION in categories:
        return MomentType.PRIZE_SELECTION
    if ActionCategory.PROMOTE_AFTER_KO in categories:
        return MomentType.FORCED_REPLACEMENT
    if context in (CTX_SETUP_ACTIVE, CTX_SETUP_BENCH, CTX_MULLIGAN, CTX_IS_FIRST) or is_pre_first_turn(state):
        return MomentType.SETUP
    if is_attack_selection_context(state, select, options):
        return MomentType.ATTACK_SELECTION
    if is_main_action_window(select, options):
        return MomentType.OUR_MAIN_TURN
    if turn_player is not None and turn_player != state.your_index:
        return MomentType.OPPONENT_TURN_RESPONSE
    if context in EFFECT_RESOLUTION_CONTEXTS or categories & {
        ActionCategory.CHOOSE_ATTACK_TARGET,
        ActionCategory.CHOOSE_EFFECT_TARGET,
        ActionCategory.DISCARD_COST,
        ActionCategory.RECOVER_FROM_DISCARD,
        ActionCategory.SHUFFLE_INTO_DECK,
        ActionCategory.YES_NO_DECISION,
        ActionCategory.COUNT_SELECTION,
        ActionCategory.SPECIAL_CONDITION_CHECK,
    }:
        return MomentType.EFFECT_RESOLUTION
    if context == CTX_MAIN and (turn_player is None or turn_player == state.your_index):
        return MomentType.OUR_MAIN_TURN
    if categories & MAIN_TURN_CATEGORIES and (turn_player is None or turn_player == state.your_index):
        return MomentType.OUR_MAIN_TURN
    return MomentType.UNKNOWN


def is_main_action_window(select: Any, options: Sequence[ClassifiedAction]) -> bool:
    context = int_or(getv(select, "context", -1), -1)
    if context != CTX_MAIN:
        return False
    categories = {option.category for option in options}
    return bool(categories & {
        ActionCategory.DRAW_OR_SEARCH,
        ActionCategory.PLAY_BASIC_TO_BENCH,
        ActionCategory.EVOLVE,
        ActionCategory.RARE_CANDY_EVOLVE,
        ActionCategory.ATTACH_ENERGY,
        ActionCategory.PLAY_ITEM,
        ActionCategory.PLAY_SUPPORTER,
        ActionCategory.PLAY_STADIUM,
        ActionCategory.USE_ABILITY,
        ActionCategory.RETREAT,
        ActionCategory.SWITCH_ACTIVE,
        ActionCategory.ATTACK,
        ActionCategory.END_TURN,
    })


def is_mandatory_prompt(select: Any, options: Sequence[ClassifiedAction]) -> bool:
    min_count = max(0, int_or(getv(select, "minCount", 0), 0))
    if min_count <= 0:
        return False
    return any(option.category in MANDATORY_PROMPT_CATEGORIES for option in options)


def is_setup_phase(state: Any, select: Any, options: Sequence[ClassifiedAction]) -> bool:
    del options
    context = int_or(getv(select, "context", -1), -1)
    return context in (CTX_SETUP_ACTIVE, CTX_SETUP_BENCH, CTX_MULLIGAN, CTX_IS_FIRST) or is_pre_first_turn(state)


def is_opponent_turn_prompt(state: Any, select: Any, options: Sequence[ClassifiedAction]) -> bool:
    if is_main_action_window(select, options):
        return False
    turn_player = current_turn_player_index(state)
    return turn_player is not None and turn_player != state.your_index


def is_our_main_turn(state: Any, select: Any, options: Sequence[ClassifiedAction]) -> bool:
    context = int_or(getv(select, "context", -1), -1)
    turn_player = current_turn_player_index(state)
    if is_main_action_window(select, options):
        return True
    if turn_player is not None and turn_player != state.your_index:
        return False
    if context in (CTX_MAIN, CTX_ATTACK):
        return True
    return any(option.category in MAIN_TURN_CATEGORIES for option in options)


def choose_mandatory_action(state: Any, select: Any, options: Sequence[ClassifiedAction]) -> List[int]:
    return choose_with_state_machine_scores(state, select, options, allow_search=False)


def choose_setup_action(state: Any, select: Any, options: Sequence[ClassifiedAction]) -> List[int]:
    return choose_with_state_machine_scores(state, select, options, allow_search=False)


def choose_reaction_action(state: Any, select: Any, options: Sequence[ClassifiedAction]) -> List[int]:
    return choose_with_state_machine_scores(state, select, options, allow_search=False)


def choose_effect_resolution_action(state: Any, select: Any, options: Sequence[ClassifiedAction]) -> List[int]:
    return choose_with_state_machine_scores(state, select, options, allow_search=False)


def choose_main_turn_action(state: Any, select: Any, options: Sequence[ClassifiedAction]) -> List[int]:
    return choose_with_state_machine_scores(state, select, options, allow_search=True)


def choose_with_state_machine_scores(
    state: Any,
    select: Any,
    options: Sequence[ClassifiedAction],
    allow_search: bool,
) -> List[int]:
    moment = getattr(state, "moment_type", MomentType.UNKNOWN)
    scores = apply_moment_adjustments(state, score_options(state), options, moment)
    zoroark_specific = use_ns_zoroark_strategy(state)

    if allow_search and zoroark_specific:
        if not immediate_ko_or_win_available(state, scores):
            try:
                from core.zoroark_planner import choose_zoroark_priority_action

                zoroark_choice = choose_zoroark_priority_action(state, state.options, scores)
                if zoroark_choice is not None:
                    return finalize_choice(state, sanitize_choice(state, [zoroark_choice], scores), scores)
            except Exception:
                pass

    return finalize_choice(state, sanitize_choice(state, choose_by_scores(state, scores), scores), scores)


def immediate_ko_or_win_available(state: Any, scores: Sequence[float]) -> bool:
    for idx, score in enumerate(scores):
        if score >= KO_ATTACK_SCORE and idx < len(state.options) and option_type(state.options[idx]) == OPT_ATTACK:
            return True
    return False


def apply_moment_adjustments(
    state: Any,
    scores: Sequence[float],
    options: Sequence[ClassifiedAction],
    moment: str,
) -> List[float]:
    adjusted = list(scores)
    for action in options:
        if not (0 <= action.index < len(adjusted)):
            continue
        adjusted[action.index] += moment_bonus(state, action, moment)
    return adjusted


def moment_bonus(state: Any, action: ClassifiedAction, moment: str) -> float:
    category = action.category
    if moment == MomentType.PRIZE_SELECTION:
        return 10000.0 if category == ActionCategory.PRIZE_SELECTION else -1000.0
    if moment == MomentType.FORCED_REPLACEMENT:
        return 8000.0 if category == ActionCategory.PROMOTE_AFTER_KO else -1000.0
    if moment == MomentType.SETUP:
        if category in (ActionCategory.SETUP_CHOOSE_ACTIVE, ActionCategory.SETUP_CHOOSE_BENCH):
            return 700.0
        if category in (ActionCategory.MULLIGAN_DECISION, ActionCategory.GO_FIRST_SECOND_DECISION):
            return 500.0
        if category == ActionCategory.END_TURN:
            return -500.0
        return 0.0
    if moment == MomentType.OPPONENT_TURN_RESPONSE:
        if category in (ActionCategory.YES_NO_DECISION, ActionCategory.SPECIAL_CONDITION_CHECK, ActionCategory.CHOOSE_EFFECT_TARGET):
            return 300.0
        if category in (ActionCategory.PLAY_SUPPORTER, ActionCategory.PLAY_STADIUM, ActionCategory.ATTACH_ENERGY, ActionCategory.RETREAT):
            return -300.0
        return 0.0
    if moment == MomentType.ATTACK_SELECTION:
        if category == ActionCategory.ATTACK:
            return 350.0
        if category == ActionCategory.END_TURN:
            return -150.0
        return -75.0
    if moment == MomentType.EFFECT_RESOLUTION:
        if category in (
            ActionCategory.DRAW_OR_SEARCH,
            ActionCategory.CHOOSE_ATTACK_TARGET,
            ActionCategory.CHOOSE_EFFECT_TARGET,
            ActionCategory.DISCARD_COST,
            ActionCategory.RECOVER_FROM_DISCARD,
            ActionCategory.SHUFFLE_INTO_DECK,
            ActionCategory.YES_NO_DECISION,
            ActionCategory.COUNT_SELECTION,
            ActionCategory.SPECIAL_CONDITION_CHECK,
        ):
            return 250.0
        return 0.0
    if moment == MomentType.OUR_MAIN_TURN:
        if category == ActionCategory.ATTACK and useful_pre_attack_option_exists_for_moment(state):
            return -125.0
        return 0.0
    return 0.0


def finalize_choice(state: Any, choice: List[int], scores: Sequence[float]) -> List[int]:
    try:
        from decision_reason import log_decision_if_enabled

        log_decision_if_enabled(state, scores, choice)
    except Exception:
        pass
    return choice


def safe_fallback(select: Any, state: Optional[Any] = None) -> List[int]:
    options = getv(select, "option", []) or []
    if not isinstance(options, list) or not options:
        return []
    min_count = max(0, int_or(getv(select, "minCount", 0), 0))
    max_count = min(len(options), max(min_count, int_or(getv(select, "maxCount", min_count), min_count)))
    if max_count <= 0:
        return []
    if min_count == 0:
        return []
    for idx, option in enumerate(options):
        if option_type(option) == OPT_END and min_count <= 1 <= max_count:
            choice = [idx]
            if state is not None:
                return finalize_choice(state, choice, [0.0] * len(options))
            return choice
    choice = list(range(min(min_count, len(options))))
    if state is not None:
        return finalize_choice(state, choice, [0.0] * len(options))
    return choice


def current_turn_player_index(state: Any) -> Optional[int]:
    for key in (
        "turnPlayer",
        "turnPlayerIndex",
        "currentPlayer",
        "currentPlayerIndex",
        "activePlayer",
        "activePlayerIndex",
        "playerTurn",
        "playerTurnIndex",
        "actingPlayer",
        "actingPlayerIndex",
    ):
        value = getv(state.current, key)
        if value is None:
            continue
        player = int_or(value, -1)
        if player in (0, 1):
            return player
    turn = int_or(getv(state.current, "turn", 0), 0)
    first_player = int_or(getv(state.current, "firstPlayer", -1), -1)
    if turn <= 0 or first_player not in (0, 1):
        return None
    return first_player if turn % 2 == 1 else 1 - first_player


def is_pre_first_turn(state: Any) -> bool:
    turn = int_or(getv(state.current, "turn", 0), 0)
    first_player = int_or(getv(state.current, "firstPlayer", -1), -1)
    return turn <= 0 or first_player == -1


def is_attack_selection_context(state: Any, select: Any, options: Sequence[ClassifiedAction]) -> bool:
    del state
    context = int_or(getv(select, "context", -1), -1)
    select_type = int_or(getv(select, "type", -1), -1)
    categories = {option.category for option in options}
    if select_type == SELECT_ATTACK or context == CTX_ATTACK:
        return True
    return bool(ActionCategory.ATTACK in categories and categories <= {ActionCategory.ATTACK, ActionCategory.END_TURN})


def useful_pre_attack_option_exists_for_moment(state: Any) -> bool:
    for idx, option in enumerate(state.options):
        action = classify_legal_option(state, option, idx)
        if action.category in (
            ActionCategory.DRAW_OR_SEARCH,
            ActionCategory.PLAY_BASIC_TO_BENCH,
            ActionCategory.EVOLVE,
            ActionCategory.RARE_CANDY_EVOLVE,
            ActionCategory.ATTACH_ENERGY,
            ActionCategory.SWITCH_ACTIVE,
            ActionCategory.RETREAT,
            ActionCategory.PLAY_ITEM,
            ActionCategory.PLAY_SUPPORTER,
        ):
            return True
    return False


def score_options(state: Any) -> List[float]:
    raw_scores = [
        score_option(state, option, option_index=index, all_options=state.options)
        for index, option in enumerate(state.options)
    ]
    try:
        sequenced_scores, _ = apply_turn_sequence(state, raw_scores)
        return apply_card_analysis_priority_engine(state, apply_deck_priority_engine(state, sequenced_scores))
    except Exception:
        return apply_card_analysis_priority_engine(state, apply_deck_priority_engine(state, raw_scores))


def apply_deck_priority_engine(state: Any, scores: Sequence[float]) -> List[float]:
    adjusted = list(scores)
    if use_ns_zoroark_strategy(state):
        return apply_zoroark_priority_engine(state, adjusted)
    return adjusted


def use_ns_zoroark_strategy(state: Any) -> bool:
    try:
        from core.strategy_scope import use_ns_zoroark_strategy as active

        return active(state)
    except Exception:
        return False


def apply_zoroark_priority_engine(state: Any, scores: Sequence[float]) -> List[float]:
    adjusted = apply_general_priority_engine(state, scores)
    try:
        from core.energy_planner_zoroark import score_energy_option_zoroark
        from core.night_joker_planner import score_night_joker_option
        from core.pecharunt_planner import score_pecharunt_option
        from core.poison_mochi_planner import score_poison_mochi_option
        from core.recovery_planner_zoroark import score_recovery_option_zoroark
        from core.search_planner_zoroark import score_search_option_zoroark, score_setup_basic_play_zoroark, should_use_poffin_zoroark
        from core.supporter_router_zoroark import choose_best_supporter_zoroark, score_supporter_option_zoroark
        from core.trade_planner import score_trade_option
        from core.transformation_tome_planner import score_transformation_tome_option
        from core.zoroark_planner import score_zoroark_evolve_option, zoroark_end_turn_penalty
    except Exception:
        return adjusted

    try:
        poffin_decision = should_use_poffin_zoroark(state, state.options)
    except Exception:
        poffin_decision = None
    try:
        supporter_decision = choose_best_supporter_zoroark(state, state.options)
    except Exception:
        supporter_decision = None

    for idx, option in enumerate(getattr(state, "options", []) or []):
        bonus = 0.0
        try:
            typ = option_type(option)
            if typ == OPT_PLAY:
                bonus += score_setup_basic_play_zoroark(state, option)
                bonus += score_search_option_zoroark(state, option)
                bonus += score_supporter_option_zoroark(state, option)
                bonus += score_recovery_option_zoroark(state, option)
                bonus += score_poison_mochi_option(state, option)
                bonus += score_transformation_tome_option(state, option)
                if poffin_decision and poffin_decision.should_act and poffin_decision.option_index == idx:
                    bonus += poffin_decision.score + 1600.0
                if supporter_decision and supporter_decision.should_use and supporter_decision.option_index == idx:
                    bonus += supporter_decision.score + 1200.0
            elif typ == OPT_EVOLVE:
                bonus += score_zoroark_evolve_option(state, option)
            elif typ == OPT_ATTACH:
                bonus += score_energy_option_zoroark(state, option)
            elif typ == OPT_ABILITY:
                bonus += score_trade_option(state, option)
                bonus += score_pecharunt_option(state, option)
            elif typ == OPT_ATTACK:
                bonus += score_night_joker_option(state, option, idx)
                if supporter_decision and supporter_decision.should_use and adjusted[idx] < KO_ATTACK_SCORE:
                    bonus -= min(6000.0, max(1600.0, supporter_decision.score))
            elif typ == OPT_END:
                bonus += zoroark_end_turn_penalty(state, adjusted)
                if poffin_decision and poffin_decision.should_act:
                    bonus -= 4500.0
                if supporter_decision and supporter_decision.should_use:
                    bonus -= min(6500.0, max(2200.0, supporter_decision.score))
        except Exception:
            bonus = 0.0
        adjusted[idx] += bonus
    return adjusted


def apply_card_analysis_priority_engine(state: Any, scores: Sequence[float]) -> List[float]:
    return list(scores)


def apply_general_priority_engine(state: Any, scores: Sequence[float]) -> List[float]:
    adjusted = list(scores)
    if not adjusted:
        return adjusted
    non_end_best = max(
        (score for idx, score in enumerate(adjusted) if idx < len(state.options) and option_type(state.options[idx]) != OPT_END),
        default=-math.inf,
    )
    for idx, option in enumerate(state.options):
        if option_type(option) != OPT_END:
            continue
        if non_end_best > 60.0:
            adjusted[idx] -= 1000.0 + max(0.0, non_end_best)
        else:
            adjusted[idx] += 100.0
    return adjusted


def debug_scores(obs_dict: dict) -> Tuple[List[int], List[Tuple[int, float, str]]]:
    state = normalize_state(obs_dict)
    scores = score_options(state)
    choice = sanitize_choice(state, choose_by_scores(state, scores), scores)
    rows = [(idx, scores[idx], option_label(state, option, idx)) for idx, option in enumerate(state.options)]
    return choice, rows


def choose_by_scores(state: Any, scores: Sequence[float]) -> List[int]:
    options = state.options
    if not options:
        return []

    best_attack = None
    for idx, option in enumerate(options):
        if option_type(option) == OPT_ATTACK and scores[idx] >= KO_ATTACK_SCORE:
            if best_attack is None or scores[idx] > scores[best_attack]:
                best_attack = idx
    if best_attack is not None and state.max_count >= 1:
        return [best_attack]

    order = sorted(range(len(options)), key=lambda idx: (scores[idx], -idx), reverse=True)
    order = diversify_setup_multiselect_order(state, order)
    min_count = min(state.min_count, len(options))
    max_count = min(state.max_count, len(options))
    max_count = apply_effect_selection_limit(state, min_count, max_count)
    if max_count <= 0:
        return []

    if min_count == 0:
        positive = [idx for idx in order if scores[idx] > optional_threshold(state)]
        return positive[:max_count]
    return order[:min_count]


def diversify_setup_multiselect_order(state: Any, order: Sequence[int]) -> List[int]:
    if state.max_count <= 1:
        return list(order)
    try:
        from core.priority_tables import canonical_name_from_id, context_source_name

        source = context_source_name(state)
        if source != "Buddy-Buddy Poffin":
            return list(order)
        unique_setup: List[int] = []
        seen_names = set()
        setup_names = {"N's Zorua"}
        for idx in order:
            name = canonical_name_from_id(card_id_from_option(state, state.options[idx]))
            if name in setup_names and name not in seen_names:
                unique_setup.append(idx)
                seen_names.add(name)
        return unique_setup + [idx for idx in order if idx not in set(unique_setup)]
    except Exception:
        return list(order)


def sanitize_choice(state: Any, choice: Iterable[Any], scores: Optional[Sequence[float]] = None) -> List[int]:
    option_count = len(state.options)
    if option_count == 0:
        return []
    min_count = min(state.min_count, option_count)
    max_count = min(max(state.max_count, min_count), option_count)
    max_count = apply_effect_selection_limit(state, min_count, max_count)

    clean: List[int] = []
    seen = set()
    for raw in choice or []:
        try:
            idx = int(raw)
        except (TypeError, ValueError):
            continue
        if 0 <= idx < option_count and idx not in seen:
            clean.append(idx)
            seen.add(idx)
        if len(clean) >= max_count:
            break

    if len(clean) < min_count:
        if scores is None:
            fill_order = list(range(option_count))
        else:
            fill_order = sorted(range(option_count), key=lambda idx: (scores[idx], -idx), reverse=True)
        for idx in fill_order:
            if idx not in seen:
                clean.append(idx)
                seen.add(idx)
            if len(clean) >= min_count:
                break

    if len(clean) > max_count:
        clean = clean[:max_count]
    return clean


def apply_effect_selection_limit(state: Any, min_count: int, max_count: int) -> int:
    try:
        from core.priority_tables import context_source_name

        if context_source_name(state) == "Buddy-Buddy Poffin":
            return min(max_count, max(min_count, 2))
    except Exception:
        pass
    return max_count


def emergency_fallback(obs_dict: Any) -> List[int]:
    select = getv(obs_dict, "select")
    options = getv(select, "option", []) or []
    if not isinstance(options, list) or not options:
        return []
    min_count = max(0, int_or(getv(select, "minCount", 0), 0))
    max_count = min(len(options), max(min_count, int_or(getv(select, "maxCount", min_count), min_count)))
    if min_count == 0:
        return []
    for idx, option in enumerate(options):
        if option_type(option) == OPT_END and min_count <= 1 <= max_count:
            return [idx]
    return list(range(min(min_count, len(options))))


def optional_threshold(state: Any) -> float:
    if state.context in (CTX_SETUP_BENCH, CTX_TO_HAND, CTX_TO_FIELD, CTX_TO_BENCH):
        return 10.0
    if state.context in (CTX_DISCARD, CTX_DISCARD_CARD_OR_ATTACHED_CARD, CTX_DISCARD_ENERGY, CTX_DISCARD_ENERGY_CARD):
        return -9999.0
    return 25.0


def score_option(state: Any, option: Any, option_index: int = 0, all_options: Optional[Sequence[Any]] = None) -> float:
    return _score_option_inner(state, option, option_index, all_options or state.options, allow_end_check=True)


def _score_option_inner(
    state: Any,
    option: Any,
    option_index: int,
    all_options: Sequence[Any],
    allow_end_check: bool,
) -> float:
    typ = option_type(option)
    context = state.context

    if typ == OPT_END:
        base = score_end(state, all_options) if allow_end_check else -5.0
        return apply_action_reasoning(state, option, option_index, base)
    if typ == OPT_ATTACK:
        base = score_attack(state, option, option_index, all_options)
        return apply_action_reasoning(state, option, option_index, base)
    if typ == OPT_ATTACH:
        base = score_attach(state, option)
        return apply_action_reasoning(state, option, option_index, base)
    if typ == OPT_PLAY:
        base = score_play(state, option)
        return apply_action_reasoning(state, option, option_index, base)
    if typ == OPT_EVOLVE:
        base = score_evolve(state, option)
        return apply_action_reasoning(state, option, option_index, base)
    if typ == OPT_ABILITY:
        base = score_ability(state, option)
        return apply_action_reasoning(state, option, option_index, base)
    if typ == OPT_RETREAT:
        base = score_retreat(state)
        return apply_action_reasoning(state, option, option_index, base)
    if typ == OPT_DISCARD:
        cid = card_id_from_option(state, option)
        base = score_discard_card(state, cid, source="main")
        return apply_action_reasoning(state, option, option_index, base)
    if typ in (OPT_CARD, OPT_TOOL_CARD, OPT_ENERGY_CARD, OPT_ENERGY):
        base = score_card_selection(state, option, context)
        return apply_action_reasoning(state, option, option_index, base)
    if typ == OPT_NUMBER:
        base = score_number(state, option, context)
        return apply_action_reasoning(state, option, option_index, base)
    if typ in (OPT_YES, OPT_NO):
        base = score_yes_no(state, option, context)
        return apply_action_reasoning(state, option, option_index, base)
    if typ == OPT_SKILL:
        base = score_skill_order(state, option)
        return apply_action_reasoning(state, option, option_index, base)
    return apply_action_reasoning(state, option, option_index, 0.0)


def apply_action_reasoning(state: Any, option: Any, option_index: int, base_score: float) -> float:
    try:
        intent = classify_option(state, option, option_index)
        rules = turn_rules(state)
    except Exception:
        return base_score

    score = base_score
    cls = intent.action_class

    if cls == ActionClass.PLAY_SUPPORTER:
        if rules.supporter_played:
            score -= 50000.0
        if rules.is_first_player_first_turn:
            score -= 50000.0
    elif cls == ActionClass.PLAY_STADIUM:
        if rules.stadium_played:
            score -= 50000.0
        if same_name_stadium_in_play(state, intent.card_name):
            score -= 50000.0
    elif cls == ActionClass.ATTACH_ENERGY:
        if rules.energy_attached:
            score -= 50000.0
    elif cls == ActionClass.RETREAT:
        if rules.retreated:
            score -= 50000.0
    elif cls == ActionClass.EVOLVE:
        target = get_pokemon_by_area(state, getv(option, "inPlayArea"), getv(option, "inPlayIndex"), state.your_index)
        if target is not None and bool(getv(target, "appearThisTurn", False)):
            score -= 50000.0
    elif cls == ActionClass.BENCH_BASIC:
        if rules.bench_space <= 0:
            score -= 1000.0
    elif cls == ActionClass.ATTACK:
        if rules.is_first_player_first_turn:
            score -= 50000.0
    elif cls in (ActionClass.SETUP_ACTIVE, ActionClass.PROMOTE_ACTIVE):
        if intent.is_mandatory:
            score += 500.0
    elif cls == ActionClass.END_TURN:
        if not rules.has_active and intent.is_mandatory:
            score -= 1000.0

    if cls == ActionClass.DISCARD_COST and intent.card_id in list_value("protected_cards"):
        score -= 100.0
    if cls == ActionClass.SEARCH_TAKE_CARD and intent.card_id in list_value("setup_priority"):
        score += 40.0
    try:
        from study_rule_runtime import apply_study_rules

        score = apply_study_rules(state, option, option_index, score)
    except Exception:
        pass
    return score


def score_end(state: Any, all_options: Sequence[Any]) -> float:
    if len(all_options) <= 1:
        return 0.0
    best_non_end = -math.inf
    for idx, option in enumerate(all_options):
        if option_type(option) == OPT_END:
            continue
        score = _score_option_inner(state, option, idx, all_options, allow_end_check=False)
        best_non_end = max(best_non_end, score)
    action_count = int_or(getv(state.current, "turnActionCount", 0), 0)
    if best_non_end > 40 and action_count < 80:
        return -200.0 - best_non_end
    if best_non_end > 5 and action_count < 30:
        return -50.0
    return 5.0


def score_attack(state: Any, option: Any, option_index: int, all_options: Sequence[Any]) -> float:
    db = get_db()
    active = active_pokemon(state)
    opponent = active_pokemon(state, state.opponent_index)
    active_id = card_id(active)
    opponent_id = card_id(opponent)
    if use_ns_zoroark_strategy(state):
        try:
            from core.target_board import ZOROARK_EX, pokemon_name

            if pokemon_name(active) != ZOROARK_EX:
                return -9500.0
        except Exception:
            if active_id != 293:
                return -9500.0
    attack = db.get_attack(getv(option, "attackId"))
    if attack is None:
        attack = attack_by_option_order(state, option_index, all_options)

    if active is None or attack is None:
        return 25.0
    damage = estimate_attack_damage(state, attack, active, opponent)
    score = 100.0 + damage * 2.0
    if opponent is not None and pokemon_hp(opponent) > 0:
        hp = pokemon_hp(opponent)
        prize_value = prize_value_for_card(opponent_id)
        if damage >= hp:
            score += KO_ATTACK_SCORE + prize_value * 1000.0
            if prize_count(state) <= prize_value:
                score += WINNING_ATTACK_SCORE
        else:
            remaining = hp - damage
            if remaining <= 60:
                score += 450.0
            elif damage >= hp * 0.65:
                score += 220.0

    active_info = db.get_card(active_id)
    if active_id in list_value("primary_attackers"):
        score += 90.0
    elif active_id in list_value("secondary_attackers"):
        score += 55.0
    if active_info and active_info.ex:
        score += 10.0

    text = (attack.text or "").lower()
    opponent_hp = pokemon_hp(opponent) if opponent else 9999
    score += score_opponent_deck_discard_pressure(state, attack, damage, opponent_hp)
    if "discard" in text and damage < opponent_hp:
        score -= 30.0
    if "can't attack" in text or "cannot attack" in text:
        score -= 40.0
    if player_has_condition(state, "confused"):
        score -= 15.0
    return score


def score_opponent_deck_discard_pressure(state: Any, attack: AttackInfo, damage: int, opponent_hp: int) -> float:
    discard_count = opponent_deck_discard_count(attack)
    if discard_count <= 0:
        return 0.0
    if damage >= opponent_hp:
        return 0.0
    opponent_deck = deck_count(state, state.opponent_index)
    if opponent_deck > OPPONENT_DECK_PRESSURE_THRESHOLD:
        return -850.0 if damage > 0 else -3600.0

    projected_deck = max(0, opponent_deck - discard_count)
    score = 450.0 + discard_count * 275.0 + max(0, OPPONENT_DECK_PRESSURE_THRESHOLD - opponent_deck) * 120.0
    if projected_deck <= 0:
        score += WINNING_ATTACK_SCORE
    return score


def opponent_deck_discard_count(attack: AttackInfo) -> int:
    text = f"{attack.name or ''} {attack.text or ''}".lower()
    if "opponent" not in text or "deck" not in text or "discard" not in text:
        return 0
    for count in range(10, 1, -1):
        if f"top {count}" in text:
            return count
    if "top card" in text:
        return 1
    return 1


def score_attach(state: Any, option: Any) -> float:
    db = get_db()
    cid = card_id_from_option(state, option)
    target = attach_target_from_option(state, option)
    target_id = card_id(target)
    if cid is None or target is None:
        return 10.0

    card = db.get_card(cid)
    if card and "Energy" in card.card_type and use_ns_zoroark_strategy(state):
        try:
            from core.energy_planner_zoroark import score_energy_attachment_zoroark

            return score_energy_attachment_zoroark(state, cid, target).score
        except Exception:
            pass
    if target_id in list_value("support_pokemon"):
        return -1400.0
    if card and "Energy" in card.card_type:
        before = pokemon_energy_count(target)
        after = before + 1
        needed = min_attack_cost(target_id)
        score = 60.0
        if target_id in list_value("energy_attachment_priorities"):
            score += 60.0 + card_priority(target_id, "energy_attachment_priorities") * 12.0
        if target is active_pokemon(state):
            score += 45.0
        if before < needed <= after:
            score += 170.0
        elif after <= needed:
            score += 55.0
        if target_id in list_value("primary_attackers"):
            score += 65.0
        elif target_id in list_value("secondary_attackers"):
            score += 35.0
        if pokemon_hp(target) and pokemon_hp(target) <= 40 and target is not active_pokemon(state):
            score -= 30.0
        return score

    score = 20.0
    if cid in (1158, 1174):
        score += 85.0
        if target_id in list_value("primary_attackers"):
            score += 60.0
        if target is active_pokemon(state):
            score += 30.0
    if card and card.card_type == "Tool":
        score += 35.0
    return score


def score_play(state: Any, option: Any) -> float:
    db = get_db()
    cid = card_id_from_option(state, option)
    card = db.get_card(cid)
    if cid is None or card is None:
        return 15.0

    score = 25.0
    text = card_text(card)
    lower = text.lower()
    if cid in list_value("draw_search_cards"):
        score += 80.0
    if cid in list_value("setup_priority"):
        score += 55.0 + card_priority(cid, "setup_priority") * 10.0
    if cid in list_value("must_use_before_attack"):
        score += 35.0
    if any(keyword.lower() in lower for keyword in load_profile().get("draw_keywords", [])):
        score += 70.0
    if any(keyword.lower() in lower for keyword in load_profile().get("search_keywords", [])):
        score += 75.0
    if any(keyword.lower() in lower for keyword in load_profile().get("energy_acceleration_keywords", [])):
        score += 70.0
    if card.card_type == "Supporter":
        score += 30.0
        if int_or(getv(state.current, "supporterPlayed", 0), 0):
            score -= 100.0
    elif card.card_type == "Item":
        score += 35.0
    elif card.card_type == "Stadium":
        score += 20.0
    elif card.card_type == "Tool":
        score += 35.0
    elif card.card_type == "Pokemon":
        score += score_setup_card(state, cid, active_target=False) - 20.0

    if "draw" in lower and hand_count_after_play(state) <= 4:
        score += 45.0
    if is_gust_text(lower):
        score += 60.0
        if gust_creates_ko(state):
            score += KO_ATTACK_SCORE + 850.0
    if is_disruption_text(lower):
        opp_hand = hand_count(state, state.opponent_index)
        own_prizes = prize_count(state)
        score += min(opp_hand, 10) * 8.0
        if own_prizes <= 3:
            score += 75.0
    if "search your deck" in lower and deck_count(state) <= 0:
        score -= 60.0
    if cid in list_value("avoid_benching"):
        score -= 200.0
    return score


def score_evolve(state: Any, option: Any) -> float:
    db = get_db()
    cid = card_id_from_option(state, option)
    evolved = db.get_card(cid)
    target = attach_target_from_option(state, option)
    if target is None:
        target = get_pokemon_by_area(state, getv(option, "inPlayArea"), getv(option, "inPlayIndex"), state.your_index)
    if evolved is None:
        return 40.0

    score = 80.0
    if cid in list_value("evolution_priorities"):
        score += 160.0 + card_priority(cid, "evolution_priorities") * 20.0
    if cid in list_value("primary_attackers"):
        score += 120.0
    if evolved.ex:
        score += 25.0
    if target is not None:
        score += max(0, evolved.hp - pokemon_max_hp(target)) / 3.0
        if pokemon_energy_count(target) >= min_attack_cost(cid):
            score += 60.0
    return score


def score_ability(state: Any, option: Any) -> float:
    db = get_db()
    cid = card_id_from_option(state, option)
    card = db.get_card(cid)
    text = card_text(card) if card else ""
    lower = text.lower()
    score = 40.0
    if "draw" in lower:
        score += 80.0
    if "search" in lower:
        score += 75.0
    if "attach" in lower and "energy" in lower:
        score += 70.0
    if "discard" in lower:
        score -= 20.0
    if cid in list_value("primary_attackers"):
        score += 20.0
    return score


def score_retreat(state: Any) -> float:
    active = active_pokemon(state)
    if active is None:
        return -20.0
    score = 15.0
    active_info = get_db().get_card(card_id(active))
    retreat_cost = active_info.retreat_cost if active_info else 0
    score -= retreat_cost * 20.0
    if retreat_cost >= pokemon_energy_count(active) and can_pokemon_attack_now(card_id(active), pokemon_energy_count(active)):
        score -= 35.0
    if player_has_condition(state, "asleep") or player_has_condition(state, "paralyzed"):
        score += 120.0
    if not can_pokemon_attack_now(card_id(active), pokemon_energy_count(active)):
        score += 55.0
    if pokemon_hp(active) and pokemon_hp(active) <= max(40, pokemon_max_hp(active) * 0.25):
        score += 45.0
    for _, _, pokemon in iter_in_play(state):
        if pokemon is active:
            continue
        if can_pokemon_attack_now(card_id(pokemon), pokemon_energy_count(pokemon)):
            score += 45.0
            if can_pokemon_take_ko(state, pokemon):
                score += 220.0
    if int_or(getv(state.current, "retreated", 0), 0):
        score -= 200.0
    return score


def score_card_selection(state: Any, option: Any, context: int) -> float:
    cid = card_id_from_option(state, option)
    if cid is None and option_type(option) in (OPT_TOOL_CARD, OPT_ENERGY_CARD, OPT_ENERGY):
        cid = attached_card_id_from_option(state, option)

    if context == CTX_TO_PRIZE or enum_int(getv(option, "area", -1), -1) == AREA_PRIZE:
        return score_prize_selection(state, option, cid)
    if use_ns_zoroark_strategy(state):
        try:
            from core.copy_target_planner import score_copy_selection_zoroark
            from core.pecharunt_planner import score_pecharunt_switch_target
            from core.poison_mochi_planner import score_mochi_target_zoroark
            from core.recovery_planner_zoroark import score_recovery_selection_zoroark
            from core.search_planner_zoroark import (
                is_discard_context,
                is_search_context,
                score_discard_selection_zoroark,
                score_search_selection_zoroark,
            )
            from core.transformation_tome_planner import score_transformation_tome_selection_zoroark
            from core.zoroark_planner import score_zoroark_selection
            from core.priority_tables import canonical_name_from_id, context_source_name

            source = context_source_name(state)
            name = canonical_name_from_id(cid)
            if is_discard_context(context):
                return score_discard_selection_zoroark(state, cid)
            if source == "Night Joker":
                return score_copy_selection_zoroark(state, cid)
            if source == "Transformation Tome":
                return score_transformation_tome_selection_zoroark(state, cid)
            if source in {"Night Stretcher", "Sacred Ash"}:
                return score_recovery_selection_zoroark(state, cid)
            if context in (CTX_SWITCH, CTX_TO_ACTIVE):
                pokemon = pokemon_from_card_option(state, option)
                return max(score_pecharunt_switch_target(state, pokemon), score_zoroark_selection(state, option, context))
            if context in (CTX_ATTACH_FROM, CTX_ATTACH_TO):
                return score_zoroark_selection(state, option, context)
            if name == "Binding Mochi":
                pokemon = pokemon_from_card_option(state, option)
                if pokemon is not None:
                    return score_mochi_target_zoroark(state, pokemon)
            if is_search_context(context) or context in (CTX_EVOLVES_FROM, CTX_EVOLVES_TO, CTX_EVOLVE):
                return score_search_selection_zoroark(state, option, name, cid)
        except Exception:
            pass
    if context in (CTX_DISCARD, CTX_DISCARD_CARD_OR_ATTACHED_CARD, CTX_DISCARD_ENERGY_CARD, CTX_DISCARD_TOOL_CARD, CTX_DISCARD_ENERGY):
        return score_discard_card(state, cid, source="selection")
    if context in (CTX_SETUP_ACTIVE,):
        return score_setup_card(state, cid, active_target=True)
    if context in (CTX_SETUP_BENCH, CTX_TO_BENCH, CTX_TO_FIELD):
        return score_setup_card(state, cid, active_target=False)
    if context in (CTX_TO_HAND, CTX_LOOK):
        return score_search_card(state, cid)
    if context in (CTX_SWITCH, CTX_TO_ACTIVE):
        pokemon = pokemon_from_card_option(state, option)
        if context == CTX_TO_ACTIVE:
            return score_promote_after_ko(state, pokemon)
        return score_switch_target(state, pokemon)
    if context in (CTX_DAMAGE_COUNTER, CTX_DAMAGE_COUNTER_ANY, CTX_DAMAGE, CTX_EFFECT_TARGET):
        pokemon = pokemon_from_card_option(state, option)
        return score_damage_target(state, pokemon, int_or(getv(option, "playerIndex", state.opponent_index), state.opponent_index))
    if context in (CTX_HEAL, CTX_REMOVE_DAMAGE_COUNTER):
        pokemon = pokemon_from_card_option(state, option)
        return score_heal_target(state, pokemon)
    if context in (CTX_ATTACH_FROM, CTX_ATTACH_TO):
        pokemon = pokemon_from_card_option(state, option)
        return score_attach_target_only(state, pokemon)
    if context in (CTX_EVOLVES_FROM, CTX_EVOLVES_TO, CTX_EVOLVE):
        return score_search_card(state, cid) + 25.0
    if context in (CTX_TO_DECK, CTX_TO_DECK_BOTTOM, CTX_NOT_MOVE):
        return score_discard_card(state, cid, source="to_deck") * 0.25
    return score_search_card(state, cid)


def score_prize_selection(state: Any, option: Any, cid: Optional[int]) -> float:
    # Prize list order in cabt docs is bottom-to-top, so a hidden prize tie
    # deterministically prefers the highest index ("top" prize) without
    # pretending to know face-down contents.
    option_index = int_or(getv(option, "index", 0), 0)
    if cid is None:
        return 100.0 + option_index

    score = 1000.0 + option_index
    if prize_count(state) <= max(1, state.max_count):
        score += 5000.0
    if cid in list_value("primary_attackers"):
        score += 1500.0
    if cid in list_value("evolution_priorities"):
        score += 1100.0
    if cid in list_value("setup_pokemon"):
        score += 900.0
    if cid in list_value("energy_ids"):
        score += 700.0
    if cid in list_value("draw_search_cards"):
        score += 550.0
    if cid in list_value("secondary_attackers"):
        score += 450.0
    return score


def score_promote_after_ko(state: Any, pokemon: Any) -> float:
    if pokemon is None:
        return 0.0
    pid = card_id(pokemon)
    card = get_db().get_card(pid)
    energy_count = pokemon_energy_count(pokemon)
    can_attack = can_pokemon_attack_now(pid, energy_count)
    score = 100.0
    if can_attack:
        score += 1200.0
        if can_pokemon_take_ko(state, pokemon):
            score += 900.0
    if card and card.retreat_cost == 0:
        score += 650.0
    elif card:
        score -= card.retreat_cost * 60.0

    if pid in list_value("primary_attackers"):
        score += 450.0 if can_attack else -100.0
    elif pid in list_value("secondary_attackers"):
        score += 350.0 if can_attack else 50.0
    if pid in list_value("setup_pokemon") and not can_attack:
        score -= 450.0
    if pid in list_value("support_pokemon"):
        score -= 350.0
    if card and card.prize_value == 1 and pid not in list_value("protected_cards"):
        score += 180.0
    if use_ns_zoroark_strategy(state):
        try:
            from core.target_board import ZOROARK_EX, ZORUA, pokemon_name

            name = pokemon_name(pokemon)
            if name == ZOROARK_EX and energy_count >= 2:
                score += 2800.0
            elif name == ZORUA:
                ready_bench = any(can_pokemon_attack_now(card_id(p), pokemon_energy_count(p)) for p in bench_pokemon(state))
                score += 400.0 if not ready_bench else -500.0
            elif name == "Budew":
                score += 600.0
            elif name in {"Pecharunt ex", "Fezandipiti ex"}:
                score -= 600.0
        except Exception:
            pass
    if pokemon_hp(pokemon) <= max(30, pokemon_max_hp(pokemon) * 0.25):
        score -= 120.0
    return score


def has_card_name_in_hand(state: Any, wanted_name: str) -> bool:
    try:
        from core.priority_tables import canonical_name_from_id

        return any(canonical_name_from_id(card_id(card)) == wanted_name for card in hand_cards(state))
    except Exception:
        return False


def score_number(state: Any, option: Any, context: int) -> float:
    number = option_number(option)
    if context in (CTX_DRAW_COUNT, CTX_REMOVE_DAMAGE_COUNTER_COUNT):
        return float(number)
    if context == CTX_DAMAGE_COUNTER_COUNT:
        opponent = active_pokemon(state, state.opponent_index)
        if opponent is not None:
            needed = math.ceil(max(0, pokemon_hp(opponent)) / 10.0)
            return 100.0 - abs(number - needed) * 3.0
        return float(number)
    if context in (CTX_DISCARD, CTX_DISCARD_ENERGY):
        return -float(number)
    return float(number)


def score_yes_no(state: Any, option: Any, context: int) -> float:
    typ = option_type(option)
    yes = typ == OPT_YES
    if context == CTX_IS_FIRST:
        preferred = str(load_profile().get("preferred_going", "second")).lower()
        return 100.0 if (yes and preferred == "first") or ((not yes) and preferred != "first") else 0.0
    if context == CTX_MULLIGAN:
        return 100.0 if yes else 0.0
    if context == CTX_COIN_HEAD:
        return 10.0 if yes else 0.0
    if context in (CTX_ACTIVATE, CTX_FIRST_EFFECT, CTX_MORE_DEVOLVE):
        effect_card = getv(state.select, "effect") or getv(state.select, "contextCard")
        cid = card_id(effect_card)
        text = card_text(get_db().get_card(cid)).lower() if cid is not None else ""
        beneficial = any(word in text for word in ("draw", "search", "attach", "heal", "switch"))
        harmful = any(word in text for word in ("discard", "damage to this", "knocked out"))
        if beneficial and not harmful:
            return 100.0 if yes else 0.0
        if harmful and not beneficial:
            return 100.0 if not yes else 0.0
        return 40.0 if yes else 10.0
    return 10.0 if yes else 0.0


def score_skill_order(state: Any, option: Any) -> float:
    cid = int_or(getv(option, "cardId"), 0)
    card = get_db().get_card(cid)
    text = card_text(card).lower() if card else ""
    score = 10.0
    if "draw" in text or "search" in text:
        score += 50.0
    if "attach" in text and "energy" in text:
        score += 45.0
    return score


def score_search_card(state: Any, cid: Optional[int]) -> float:
    db = get_db()
    if cid is None:
        return 0.0
    card = db.get_card(cid)
    score = 10.0
    if cid in list_value("primary_attackers"):
        score += 170.0
        if not has_card_in_play(state, cid):
            score += 60.0
        if missing_stage2_payoff(state):
            score += 500.0
    if cid in list_value("secondary_attackers"):
        score += 95.0
    if cid in list_value("setup_pokemon"):
        score += 115.0
        if cid == 227 and count_in_play_id(state, 227) < 2:
            score += 650.0
        elif not has_any_in_play(state, list_value("setup_pokemon")):
            score += 120.0
    if cid in list_value("energy_ids"):
        score += 75.0
        if not any(card_id(c) in list_value("energy_ids") for c in hand_cards(state)):
            score += 35.0
        if active_needs_one_energy(state):
            score += 420.0
    if cid in list_value("draw_search_cards"):
        score += 85.0
    if cid in list_value("setup_priority"):
        score += 70.0 + card_priority(cid, "setup_priority") * 12.0
    if cid in list_value("evolution_priorities"):
        score += 45.0 + card_priority(cid, "evolution_priorities") * 8.0
    if cid in list_value("protected_cards"):
        score += 25.0
    if card:
        if card.card_type == "Supporter":
            score += 25.0
        elif card.card_type == "Item":
            score += 20.0
        elif card.card_type == "Pokemon" and card.basic:
            score += 25.0
            if low_setup_board(state):
                score += 45.0 if not card.ex else -35.0
        elif card.card_type == "Pokemon" and (card.stage1 or card.stage2):
            score += 35.0
    return score


def low_setup_board(state: Any) -> bool:
    in_play_count = sum(1 for _area, _index, _pokemon in iter_in_play(state))
    return in_play_count <= 2 and bench_space(state) > 0


def score_setup_card(state: Any, cid: Optional[int], active_target: bool) -> float:
    db = get_db()
    card = db.get_card(cid)
    if cid is None or card is None or card.card_type != "Pokemon":
        return -100.0
    if not active_target and bench_space(state) <= 0:
        return -150.0

    score = 30.0 + card.hp / 10.0
    if cid in list_value("avoid_benching"):
        score -= 250.0
    if cid in list_value("setup_pokemon"):
        score += 100.0 if not active_target else 60.0
    if cid in list_value("secondary_attackers"):
        score += 95.0 if active_target else 70.0
    if cid in list_value("primary_attackers"):
        score += 120.0
    if cid in list_value("bench_only_if_useful") and duplicate_in_play_count(state, cid) >= 2:
        score -= 50.0
    if card.ex and not active_target:
        score -= 20.0
    if active_target and use_ns_zoroark_strategy(state):
        try:
            from core.priority_tables import canonical_name_from_id

            name = canonical_name_from_id(cid)
            if name == "N's Zorua":
                score += 520.0
            elif name in {"N's Zekrom", "N's Darumaka"}:
                score -= 180.0
            elif name in {"Pecharunt ex", "Fezandipiti ex"}:
                score -= 420.0
            elif name == "Budew":
                score += 90.0
        except Exception:
            pass
    return score


def score_switch_target(state: Any, pokemon: Any) -> float:
    if pokemon is None:
        return 0.0
    pid = card_id(pokemon)
    score = 25.0 + pokemon_hp(pokemon) / 10.0
    if pid in list_value("retreat_switch_priorities"):
        score += 80.0 + card_priority(pid, "retreat_switch_priorities") * 15.0
    if can_pokemon_attack_now(pid, pokemon_energy_count(pokemon)):
        score += 90.0
    if can_pokemon_take_ko(state, pokemon):
        score += 300.0
    if pokemon_hp(pokemon) and pokemon_hp(pokemon) <= 30:
        score -= 60.0
    return score


def score_attach_target_only(state: Any, pokemon: Any) -> float:
    if pokemon is None:
        return 0.0
    pid = card_id(pokemon)
    attached = pokemon_energy_count(pokemon)
    needed = min_attack_cost(pid)
    if needed <= 0:
        needed = 1

    score = 20.0
    if pid in list_value("energy_attachment_priorities"):
        score += 80.0 + card_priority(pid, "energy_attachment_priorities") * 12.0
    if pokemon is active_pokemon(state):
        score += 25.0
    if attached <= 0:
        score += 650.0
    elif attached < needed:
        score += 350.0
    else:
        score -= 700.0 + attached * 120.0
    card = get_db().get_card(pid)
    if card and card.card_type == "Pokemon":
        if card.ex:
            score += 120.0
        if card.basic and attached <= 0:
            score += 80.0
    return score


def score_damage_target(state: Any, pokemon: Any, player_index: int) -> float:
    if pokemon is None:
        return 0.0
    pid = card_id(pokemon)
    score = 10.0
    if player_index == state.opponent_index:
        hp = pokemon_hp(pokemon)
        score += max(0, 220 - hp)
        score += prize_value_for_card(pid) * 35.0
        if hp <= 60:
            score += 100.0
    else:
        score -= 200.0
    return score


def score_heal_target(state: Any, pokemon: Any) -> float:
    if pokemon is None:
        return 0.0
    pid = card_id(pokemon)
    score = pokemon_damage(pokemon) * 2.0
    if pid in list_value("primary_attackers"):
        score += 60.0
    if pid in list_value("secondary_attackers"):
        score += 35.0
    return score


def score_discard_card(state: Any, cid: Optional[int], source: str = "selection") -> float:
    db = get_db()
    if cid is None:
        return 0.0
    card = db.get_card(cid)
    score = 10.0
    if cid in list_value("discard_freely"):
        score += 150.0
    if card and "Energy" in card.card_type:
        score += 70.0
    if cid in list_value("protected_cards"):
        score -= 220.0
    if is_only_critical_copy_available(state, cid):
        score -= 5000.0
    if cid in list_value("conditionally_protected_cards"):
        score -= 70.0
    if cid in list_value("protected_energy_ids"):
        score -= 120.0
    if cid in list_value("primary_attackers"):
        score -= 180.0
    if cid in list_value("secondary_attackers"):
        score -= 130.0
    if cid in list_value("draw_search_cards"):
        score -= 45.0
    if duplicate_in_hand_count(state, cid) >= 2:
        score += 125.0
    if card and card.card_type == "Basic Energy":
        score += 20.0
    if source == "to_deck" and cid in list_value("protected_cards"):
        score += 80.0
    return score


def estimate_attack_damage(state: Any, attack: AttackInfo, active: Any, opponent: Any) -> int:
    damage = int(attack.damage or 0)
    text = (attack.text or "").lower()
    damage_text = (attack.damage_text or "").lower()

    if "basic" in text and "energy" in text and "discard pile" in text and ("for each" in text or "each basic" in text):
        energy_count = sum(count_card_in_discard(state, eid) for eid in list_value("energy_ids"))
        damage = damage * energy_count
    elif "discard the top 6" in text and "basic" in text and "energy" in text:
        damage = int(damage * expected_energy_in_top_cards(state, 6))
    elif "x" in damage_text or "×" in damage_text:
        damage = max(damage, damage)

    active_info = get_db().get_card(card_id(active))
    opponent_info = get_db().get_card(card_id(opponent))
    if active_info and opponent_info:
        if energy_matches(active_info.energy_type, opponent_info.weakness):
            damage *= 2
        if damage > 0 and energy_matches(active_info.energy_type, opponent_info.resistance):
            damage = max(0, damage - 30)
    if opponent_info and opponent_info.ex and 1158 in attached_card_ids(active, "tools"):
        damage += 50
    return int(max(0, damage))


def expected_energy_in_top_cards(state: Any, count: int) -> float:
    deck = load_deck_ids()
    energy_ids = set(list_value("energy_ids"))
    total_energy = sum(1 for cid in deck if cid in energy_ids)
    seen_energy = sum(count_seen_card(state, eid) for eid in energy_ids)
    remaining_energy = max(0, total_energy - seen_energy)
    remaining_deck = max(1, deck_count(state))
    return min(float(count), float(count) * remaining_energy / remaining_deck)


def attack_by_option_order(state: Any, option_index: int, all_options: Sequence[Any]) -> Optional[AttackInfo]:
    active = active_pokemon(state)
    active_info = get_db().get_card(card_id(active))
    if not active_info or not active_info.attacks:
        return None
    attack_indices = [idx for idx, option in enumerate(all_options) if option_type(option) == OPT_ATTACK]
    try:
        position = attack_indices.index(option_index)
    except ValueError:
        position = 0
    if 0 <= position < len(active_info.attacks):
        return active_info.attacks[position]
    return active_info.attacks[0]


def min_attack_cost(card_id_value: Optional[int]) -> int:
    card = get_db().get_card(card_id_value)
    if not card or not card.attacks:
        return 99
    costs = [len(attack.cost) for attack in card.attacks if attack.cost is not None]
    return min(costs) if costs else 0


def can_pokemon_attack_now(card_id_value: Optional[int], energy_count: int) -> bool:
    card = get_db().get_card(card_id_value)
    if not card or not card.attacks:
        return False
    return any(energy_count >= len(attack.cost) for attack in card.attacks)


def can_pokemon_take_ko(state: Any, pokemon: Any) -> bool:
    opponent = active_pokemon(state, state.opponent_index)
    if opponent is None:
        return False
    card = get_db().get_card(card_id(pokemon))
    if not card:
        return False
    for attack in card.attacks:
        if pokemon_energy_count(pokemon) >= len(attack.cost):
            if estimate_attack_damage(state, attack, pokemon, opponent) >= pokemon_hp(opponent):
                return True
    return False


def gust_creates_ko(state: Any) -> bool:
    attacker = active_pokemon(state)
    if attacker is None:
        return False
    active_info = get_db().get_card(card_id(attacker))
    if not active_info:
        return False
    energy_count = pokemon_energy_count(attacker)
    for target in bench_pokemon(state, state.opponent_index):
        for attack in active_info.attacks:
            if energy_count >= len(attack.cost) and estimate_attack_damage(state, attack, attacker, target) >= pokemon_hp(target):
                return True
    return False


def is_gust_text(text: str) -> bool:
    return "opponent" in text and "benched" in text and ("switch" in text or "active spot" in text)


def is_disruption_text(text: str) -> bool:
    if "opponent" not in text:
        return False
    return any(word in text for word in ("discard", "shuffle", "bottom of their deck", "hand"))


def same_name_stadium_in_play(state: Any, card_name: str) -> bool:
    if not card_name:
        return False
    stadium = getv(state.current, "stadium", []) or []
    if not isinstance(stadium, list) or not stadium:
        return False
    db = get_db()
    normalized = normalize_card_name(card_name)
    for card in stadium:
        cid = card_id(card)
        current = db.get_card(cid)
        if current and normalize_card_name(current.name) == normalized:
            return True
    return False


def normalize_card_name(name: str) -> str:
    return "".join(ch.lower() for ch in str(name or "") if ch.isalnum())


def prize_value_for_card(cid: Optional[int]) -> int:
    card = get_db().get_card(cid)
    return card.prize_value if card else 1


def card_text(card: Optional[CardInfo]) -> str:
    if card is None:
        return ""
    pieces = [card.text]
    pieces.extend(skill.text for skill in card.skills)
    pieces.extend(attack.text for attack in card.attacks)
    return " ".join(piece for piece in pieces if piece)


def hand_count_after_play(state: Any) -> int:
    return max(0, len(hand_cards(state)) - 1)


def has_card_in_play(state: Any, cid: int) -> bool:
    return any(card_id(pokemon) == cid for _, _, pokemon in iter_in_play(state))


def count_in_play_id(state: Any, cid: int) -> int:
    return sum(1 for _, _, pokemon in iter_in_play(state) if card_id(pokemon) == cid)


def has_any_in_play(state: Any, ids: Iterable[int]) -> bool:
    wanted = set(ids)
    return any(card_id(pokemon) in wanted for _, _, pokemon in iter_in_play(state))


def duplicate_in_play_count(state: Any, cid: int) -> int:
    return sum(1 for _, _, pokemon in iter_in_play(state) if card_id(pokemon) == cid)


def duplicate_in_hand_count(state: Any, cid: int) -> int:
    return sum(1 for card in hand_cards(state) if card_id(card) == cid)


def missing_stage2_payoff(state: Any) -> bool:
    del state
    return False


def rare_candy_line_available(state: Any) -> bool:
    del state
    return False


def active_needs_one_energy(state: Any) -> bool:
    active = active_pokemon(state)
    if active is None:
        return False
    active_id = card_id(active)
    energy_count = pokemon_energy_count(active)
    card = get_db().get_card(active_id)
    if not card:
        return False
    return any(len(attack.cost) == energy_count + 1 for attack in card.attacks)


def is_only_critical_copy_available(state: Any, cid: Optional[int]) -> bool:
    if cid is None:
        return False
    critical = set(list_value("primary_attackers")) | set(list_value("protected_energy_ids"))
    if cid not in critical:
        return False
    return duplicate_in_hand_count(state, cid) <= 1 and count_in_play_id(state, cid) == 0


def energy_matches(attacker_type: str, target_modifier: str) -> bool:
    atk = normalize_energy_label(attacker_type)
    mod = normalize_energy_label(target_modifier)
    return bool(atk and mod and atk in mod)


def normalize_energy_label(value: str) -> str:
    text = str(value or "").upper()
    replacements = {
        "{G}": "G",
        "{R}": "R",
        "{W}": "W",
        "{L}": "L",
        "{P}": "P",
        "{F}": "F",
        "{D}": "D",
        "{M}": "M",
        "GRASS": "G",
        "FIRE": "R",
        "WATER": "W",
        "LIGHTNING": "L",
        "PSYCHIC": "P",
        "FIGHTING": "F",
        "DARKNESS": "D",
        "METAL": "M",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return "".join(ch for ch in text if ch.isalnum())


def option_label(state: Any, option: Any, option_index: int = 0) -> str:
    db = get_db()
    typ = option_type(option)
    cid = card_id_from_option(state, option)
    name = db.card_name(cid) if cid is not None else ""
    try:
        intent = classify_option(state, option, option_index)
        action_prefix = intent.action_class
    except Exception:
        action_prefix = "OPTION"
    if typ == OPT_ATTACK:
        attack = db.get_attack(getv(option, "attackId"))
        if attack is None:
            attack = attack_by_option_order(state, option_index, state.options)
        return action_prefix + " " + (attack.name if attack else str(getv(option, "attackId")))
    if typ == OPT_PLAY:
        return action_prefix + " " + name
    if typ == OPT_ATTACH:
        return action_prefix + " " + name
    if typ == OPT_EVOLVE:
        return action_prefix + " " + name
    if typ == OPT_ABILITY:
        return action_prefix + " " + name
    if typ == OPT_CARD:
        return action_prefix + " " + name
    if typ == OPT_END:
        return action_prefix
    if typ == OPT_YES:
        return action_prefix + " YES"
    if typ == OPT_NO:
        return action_prefix + " NO"
    if typ == OPT_NUMBER:
        return action_prefix + " " + str(option_number(option))
    return action_prefix + " type=" + str(typ) + (" " + name if name else "")
