from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

from action_classifier import ActionCategory, classify_legal_option
from state_eval import card_id_from_option, deck_count, getv, hand_count
from core.priority_tables import canonical_name, canonical_name_from_id, has_in_hand
from core.strategy_scope import use_palaking_strategy


@dataclass(frozen=True)
class SupporterDecision:
    should_use: bool
    option_index: Optional[int] = None
    supporter_name: str = ""
    score: float = 0.0
    reason: str = ""


def choose_best_supporter(state: Any, legal_options: Sequence[Any], deck_goal: Optional[Any] = None) -> SupporterDecision:
    del deck_goal
    if bool(getv(state.current, "supporterPlayed", False)):
        return SupporterDecision(False, reason="Supporter already used.")

    best = SupporterDecision(False, reason="No legal Supporter option.")
    for idx, option in enumerate(legal_options):
        action = classify_legal_option(state, option, idx)
        if action.category != ActionCategory.PLAY_SUPPORTER:
            continue
        name = canonical_name(action.card_name or canonical_name_from_id(card_id_from_option(state, option)))
        if use_palaking_strategy(state):
            score, reason = score_palaking_supporter_by_function(state, option, name)
        else:
            score, reason = score_generic_supporter_by_function(state, name)
        if score > best.score:
            best = SupporterDecision(score > 0.0, idx, name, score, reason)
    return best


def score_generic_supporter_by_function(state: Any, name: str) -> tuple[float, str]:
    if deck_count(state) <= 3 and name == "Lillie's Determination":
        return -9000.0, "Avoid large draw near deck-out."
    if name == "Lillie's Determination":
        return (7800.0 if hand_count(state) <= 4 else 2600.0), "Use Lillie when hand quality is low."
    if name == "Boss's Orders":
        return 350.0, "Use Boss only for a visible prize route."
    return 800.0, "Use the available Supporter when it advances the turn."


def score_palaking_supporter_by_function(state: Any, option: Any, name: str) -> tuple[float, str]:
    del option
    try:
        from core.palafin_planner import (
            dragonite_energy_gap,
            has_ready_finizen_for_palafin,
            score_crispin_play,
            score_hilda_play,
            score_lillie_play,
            score_petrel_play as palaking_petrel_play,
            kieran_plus_damage_creates_visible_ko,
            palafin_ex_overloaded_in_hand,
            zero_to_hero_combo_ready,
        )
        from core.giga_impact_planner import boss_for_giga_route_index, kieran_for_giga_ko_index
    except Exception:
        return score_generic_supporter_by_function(state, name)

    chain_hold = palaking_lillie_chain_hold_active(state)

    if name == "Lillie's Determination":
        score = score_lillie_play(state)
        if chain_hold and not palafin_ex_overloaded_in_hand(state) and alternate_palaking_supporter_legal(state):
            return min(score, -2600.0), "Hold Lillie because a live evolution chain is in hand; use another Supporter first."
        if score < 0:
            return score, "Do not Lillie away an exact Palafin combo or deck-out risk."
        return score, "Use Lillie after obvious setup actions when hand is weak."
    if name == "Team Rocket's Petrel":
        score = palaking_petrel_play(state)
        if chain_hold:
            score = max(score, 4200.0)
        if has_in_hand(state, "Buddy-Buddy Poffin"):
            return score, "Poffin already in hand; Petrel should find Surfing Beach, Switch, Poke Pad, or Secret Box instead."
        return score, "Use Petrel for exact Palafin setup Trainer."
    if name == "Hilda":
        score = score_hilda_play(state)
        if chain_hold:
            score = max(score, 5200.0)
        return score, "Use Hilda for Evolution plus Energy package."
    if name == "Crispin":
        score = score_crispin_play(state)
        if chain_hold:
            score = max(score, 2600.0)
        return score, "Use Crispin mainly to fix Mega Dragonite Energy, or Palafin Water if needed."
    if name == "Boss's Orders":
        if boss_for_giga_route_index(state, getattr(state, "options", []) or []) is not None:
            return 7200.0, "Use Boss because it gives Giga Impact a visible prize route."
        return -1200.0, "Hold Boss; no visible KO or prize-route target."
    if name == "Kieran":
        if kieran_for_giga_ko_index(state, getattr(state, "options", []) or []) is not None or kieran_plus_damage_creates_visible_ko(state):
            return 7000.0, "Use Kieran because +30 makes Giga Impact take a KO."
        if zero_to_hero_combo_ready(state):
            return 4200.0, "Use Kieran as switch if it enables Zero to Hero or resets Palafin."
        return -800.0, "Hold Kieran; no switch reset or +30 damage breakpoint."
    if deck_count(state) <= 4:
        return -9000.0, "Avoid Supporter draw near deck-out."
    if has_ready_finizen_for_palafin(state) or dragonite_energy_gap(state) > 0:
        return 1200.0, "Supporter may improve Palafin/Dragonite setup."
    return 0.0, "Unknown Palaking Supporter function."


def palaking_lillie_chain_hold_active(state: Any) -> bool:
    try:
        from core.lillie_guard import lillie_holds_evolution_chain

        return lillie_holds_evolution_chain(state)
    except Exception:
        return False


def alternate_palaking_supporter_legal(state: Any) -> bool:
    for idx, option in enumerate(getattr(state, "options", []) or []):
        action = classify_legal_option(state, option, idx)
        if action.category != ActionCategory.PLAY_SUPPORTER:
            continue
        name = canonical_name(action.card_name or canonical_name_from_id(card_id_from_option(state, option)))
        if name in {"Team Rocket's Petrel", "Hilda", "Crispin", "Kieran"}:
            return True
        if name == "Boss's Orders":
            try:
                from core.giga_impact_planner import boss_for_giga_route_index

                if boss_for_giga_route_index(state, getattr(state, "options", []) or []) is not None:
                    return True
            except Exception:
                pass
    return False


def score_supporter_router_option(state: Any, option: Any) -> float:
    decision = choose_best_supporter(state, getattr(state, "options", []) or [])
    if decision.option_index is None:
        return 0.0
    try:
        idx = list(getattr(state, "options", []) or []).index(option)
    except ValueError:
        return 0.0
    return decision.score if idx == decision.option_index and decision.should_use else 0.0


def legal_supporter_exists(state: Any, name: str) -> bool:
    for idx, option in enumerate(getattr(state, "options", []) or []):
        action = classify_legal_option(state, option, idx)
        if action.category == ActionCategory.PLAY_SUPPORTER and (action.card_name or canonical_name_from_id(card_id_from_option(state, option))) == name:
            return True
    return False


def supporter_debug(state: Any) -> dict[str, Any]:
    decision = choose_best_supporter(state, getattr(state, "options", []) or [])
    return {
        "supporter_slot": "used" if bool(getv(state.current, "supporterPlayed", False)) else "unused",
        "best_supporter": decision.supporter_name,
        "reason": decision.reason,
    }
