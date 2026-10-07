from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from action_classifier import ActionCategory, classify_legal_option
from state_eval import OPT_ABILITY, OPT_ATTACH, OPT_ATTACK, OPT_EVOLVE, OPT_PLAY, card_id_from_option, option_type
from core.priority_tables import canonical_name_from_id, has_in_hand, has_in_play


@dataclass(frozen=True)
class LilliePrecheck:
    should_wait: bool
    option_index: Optional[int] = None
    reason: str = ""
    score: float = 0.0


def useful_action_before_lillie(state: Any) -> LilliePrecheck:
    for stage in ("item", "board", "resource"):
        best = best_pre_lillie_stage_action(state, stage)
        if best.should_wait:
            return best
    return LilliePrecheck(False)


def best_pre_lillie_stage_action(state: Any, stage: str) -> LilliePrecheck:
    best = LilliePrecheck(False)
    for idx, option in enumerate(getattr(state, "options", []) or []):
        name = canonical_name_from_id(card_id_from_option(state, option))
        if name == "Lillie's Determination":
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
    try:
        from core.combo_presence_planner import score_before_lillie_combo

        combo_score = score_before_lillie_combo(state, option)
        if combo_score:
            return combo_score
    except Exception:
        pass
    if action.category in (ActionCategory.EVOLVE, ActionCategory.RARE_CANDY_EVOLVE) or typ == OPT_EVOLVE:
        return 7000.0
    if action.category == ActionCategory.PLAY_BASIC_TO_BENCH:
        return 6200.0
    if typ == OPT_PLAY:
        if name == "Dawn":
            try:
                from core.fezandipiti_planner import score_post_ko_fezandipiti_enabler

                return 8200.0 if score_post_ko_fezandipiti_enabler(state, "Dawn") >= 5000.0 else 0.0
            except Exception:
                return 0.0
        if name in {"Sacred Ash", "Night Stretcher", "Energy Recycler"}:
            try:
                from core.recovery_goal_planner import score_recovery_goal_option
                from core.recovery_timing_planner import score_recovery_timing_option

                recovery_score = max(score_recovery_timing_option(state, option), score_recovery_goal_option(state, option))
                return 9000.0 if recovery_score >= 2000.0 else 0.0
            except Exception:
                return 0.0
        if name == "Buddy-Buddy Poffin":
            return 6800.0
        if name == "Poke Pad":
            return 4200.0
        if name == "Rare Candy":
            return 6500.0
        if name == "Ultra Ball":
            try:
                from core.discard_cost_guard import score_discard_cost_play_safety

                return 4600.0 if score_discard_cost_play_safety(state, "Ultra Ball", 2) > -3000.0 else 0.0
            except Exception:
                return 2600.0
        if name == "Secret Box":
            try:
                from core.secret_box_planner import choose_secret_box_package

                package = choose_secret_box_package(state)
                return package.score if package.should_use else 0.0
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
        try:
            from core.fezandipiti_planner import score_fezandipiti_option

            if score_fezandipiti_option(state, option) >= 5000.0:
                return 8200.0
        except Exception:
            pass
        try:
            from core.toxtricity_engine_planner import score_toxtricity_option

            if score_toxtricity_option(state, option, 0.0) >= 1800.0:
                return 2800.0
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
        try:
            from core.fezandipiti_planner import score_fezandipiti_option

            if score_fezandipiti_option(state, option) >= 5000.0:
                return 7800.0
        except Exception:
            pass
    return 0.0
