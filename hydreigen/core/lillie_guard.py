from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from action_classifier import ActionCategory, classify_legal_option
from state_eval import OPT_ABILITY, OPT_ATTACH, OPT_ATTACK, OPT_EVOLVE, OPT_PLAY, card_id_from_option, option_type
from core.priority_tables import canonical_name_from_id


@dataclass(frozen=True)
class LilliePrecheck:
    should_wait: bool
    option_index: Optional[int] = None
    reason: str = ""
    score: float = 0.0


def useful_action_before_lillie(state: Any) -> LilliePrecheck:
    best = LilliePrecheck(False)
    for idx, option in enumerate(getattr(state, "options", []) or []):
        name = canonical_name_from_id(card_id_from_option(state, option))
        if name == "Lillie's Determination":
            continue
        score = score_pre_lillie_action(state, option, idx, name)
        if score > best.score:
            best = LilliePrecheck(True, idx, f"Use {name or 'useful action'} before Lillie's Determination.", score)
    return best if best.score >= 900.0 else LilliePrecheck(False)


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
    if typ == OPT_ATTACH or action.category == ActionCategory.ATTACH_ENERGY:
        try:
            from core.energy_planner import score_energy_option

            return 1800.0 if score_energy_option(state, option) >= 800.0 else 0.0
        except Exception:
            return 0.0
    if typ == OPT_ABILITY or action.category == ActionCategory.USE_ABILITY:
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
            from core.fezandipiti_planner import score_fezandipiti_option

            if score_fezandipiti_option(state, option) >= 5000.0:
                return 7800.0
        except Exception:
            pass
    return 0.0
