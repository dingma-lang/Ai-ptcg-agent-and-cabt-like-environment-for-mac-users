from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from action_classifier import ActionCategory, classify_legal_option
from state_eval import OPT_ABILITY, OPT_ATTACH, OPT_ATTACK, OPT_EVOLVE, OPT_PLAY, OPT_RETREAT, active_pokemon, card_id_from_option, getv, option_type
from core.priority_tables import canonical_name_from_id, has_in_hand, has_in_play
from core.strategy_scope import use_palaking_strategy


@dataclass(frozen=True)
class LilliePrecheck:
    should_wait: bool
    option_index: Optional[int] = None
    reason: str = ""
    score: float = 0.0


def useful_action_before_lillie(state: Any) -> LilliePrecheck:
    cache = getattr(state, "decision_score_cache", None)
    if cache is not None and "pre_lillie" in cache:
        return cache["pre_lillie"]
    result = _useful_action_before_lillie(state)
    if cache is not None:
        cache["pre_lillie"] = result
    return result


def _useful_action_before_lillie(state: Any) -> LilliePrecheck:
    for stage in ("item", "board", "resource"):
        best = best_pre_lillie_stage_action(state, stage)
        if best.should_wait:
            return best
    return LilliePrecheck(False)


def hand_is_stalled(state: Any) -> bool:
    """Hand size is not hand quality: distinguish dead cards from a usable turn."""
    from card_db import get_db
    from policy import estimate_attack_damage

    if useful_action_before_lillie(state).should_wait:
        return False
    for option in state.options:
        if option_type(option) != OPT_ATTACK:
            continue
        attack = get_db().get_attack(getv(option, "attackId"))
        if attack and estimate_attack_damage(state, attack, active_pokemon(state),
                                             active_pokemon(state, state.opponent_index)) > 0:
            return False
    return True


def best_pre_lillie_stage_action(state: Any, stage: str) -> LilliePrecheck:
    best = LilliePrecheck(False)
    for idx, option in enumerate(getattr(state, "options", []) or []):
        name = canonical_name_from_id(card_id_from_option(state, option))
        if name in {"Lillie's Determination", "Judge"}:
            continue
        if pre_lillie_stage(state, option, idx, name) != stage:
            continue
        score = score_pre_lillie_action(state, option, idx, name)
        if score > best.score:
            best = LilliePrecheck(True, idx, f"Use {name or 'useful action'} before Lillie's Determination.", score)
    return best if best.score >= 900.0 else LilliePrecheck(False)


def pre_lillie_stage(state: Any, option: Any, idx: int, name: str = "") -> str:
    action = classify_legal_option(state, option, idx)
    typ = option_type(option)
    if action.category in (ActionCategory.EVOLVE, ActionCategory.RARE_CANDY_EVOLVE, ActionCategory.PLAY_BASIC_TO_BENCH):
        return "board"
    if action.category in (ActionCategory.PLAY_ITEM, ActionCategory.PLAY_STADIUM, ActionCategory.DRAW_OR_SEARCH):
        return "item"
    if typ == OPT_PLAY and name not in {
        "Lillie's Determination",
        "Judge",
        "Team Rocket's Petrel",
        "Boss's Orders",
        "Crispin",
        "Hilda",
        "Kieran",
    }:
        return "item"
    if typ == OPT_EVOLVE:
        return "board"
    if typ in (OPT_ATTACH, OPT_ABILITY, OPT_ATTACK):
        return "resource"
    return "board"


def lillie_holds_evolution_chain(state: Any) -> bool:
    return any(
        (
            has_in_play(state, "Finizen") and has_in_hand(state, "Palafin"),
            has_in_play(state, "Dratini") and has_in_hand(state, "Dragonair"),
            has_in_play(state, "Dragonair") and has_in_hand(state, "Mega Dragonite ex"),
            has_in_play(state, "Palafin") and has_in_hand(state, "Palafin ex"),
        )
    )


