from __future__ import annotations

from typing import Any, Optional, Sequence

from action_classifier import ActionCategory, classify_legal_option
from core.action_intent import ActionIntent, ActionIntentType
from state_eval import OPT_PLAY, bench_pokemon, card_id_from_option, deck_count, getv, option_type
from core.poffin_planner import should_use_poffin_now
from core.pokepad_planner import should_use_pokepad_now
from core.priority_tables import canonical_name_from_id, count_in_play, has_in_play
from core.supporter_planner import hand_playability_score


def opening_script_action(state: Any, legal_options: Sequence[Any] | None = None) -> Optional[ActionIntent]:
    options = list(legal_options or getattr(state, "options", []) or [])
    if not opening_condition(state):
        return None

    fez_idx = post_ko_fezandipiti_action(state, options)
    if fez_idx is not None:
        name = option_name(state, options[fez_idx])
        return intent(fez_idx, name, "Post-KO rule: find or use Fezandipiti ex before ordinary draw.", 5600.0)

    basic_idx = best_setup_basic_from_hand(state, options)
    if basic_idx is not None:
        name = canonical_name_from_id(card_id_from_option(state, options[basic_idx]))
        return intent(basic_idx, name, f"Opening rule: bench {name} from hand before search/draw.", 7200.0)

    try:
        from core.setup_recovery_planner import setup_action_now

        setup = setup_action_now(state, options)
        if setup.should_act and setup.option_index is not None:
            return intent(setup.option_index, option_name(state, options[setup.option_index]), setup.reason, setup.score)
    except Exception:
        pass

    poffin = should_use_poffin_now(state, options)
    if poffin.should_act and poffin.option_index is not None:
        return intent(poffin.option_index, "Buddy-Buddy Poffin", poffin.reason, poffin.score)

    pokepad = should_use_pokepad_now(state, options)
    if pokepad.should_act and pokepad.option_index is not None:
        return intent(pokepad.option_index, "Poke Pad", pokepad.reason, pokepad.score)

    supporter_idx = lillie_if_dead_hand(state, options)
    if supporter_idx is not None and not better_opening_action_exists(state, options):
        return intent(supporter_idx, "Lillie's Determination", "Opening rule: use Lillie's Determination because hand is weak.", 900.0)
    return None


def opening_condition(state: Any) -> bool:
    turn = int(getv(state.current, "turn", 0) or 0)
    if turn <= 4:
        return True
    if len(bench_pokemon(state)) < 3:
        return True
    if not has_in_play(state, "Hydreigon ex") and not has_in_play(state, "Mega Gengar ex"):
        return True
    if count_in_play(state, "Deino") == 0 and not has_in_play(state, "Gastly"):
        return True
    return False


def best_setup_basic_from_hand(state: Any, options: Sequence[Any]) -> Optional[int]:
    try:
        from core.basic_bench_planner import best_basic_bench_from_hand

        return best_basic_bench_from_hand(state, options)
    except Exception:
        priorities = {"Deino": 500, "Gastly": 400, "Toxel": 300, "Fezandipiti ex": 250, "Pecharunt ex": 200}
        best = None
        best_score = -1
        for idx, option in enumerate(options):
            action = classify_legal_option(state, option, idx)
            if action.category != ActionCategory.PLAY_BASIC_TO_BENCH:
                continue
            name = canonical_name_from_id(card_id_from_option(state, option))
            score = priorities.get(name, 100)
            if score > best_score:
                best = idx
                best_score = score
        return best if best_score > 0 else None


def lillie_if_dead_hand(state: Any, options: Sequence[Any]) -> Optional[int]:
    if bool(getv(state.current, "supporterPlayed", False)) or deck_count(state) <= 3:
        return None
    if hand_playability_score(state) >= 120.0:
        return None
    for idx, option in enumerate(options):
        if option_type(option) != OPT_PLAY:
            continue
        if canonical_name_from_id(card_id_from_option(state, option)) == "Lillie's Determination":
            return idx
    return None


def better_opening_action_exists(state: Any, options: Sequence[Any]) -> bool:
    for idx, option in enumerate(options):
        action = classify_legal_option(state, option, idx)
        if action.category in (
            ActionCategory.USE_ABILITY,
            ActionCategory.EVOLVE,
            ActionCategory.RARE_CANDY_EVOLVE,
            ActionCategory.ATTACH_ENERGY,
        ):
            return True
        try:
            from core.fezandipiti_planner import score_fezandipiti_option, score_pre_ko_fezandipiti_enabler

            if score_fezandipiti_option(state, option) > 0:
                return True
            if option_type(option) == OPT_PLAY and score_pre_ko_fezandipiti_enabler(state, option_name(state, option)) > 0:
                return True
        except Exception:
            pass
        try:
            from core.mega_gengar_planner import score_mega_gengar_option

            if score_mega_gengar_option(state, option, 0.0) >= 2000.0:
                return True
        except Exception:
            pass
        try:
            from core.recovery_goal_planner import score_recovery_goal_option

            if score_recovery_goal_option(state, option) >= 2000.0:
                return True
        except Exception:
            pass
    return False


def post_ko_fezandipiti_action(state: Any, options: Sequence[Any]) -> Optional[int]:
    best_idx = None
    best_score = 0.0
    try:
        from core.fezandipiti_planner import score_fezandipiti_option, score_post_ko_fezandipiti_enabler
    except Exception:
        return None

    for idx, option in enumerate(options):
        score = score_fezandipiti_option(state, option)
        name = option_name(state, option)
        if option_type(option) == OPT_PLAY and name in {"Dawn", "Ultra Ball"}:
            score = max(score, score_post_ko_fezandipiti_enabler(state, name))
        if score > best_score:
            best_idx = idx
            best_score = score
    return best_idx if best_score > 0 else None


def option_name(state: Any, option: Any) -> str:
    return canonical_name_from_id(card_id_from_option(state, option))


def intent(index: int, source: str, reason: str, score: float) -> ActionIntent:
    return ActionIntent(
        intent_type=ActionIntentType.PLAY_CARD_FROM_HAND,
        selected_option_indices=[int(index)],
        source_card_name=source,
        priority_score=float(score),
        reason=reason,
        submission_safe=True,
    )
