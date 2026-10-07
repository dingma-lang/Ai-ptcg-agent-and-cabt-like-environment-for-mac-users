from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from state_eval import OPT_CARD, OPT_PLAY, card_id, card_id_from_option, hand_cards, option_type
from core.deck_operating_system import compute_deck_goal_state
from core.priority_tables import LOW_PRIORITY_DISCARD_IDS, PROTECTED_IDS, canonical_name_from_id, has_in_hand
from core.strategy_scope import use_palaking_strategy


@dataclass(frozen=True)
class SecretBoxPackage:
    should_use: bool
    score: float = 0.0
    reason: str = ""


def score_secret_box_option(state: Any, option: Any) -> float:
    if option_type(option) != OPT_PLAY or canonical_name_from_id(card_id_from_option(state, option)) != "Secret Box":
        return 0.0
    package = choose_secret_box_package(state)
    return package.score if package.should_use else -1200.0


def choose_secret_box_package(state: Any) -> SecretBoxPackage:
    if use_palaking_strategy(state):
        try:
            from core.palafin_planner import score_secret_box_play, secret_box_discard_safety, secret_box_palafin_chain_available

            safety = secret_box_discard_safety(state)
            if safety <= -4500.0:
                return SecretBoxPackage(False, safety, "Do not use Secret Box because discard is unsafe.")
            if secret_box_palafin_chain_available(state):
                return SecretBoxPackage(True, score_secret_box_play(state), "Use Secret Box for Poké Pad, Air Balloon, Surfing Beach, and Supporter package.")
            score = score_secret_box_play(state)
            if score > 0.0:
                return SecretBoxPackage(True, score, "Use Secret Box to assemble Palafin/Dragonite setup package.")
            return SecretBoxPackage(False, score, "Hold Secret Box because the Palafin package is not needed.")
        except Exception:
            pass

    discard_penalty = secret_box_discard_safety_penalty(state)
    if discard_penalty <= -4500.0:
        return SecretBoxPackage(False, discard_penalty, "Do not use Secret Box because discard is unsafe.")
    try:
        from core.combo_presence_planner import (
            gengar_bridge_needed,
            hydreigon_bridge_needed,
            secret_box_energy_recycler_combo,
        )

        if hydreigon_bridge_needed(state):
            return SecretBoxPackage(True, 7800.0 + discard_penalty, "Use Secret Box to find Rare Candy or a Hydreigon bridge card.")
        if gengar_bridge_needed(state):
            return SecretBoxPackage(True, 7400.0 + discard_penalty, "Use Secret Box to find a Gengar bridge card.")
        if secret_box_energy_recycler_combo(state):
            return SecretBoxPackage(True, 5900.0 + discard_penalty, "Use Secret Box because Energy Recycler covers the Energy discard package.")
    except Exception:
        pass
    goal = compute_deck_goal_state(state)
    if goal.setup_urgency >= 4500.0:
        return SecretBoxPackage(True, 7200.0 + discard_penalty, "Use Secret Box as supporter-access package.")
    if hydreigon_energy_or_evolution_package_needed(state):
        return SecretBoxPackage(True, 6800.0 + discard_penalty, "Use Secret Box for Hydreigon evolution/Energy package.")
    if not goal.target_board_complete and not has_stronger_setup_in_hand(state):
        return SecretBoxPackage(True, 5200.0 + discard_penalty, "Use Secret Box to assemble target field package.")
    return SecretBoxPackage(False, -1200.0, "Hold Secret Box because hand is already functional.")


def score_secret_box_target_selection(state: Any, cid: Optional[int], name: str) -> float:
    if use_palaking_strategy(state):
        try:
            from core.palafin_planner import score_secret_box_target

            return score_secret_box_target(state, name)
        except Exception:
            pass

    package = choose_secret_box_package(state)
    if not package.should_use:
        return -500.0
    try:
        from core.combo_presence_planner import score_combo_search_target
        from core.priority_tables import context_source_name

        combo_score = score_combo_search_target(state, cid, context_source_name(state) or "Secret Box")
        if combo_score:
            return combo_score
    except Exception:
        pass
    if name == "Buddy-Buddy Poffin":
        return 9000.0 if "Deino" in compute_deck_goal_state(state).missing_core_pieces or "Gastly" in compute_deck_goal_state(state).missing_core_pieces else 3000.0
    if name == "Rare Candy":
        try:
            from core.trainer_search_planner import rare_candy_needed_now

            return 8800.0 if rare_candy_needed_now(state) else 2500.0
        except Exception:
            return 2500.0
    if name == "Ultra Ball":
        return 7600.0
    if name == "Air Balloon":
        return 5600.0
    if name == "Crispin":
        try:
            from core.crispin_planner import hydreigon_crispin_plan

            if hydreigon_crispin_plan(state).should_use:
                return 9000.0
        except Exception:
            pass
        return 4000.0
    if name == "Dawn":
        return 7200.0
    if name == "Lillie's Determination":
        return 6500.0
    if name == "Battle Cage":
        return 5200.0
    return 0.0


def safe_secret_box_discard(state: Any) -> bool:
    return secret_box_discard_safety_penalty(state) > -4500.0


def secret_box_discard_safety_penalty(state: Any) -> float:
    if use_palaking_strategy(state):
        try:
            from core.palafin_planner import secret_box_discard_safety

            return secret_box_discard_safety(state)
        except Exception:
            pass

    try:
        from core.discard_cost_guard import discard_cost_plan, score_discard_cost_play_safety

        plan = discard_cost_plan(state, "Secret Box", 3)
        penalty = score_discard_cost_play_safety(state, "Secret Box", 3)
        if plan.safe_count >= 3:
            return 0.0
        if emergency_secret_box_can_spend_thin_hand(state) and plan.safe_count >= 2:
            return -1800.0
        return penalty
    except Exception:
        hand_ids = [card_id(card) for card in hand_cards(state)]
        if len(hand_ids) < 4:
            return -6000.0
        safe = sum(1 for cid in hand_ids if cid in LOW_PRIORITY_DISCARD_IDS or hand_ids.count(cid) >= 2)
        protected = sum(1 for cid in hand_ids if cid in PROTECTED_IDS)
        return 0.0 if safe >= 3 and protected <= 2 else -5200.0


def emergency_secret_box_can_spend_thin_hand(state: Any) -> bool:
    try:
        goal = compute_deck_goal_state(state)
        return goal.setup_urgency >= 6500.0
    except Exception:
        return False


def hydreigon_energy_or_evolution_package_needed(state: Any) -> bool:
    try:
        from core.crispin_planner import hydreigon_crispin_plan
        from core.trainer_search_planner import rare_candy_needed_now

        return hydreigon_crispin_plan(state).should_use or rare_candy_needed_now(state)
    except Exception:
        return False


def has_stronger_setup_in_hand(state: Any) -> bool:
    if use_palaking_strategy(state):
        return any(has_in_hand(state, name) for name in ("Buddy-Buddy Poffin", "Poke Pad", "Surfing Beach", "Switch"))
    return any(has_in_hand(state, name) for name in ("Buddy-Buddy Poffin", "Rare Candy", "Ultra Ball", "Dawn"))


def is_secret_box_context(state: Any) -> bool:
    try:
        from core.priority_tables import context_source_name

        return context_source_name(state) == "Secret Box"
    except Exception:
        return False