def score_pre_lillie_action(state: Any, option: Any, idx: int, name: str = "") -> float:
    typ = option_type(option)
    action = classify_legal_option(state, option, idx)
    if typ == OPT_RETREAT:
        from core.palafin_planner import score_retreat_option

        score = score_retreat_option(state)
        return score if score >= 1500.0 else 0.0
    if action.category in (ActionCategory.EVOLVE, ActionCategory.RARE_CANDY_EVOLVE) or typ == OPT_EVOLVE:
        if use_palaking_strategy(state):
            try:
                from core.palafin_planner import score_palaking_option

                return score_palaking_option(state, option, 0.0, idx)
            except Exception:
                pass
        return 7000.0
    if action.category == ActionCategory.PLAY_BASIC_TO_BENCH:
        if use_palaking_strategy(state):
            try:
                from core.palafin_planner import score_palaking_option

                score = score_palaking_option(state, option, 0.0, idx)
                return score if score >= 900.0 else 0.0
            except Exception:
                pass
        return 6200.0
    if typ == OPT_PLAY:
        if name == "Battle Cage":
            from core.palfingon_cards import score_battle_cage

            return max(0.0, score_battle_cage(state))
        if name in {"Sacred Ash", "Night Stretcher", "Energy Retrieval"}:
            try:
                from core.recovery_planner import score_recovery_option

                return 9000.0 if score_recovery_option(state, option) >= 2000.0 else 0.0
            except Exception:
                return 0.0
        if name == "Buddy-Buddy Poffin":
            try:
                from core.palafin_planner import score_palaking_option

                score = score_palaking_option(state, option, 0.0, idx)
                return score if score >= 2500.0 else 0.0
            except Exception:
                return 0.0
        if name == "Poke Pad":
            try:
                from core.palafin_planner import score_palaking_option

                score = score_palaking_option(state, option, 0.0, idx)
                return score if score >= 1200.0 else 0.0
            except Exception:
                return 0.0
        if name == "Secret Box":
            try:
                from core.palafin_planner import score_palaking_option

                palaking_score = score_palaking_option(state, option, 0.0, idx)
                return palaking_score if palaking_score >= 1500.0 else 0.0
            except Exception:
                return 0.0
        if name in {"Surfing Beach", "Switch", "Air Balloon"}:
            try:
                from core.palafin_planner import score_palaking_option

                palaking_score = score_palaking_option(state, option, 0.0, idx)
                return palaking_score if palaking_score >= 1500.0 else 0.0
            except Exception:
                return 0.0
    if name in {"Surfing Beach", "Switch", "Air Balloon"} and typ == OPT_ATTACH:
        try:
            from core.palafin_planner import score_palaking_option

            palaking_score = score_palaking_option(state, option, 0.0, idx)
            return palaking_score if palaking_score >= 1500.0 else 0.0
        except Exception:
            return 0.0
    if typ == OPT_ATTACH or action.category == ActionCategory.ATTACH_ENERGY:
        try:
            from core.energy_planner import score_energy_option

            return 1800.0 if score_energy_option(state, option) >= 800.0 else 0.0
        except Exception:
            return 0.0
    if typ == OPT_ABILITY or action.category == ActionCategory.USE_ABILITY:
        try:
            from core.palafin_planner import palafin_ex_overloaded_in_hand, score_palaking_option

            if name == "Palafin" and palafin_ex_overloaded_in_hand(state):
                return 0.0

            palaking_score = score_palaking_option(state, option, 0.0, idx)
            if palaking_score >= 6500.0:
                return palaking_score
        except Exception:
            pass
    if typ == OPT_ATTACK or action.category == ActionCategory.ATTACK:
        try:
            from core.palafin_planner import is_setup_ability_attack, palafin_ex_overloaded_in_hand, score_palaking_option

            if is_setup_ability_attack(state, option):
                if name == "Palafin" and palafin_ex_overloaded_in_hand(state):
                    return 0.0
                palaking_score = score_palaking_option(state, option, 0.0, idx)
                if palaking_score >= 6500.0:
                    return palaking_score
        except Exception:
            pass
    return 0.0
