from __future__ import annotations

from typing import Any, List, Optional, Sequence

from action_classifier import ActionCategory, ClassifiedAction, classify_legal_option
from core.action_intent import ActionIntent, ActionIntentType
from core.agent_memory import AgentMemory
from decision_reason import explain_choice
from state_eval import getv, int_or

import policy as legacy_policy


def choose_intent(state: Any, memory: AgentMemory) -> ActionIntent:
    """Choose an adapter-neutral intent from a normalized game state.

    The current implementation reuses the tested cabt legal-option scorer and
    wraps its selected option indices in an ActionIntent. The intent object is
    then translated by the active adapter.
    """
    select = legacy_policy.parse_select(state.obs)
    options = legacy_policy.classify_all_options(state, select)
    moment = legacy_policy.identify_moment_type(state, select, options)
    try:
        setattr(state, "moment_type", moment)
    except Exception:
        pass

    if legacy_policy.is_mandatory_prompt(select, options):
        choice = legacy_policy.choose_mandatory_action(state, select, options)
    elif legacy_policy.is_setup_phase(state, select, options):
        choice = legacy_policy.choose_setup_action(state, select, options)
    elif legacy_policy.is_opponent_turn_prompt(state, select, options):
        choice = legacy_policy.choose_reaction_action(state, select, options)
    elif moment == legacy_policy.MomentType.EFFECT_RESOLUTION:
        choice = legacy_policy.choose_effect_resolution_action(state, select, options)
    elif legacy_policy.is_our_main_turn(state, select, options):
        choice = legacy_policy.choose_main_turn_action(state, select, options)
    else:
        choice = legacy_policy.safe_fallback(select, state)

    scores = legacy_policy.score_options(state)
    intent = build_intent_from_choice(state, choice, scores, options)
    memory.record_intent(state, intent)
    return intent


def build_intent_from_choice(
    state: Any,
    choice: Sequence[int],
    scores: Sequence[float],
    classified_options: Optional[Sequence[ClassifiedAction]] = None,
) -> ActionIntent:
    selected = list(choice)
    classified = list(classified_options or [classify_legal_option(state, option, idx) for idx, option in enumerate(state.options)])
    first = classified[selected[0]] if selected and 0 <= selected[0] < len(classified) else None
    category = first.category if first else ActionCategory.UNKNOWN
    score = scores[selected[0]] if selected and 0 <= selected[0] < len(scores) else 0.0
    intent_type = category_to_intent_type(category)
    reason = explain_choice(state, selected, scores) if selected else "Decline optional selection"
    analysis_rule_names = []
    strategy_id = ""
    try:
        from core.deck_profile import generated_policy_rules

        analysis_rule_names = [rule.rule_name for rule in generated_policy_rules()]
    except Exception:
        analysis_rule_names = []
    try:
        from core.strategy_scope import active_strategy_id

        strategy_id = active_strategy_id(state)
    except Exception:
        strategy_id = ""
    return ActionIntent(
        intent_type=intent_type,
        selected_option_indices=selected,
        source_card_id=first.card_id if first else None,
        source_card_name=first.card_name if first else "",
        target_card_id=first.target_id if first else None,
        target_card_name=first.target_name if first else "",
        target_zone=zone_from_action(first),
        selected_cards=[item.card_id for item in selected_classified(classified, selected) if item.card_id is not None],
        priority_score=float(score),
        reason=reason,
        mandatory=is_mandatory(state, category),
        optional=int_or(getv(state.select, "minCount", 0), 0) == 0,
        consumes_supporter=category == ActionCategory.PLAY_SUPPORTER,
        consumes_energy_attachment=category == ActionCategory.ATTACH_ENERGY,
        consumes_retreat=category == ActionCategory.RETREAT,
        consumes_stadium=category == ActionCategory.PLAY_STADIUM,
        submission_safe=True,
        metadata={
            "strategy_id": strategy_id,
            "category": category,
            "moment_type": str(getattr(state, "moment_type", "")),
            "scores": [float(scores[idx]) for idx in selected if 0 <= idx < len(scores)],
            "analysis_rules_available": analysis_rule_names,
        },
    )


def category_to_intent_type(category: str) -> str:
    return {
        ActionCategory.DRAW_OR_SEARCH: ActionIntentType.SEARCH_CARD,
        ActionCategory.PLAY_BASIC_TO_BENCH: ActionIntentType.BENCH_BASIC,
        ActionCategory.EVOLVE: ActionIntentType.EVOLVE,
        ActionCategory.RARE_CANDY_EVOLVE: ActionIntentType.RARE_CANDY_EVOLVE,
        ActionCategory.ATTACH_ENERGY: ActionIntentType.ATTACH_ENERGY,
        ActionCategory.PLAY_ITEM: ActionIntentType.PLAY_ITEM,
        ActionCategory.PLAY_SUPPORTER: ActionIntentType.PLAY_SUPPORTER,
        ActionCategory.PLAY_STADIUM: ActionIntentType.PLAY_STADIUM,
        ActionCategory.USE_ABILITY: ActionIntentType.USE_ABILITY,
        ActionCategory.RETREAT: ActionIntentType.RETREAT,
        ActionCategory.SWITCH_ACTIVE: ActionIntentType.SWITCH_ACTIVE,
        ActionCategory.ATTACK: ActionIntentType.ATTACK,
        ActionCategory.CHOOSE_ATTACK_TARGET: ActionIntentType.CHOOSE_TARGET,
        ActionCategory.CHOOSE_EFFECT_TARGET: ActionIntentType.CHOOSE_TARGET,
        ActionCategory.DISCARD_COST: ActionIntentType.DISCARD_CARD,
        ActionCategory.RECOVER_FROM_DISCARD: ActionIntentType.SEARCH_CARD,
        ActionCategory.SHUFFLE_INTO_DECK: ActionIntentType.SEARCH_CARD,
        ActionCategory.PRIZE_SELECTION: ActionIntentType.TAKE_PRIZE,
        ActionCategory.PROMOTE_AFTER_KO: ActionIntentType.PROMOTE_AFTER_KO,
        ActionCategory.END_TURN: ActionIntentType.PASS,
        ActionCategory.SETUP_CHOOSE_BENCH: ActionIntentType.BENCH_BASIC,
        ActionCategory.SETUP_CHOOSE_ACTIVE: ActionIntentType.PROMOTE_AFTER_KO,
    }.get(category, ActionIntentType.UNKNOWN)


def selected_classified(classified: Sequence[ClassifiedAction], selected: Sequence[int]) -> List[ClassifiedAction]:
    return [classified[idx] for idx in selected if 0 <= idx < len(classified)]


def is_mandatory(state: Any, category: str) -> bool:
    if int_or(getv(state.select, "minCount", 0), 0) <= 0:
        return False
    return category in legacy_policy.MANDATORY_PROMPT_CATEGORIES


def zone_from_action(action: Optional[ClassifiedAction]) -> str:
    if action is None:
        return ""
    if action.target_area >= 0:
        return str(action.target_area)
    return ""
