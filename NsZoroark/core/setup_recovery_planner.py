from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

from action_classifier import ActionCategory, classify_legal_option
from state_eval import OPT_PLAY, bench_pokemon, bench_space, card_id_from_option, deck_count, getv, hand_cards, option_type
from core.priority_tables import CARD_IDS, canonical_name_from_id, count_in_play, has_in_hand, has_in_play


SETUP_BASIC_IDS = {CARD_IDS["Deino"], CARD_IDS["Gastly"], CARD_IDS["Toxel"], CARD_IDS["Fezandipiti ex"], CARD_IDS["Pecharunt ex"]}
CORE_TEAM_IDS = {
    CARD_IDS["Deino"],
    CARD_IDS["Hydreigon ex"],
    CARD_IDS["Gastly"],
    CARD_IDS["Mega Gengar ex"],
    CARD_IDS["Toxel"],
    CARD_IDS["Toxtricity"],
    CARD_IDS["Fezandipiti ex"],
    CARD_IDS["Pecharunt ex"],
}


@dataclass(frozen=True)
class SetupAction:
    should_act: bool
    option_index: Optional[int] = None
    score: float = 0.0
    reason: str = ""


def emergency_setup_needed(state: Any) -> bool:
    return bench_space(state) > 0 and len(bench_pokemon(state)) <= 1 and not basic_in_hand(state) and not fezandipiti_draw_legal(state)


def basic_in_hand(state: Any) -> bool:
    return any(card_id_from_hand_card(card) in SETUP_BASIC_IDS for card in hand_cards(state))


def card_id_from_hand_card(card: Any) -> Optional[int]:
    try:
        from state_eval import card_id

        return card_id(card)
    except Exception:
        return None


def call_for_family_bridge_needed(state: Any, require_no_basic_in_hand: bool = True) -> bool:
    if bench_space(state) <= 0:
        return False
    if len(bench_pokemon(state)) > 1:
        return False
    if count_in_play(state, "Deino") < 1:
        return False
    if has_in_play(state, "Toxel") or has_in_play(state, "Toxtricity"):
        return False
    if has_in_hand(state, "Haunter") and has_in_hand(state, "Mega Gengar ex") and not has_in_play(state, "Gastly"):
        return False
    if require_no_basic_in_hand and basic_in_hand(state):
        return False
    return True


def setup_action_now(state: Any, options: Sequence[Any] | None = None) -> SetupAction:
    legal_options = list(options or getattr(state, "options", []) or [])
    if not emergency_setup_needed(state) or stronger_board_action_legal(state, legal_options):
        return SetupAction(False, reason="Bench is not in emergency setup state.")

    best_idx: Optional[int] = None
    best_score = 0.0
    best_name = ""
    for idx, option in enumerate(legal_options):
        if option_type(option) != OPT_PLAY:
            continue
        name = canonical_name_from_id(card_id_from_option(state, option))
        if name == "Lillie's Determination":
            try:
                from core.lillie_guard import useful_action_before_lillie

                if useful_action_before_lillie(state).should_wait:
                    continue
            except Exception:
                pass
        score = emergency_setup_option_score(state, name)
        if score > best_score:
            best_idx = idx
            best_score = score
            best_name = name
    if best_idx is None:
        return SetupAction(False, reason="No emergency setup card is legal.")
    return SetupAction(True, best_idx, best_score, f"Emergency setup: use {best_name} to find Bench basics/Poffin.")


def score_emergency_setup_play(state: Any, option: Any) -> float:
    if not emergency_setup_needed(state) or stronger_board_action_legal(state, getattr(state, "options", []) or []) or option_type(option) != OPT_PLAY:
        return 0.0
    name = canonical_name_from_id(card_id_from_option(state, option))
    action = setup_action_now(state, getattr(state, "options", []))
    if action.should_act and action.option_index is not None:
        try:
            if getattr(state, "options", [])[action.option_index] is option:
                return action.score
        except Exception:
            pass
    return max(0.0, emergency_setup_option_score(state, name) - 2000.0)


def emergency_setup_option_score(state: Any, name: str) -> float:
    supporter_used = bool(getv(state.current, "supporterPlayed", False))
    if name in {"Lillie's Determination", "Dawn", "Team Rocket's Petrel"} and supporter_used:
        return 0.0
    if name == "Lillie's Determination" and deck_count(state) <= 3:
        return 0.0
    if name == "Secret Box":
        try:
            from core.discard_cost_guard import score_discard_cost_play_safety

            if score_discard_cost_play_safety(state, "Secret Box", 3) <= -4500.0:
                return 0.0
        except Exception:
            pass
    try:
        from core.prize_availability_tracker import infer_card_availability
        from core.recovery_goal_planner import recovery_card_legal

        if infer_card_availability(state, None).all_deino_in_discard:
            if name == "Night Stretcher":
                return 10200.0
            if name == "Sacred Ash":
                return 10000.0
            if name == "Lillie's Determination" and recovery_card_legal(state):
                return 0.0
    except Exception:
        pass
    try:
        from core.fezandipiti_planner import score_pre_ko_fezandipiti_enabler

        pre_ko_fez_score = score_pre_ko_fezandipiti_enabler(state, name)
        if pre_ko_fez_score and name == "Ultra Ball":
            return 9600.0
        if pre_ko_fez_score and name == "Dawn":
            return 9200.0
    except Exception:
        pass
    return {
        "Buddy-Buddy Poffin": 9800.0,
        "Lillie's Determination": 9600.0,
        "Secret Box": 9000.0,
        "Team Rocket's Petrel": 8600.0,
        "Poke Pad": 8200.0,
        "Dawn": 7600.0,
        "Ultra Ball": 6400.0,
    }.get(name, 0.0)


