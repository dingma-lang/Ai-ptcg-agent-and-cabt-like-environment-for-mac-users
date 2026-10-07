from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

from action_classifier import ActionCategory, classify_legal_option
from state_eval import card_id_from_option, getv, hand_count
from core.crispin_planner import hydreigon_crispin_plan, score_crispin_option
from core.deck_operating_system import DeckGoalState, compute_deck_goal_state
from core.priority_tables import canonical_name, canonical_name_from_id, has_in_hand
from core.strategy_scope import use_palaking_strategy
from core.trainer_search_planner import best_petrel_trainer_need, score_petrel_play


@dataclass(frozen=True)
class SupporterDecision:
    should_use: bool
    option_index: Optional[int] = None
    supporter_name: str = ""
    score: float = 0.0
    reason: str = ""


def choose_best_supporter(state: Any, legal_options: Sequence[Any], deck_goal: Optional[DeckGoalState] = None) -> SupporterDecision:
    if bool(getv(state.current, "supporterPlayed", False)):
        return SupporterDecision(False, reason="Supporter already used.")
    if use_palaking_strategy(state):
        best = SupporterDecision(False, reason="No legal Palaking Supporter option.")
        for idx, option in enumerate(legal_options):
            action = classify_legal_option(state, option, idx)
            if action.category != ActionCategory.PLAY_SUPPORTER:
                continue
            name = canonical_name(action.card_name or canonical_name_from_id(card_id_from_option(state, option)))
            score, reason = score_palaking_supporter_by_function(state, option, name)
            if score > best.score:
                best = SupporterDecision(score > 0.0, idx, name, score, reason)
        return best
    deck_goal = deck_goal or compute_deck_goal_state(state)
    best = SupporterDecision(False, reason="No legal Supporter option.")
    for idx, option in enumerate(legal_options):
        action = classify_legal_option(state, option, idx)
        if action.category != ActionCategory.PLAY_SUPPORTER:
            continue
        name = canonical_name(action.card_name or canonical_name_from_id(card_id_from_option(state, option)))
        score, reason = score_supporter_by_function(state, option, name, deck_goal)
        if score > best.score:
            best = SupporterDecision(score > 0.0, idx, name, score, reason)
    return best


def score_supporter_by_function(state: Any, option: Any, name: str, deck_goal: DeckGoalState) -> tuple[float, str]:
    turn = int(getv(state.current, "turn", 0) or 0)
    if name == "Crispin":
        score = score_crispin_option(state, option)
        return score, "Use Crispin because Hydreigon ex is evolved and lacks required Energy."
    if name == "Team Rocket's Petrel":
        if has_in_hand(state, "Buddy-Buddy Poffin") and deck_goal.open_bench_slots > 0:
            return -2200.0, "Poffin already in hand, do not Petrel for Poffin."
        need = best_petrel_trainer_need(state)
        return (score_petrel_play(state, option), need.reason if need.name else "No exact Trainer need.")
    if name == "Dawn":
        if deck_goal.missing_core_pieces or deck_goal.missing_evolution_pieces or deck_goal.missing_support_basics:
            return 5200.0 + min(deck_goal.setup_urgency, 2600.0), "Use Dawn because Pokemon pieces are missing."
        return 600.0, "Dawn has low value because Pokemon package is mostly complete."
    if name == "Lillie's Determination":
        from state_eval import deck_count

        if deck_count(state) <= 3:
            return -9000.0, "Do not use Lillie because deck-out risk is too high."
        try:
            from core.prize_availability_tracker import infer_card_availability
            from core.recovery_goal_planner import recovery_card_legal

            if infer_card_availability(state, None).all_deino_in_discard and recovery_card_legal(state):
                return -5000.0, "Do not use Lillie because Deino recovery is available now."
        except Exception:
            pass
        try:
            from core.lillie_guard import useful_action_before_lillie

            precheck = useful_action_before_lillie(state)
            if precheck.should_wait:
                return -2600.0, precheck.reason
        except Exception:
            pass
        base = 9800.0 if hand_count(state) <= 4 or (turn <= 4 and not deck_goal.target_board_complete) else 7600.0
        return base + min(deck_goal.setup_urgency, 1800.0), "Use Lillie's Determination as the preferred Supporter after checking useful hand actions."
    if name == "Boss's Orders":
        return 350.0, "Use Boss only if it improves prize route."
    if name == "Special Red Card":
        return 500.0 if deck_goal.target_board_complete else -700.0, "Use disruption only after setup is stable."
    return 0.0, "Unknown Supporter function."


def score_palaking_supporter_by_function(state: Any, option: Any, name: str) -> tuple[float, str]:
    del option
    try:
        from core.palafin_planner import (
            dragonite_energy_gap,
            has_ready_finizen_for_palafin,
            missing_switch_engine,
            score_crispin_play,
            score_hilda_play,
            score_lillie_play,
            score_petrel_play as palaking_petrel_play,
            kieran_plus_damage_creates_visible_ko,
            palafin_ex_overloaded_in_hand,
            zero_to_hero_combo_ready,
        )
        from core.giga_impact_planner import boss_for_giga_route_index, kieran_for_giga_ko_index
        from state_eval import deck_count
    except Exception:
        return 0.0, "Palaking Supporter helper unavailable."

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
            return score, "Poffin already in hand; Petrel should find Surfing Beach, Switch, Poké Pad, or Secret Box instead."
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
    decision = choose_best_supporter(state, getattr(state, "options", []) or [], compute_deck_goal_state(state))
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
    decision = choose_best_supporter(state, getattr(state, "options", []) or [], compute_deck_goal_state(state))
    return {
        "supporter_slot": "used" if bool(getv(state.current, "supporterPlayed", False)) else "unused",
        "best_supporter": decision.supporter_name,
        "reason": decision.reason,
    }