def stronger_board_action_legal(state: Any, options: Sequence[Any]) -> bool:
    for idx, option in enumerate(options):
        action = classify_legal_option(state, option, idx)
        if action.category in (ActionCategory.EVOLVE, ActionCategory.RARE_CANDY_EVOLVE):
            return True
        if action.category == ActionCategory.USE_ABILITY:
            text = (action.card_name + " " + action.option_text).lower()
            if any(term in text for term in ("draw", "search your deck", "attach")):
                return True
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


def whole_team_missing_count(state: Any) -> int:
    return sum(1 for cid in CORE_TEAM_IDS if count_in_play(state, cid) == 0 and not has_in_hand(state, cid))


def whole_team_setup_score(state: Any, cid: Optional[int]) -> float:
    name = canonical_name_from_id(cid)
    if not name:
        return 0.0
    has_deino = count_in_play(state, "Deino") >= 1
    has_gastly = has_in_play(state, "Gastly")
    has_toxel = has_in_play(state, "Toxel") or has_in_play(state, "Toxtricity")
    hydreigon_ready = has_in_play(state, "Hydreigon ex")
    bench_count = len(bench_pokemon(state))
    bridge_needed = call_for_family_bridge_needed(state)
    if name == "Deino":
        if not has_deino:
            return 6600.0
        if bridge_needed:
            return 700.0
        if not (has_gastly and has_toxel):
            return 1600.0
        return 3000.0 if count_in_play(state, "Deino") < 2 else 1500.0
    if name == "Gastly":
        return 6400.0 if not has_gastly else 1300.0
    if name == "Toxel":
        if bridge_needed:
            return 8800.0
        return 6300.0 if not has_toxel else 1200.0
    if name == "Fezandipiti ex":
        return 5400.0 if not has_in_play(state, "Fezandipiti ex") else 900.0
    if name == "Pecharunt ex":
        return 5000.0 if not has_in_play(state, "Pecharunt ex") else 800.0
    if name == "Toxtricity":
        return 5200.0 if has_in_play(state, "Toxel") and not has_in_play(state, "Toxtricity") else 1200.0
    if name == "Haunter":
        return 5000.0 if has_in_play(state, "Gastly") and not has_in_play(state, "Haunter") else 1100.0
    if name == "Rare Candy":
        if has_deino and has_in_hand(state, "Hydreigon ex") and not hydreigon_ready:
            return 12500.0
        if has_deino and not hydreigon_ready and bench_count >= 2:
            return 7600.0
        if has_deino and not hydreigon_ready:
            return 5200.0
        return 800.0
    if name == "Hydreigon ex":
        if (has_in_play(state, "Zweilous") or has_in_hand(state, "Rare Candy")) and not hydreigon_ready:
            return 8200.0
        return 5600.0 if has_deino and not hydreigon_ready else 1000.0
    if name == "Mega Gengar ex":
        if has_in_play(state, "Haunter") and not has_in_play(state, "Mega Gengar ex"):
            return 8800.0
        return 6500.0 if has_in_play(state, "Gastly") and not has_in_play(state, "Mega Gengar ex") else 900.0
    if name == "Buddy-Buddy Poffin":
        return poffin_trainer_target_score(state)
    if name == "Ultra Ball":
        if has_deino and not hydreigon_ready and bench_count >= 2:
            return 6500.0
        return 4200.0
    if name in {"Poke Pad", "Dawn"}:
        return 4200.0
    return 0.0


def core_setup_basics_established(state: Any) -> bool:
    return (
        count_in_play(state, "Deino") >= 1
        and has_in_play(state, "Gastly")
        and (has_in_play(state, "Toxel") or has_in_play(state, "Toxtricity"))
    )


def poffin_trainer_target_score(state: Any) -> float:
    if bench_space(state) <= 0:
        return -3000.0
    bench_count = len(bench_pokemon(state))
    if emergency_setup_needed(state):
        return 9000.0
    if bench_count <= 1:
        return 7600.0
    if not core_setup_basics_established(state):
        return 5600.0 if bench_count <= 2 else 2600.0
    if count_in_play(state, "Deino") < 2 and bench_count <= 3:
        return 3000.0
    if bench_count >= 3:
        return -900.0
    return 1200.0


def weak_board_ignores_prize_liability(state: Any) -> bool:
    return len(bench_pokemon(state)) <= 1


def fezandipiti_draw_legal(state: Any) -> bool:
    try:
        from core.danger_evaluator import our_pokemon_knocked_out_last_turn

        if not our_pokemon_knocked_out_last_turn(state):
            return False
        for idx, option in enumerate(getattr(state, "options", []) or []):
            action = classify_legal_option(state, option, idx)
            if action.category == ActionCategory.USE_ABILITY and (action.card_id == CARD_IDS["Fezandipiti ex"] or action.card_name == "Fezandipiti ex"):
                return True
    except Exception:
        return False
    return False
