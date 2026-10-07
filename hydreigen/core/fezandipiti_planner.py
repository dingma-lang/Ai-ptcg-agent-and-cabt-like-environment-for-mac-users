from __future__ import annotations

from typing import Any

from action_classifier import ActionCategory, classify_legal_option
from card_db import get_db
from state_eval import OPT_ABILITY, OPT_ATTACK, OPT_CARD, OPT_ENERGY, OPT_ENERGY_CARD, OPT_PLAY, OPT_TOOL_CARD, active_pokemon, bench_pokemon, bench_space, card_id, card_id_from_option, getv, hand_count, option_type, prize_count
from core.danger_evaluator import our_pokemon_knocked_out_last_turn
from core.disposable_active_planner import identify_disposable_active
from core.priority_tables import CARD_IDS, canonical_name_from_id, context_source_name, count_in_play, deino_count, has_in_hand
from core.supporter_planner import hand_playability_score


FEZANDIPITI_EX_ID = CARD_IDS["Fezandipiti ex"]


def score_fezandipiti_option(state: Any, option: Any) -> float:
    cid = card_id_from_option(state, option)
    typ = option_type(option)
    if typ == OPT_ATTACK:
        return score_fezandipiti_attack_enabler(state, option)
    if cid != FEZANDIPITI_EX_ID:
        return 0.0

    if typ == OPT_ABILITY:
        return score_fezandipiti_ability(state)
    if typ == OPT_PLAY:
        return score_fezandipiti_bench(state)
    if typ in (OPT_CARD, OPT_TOOL_CARD, OPT_ENERGY_CARD, OPT_ENERGY):
        return score_fezandipiti_search_target(state)
    return 0.0


def score_fezandipiti_ability(state: Any) -> float:
    if not our_pokemon_knocked_out_last_turn(state):
        return 850.0
    return 7800.0 if hand_is_weak(state) else 7000.0


def score_fezandipiti_bench(state: Any) -> float:
    if bench_space(state) <= 0:
        return -5000.0
    if count_in_play(state, "Fezandipiti ex") > 0:
        return -1200.0
    try:
        from core.setup_recovery_planner import weak_board_ignores_prize_liability

        if weak_board_ignores_prize_liability(state):
            return 6200.0
    except Exception:
        pass
    if our_pokemon_knocked_out_last_turn(state):
        return 6900.0
    if pre_ko_fezandipiti_needed(state):
        return 3200.0
    if late_final_prize_liability(state) and not recovery_is_necessary(state):
        return -4200.0
    if early_no_bench_loss_risk(state) and not safer_basic_option_available(state):
        return 3600.0
    return -650.0


def score_fezandipiti_search_target(state: Any) -> float:
    source = context_source_name(state)
    allowed_sources = {"Ultra Ball", "Secret Box", "Dawn", "Toxel"}
    if source and source not in allowed_sources:
        return 0.0
    if bench_space(state) <= 0:
        return -3000.0
    if count_in_play(state, "Fezandipiti ex") > 0:
        return -1200.0
    try:
        from core.setup_recovery_planner import emergency_setup_needed, weak_board_ignores_prize_liability

        if emergency_setup_needed(state) and source in {"Dawn", "Ultra Ball"}:
            return 9000.0 if source == "Dawn" else 6400.0
        if weak_board_ignores_prize_liability(state) and source in {"Dawn", "Ultra Ball"}:
            return 5600.0
    except Exception:
        pass
    if our_pokemon_knocked_out_last_turn(state):
        if source == "Dawn":
            return 7600.0
        if source == "Ultra Ball":
            return 7400.0
        if source == "Toxel":
            return 7300.0
        return 7000.0
    if pre_ko_fezandipiti_needed(state):
        if source == "Ultra Ball":
            return 3600.0
        if source == "Dawn":
            return 3300.0
        if source == "Toxel":
            return 3100.0
        return 2800.0
    if late_final_prize_liability(state) and not recovery_is_necessary(state):
        return -1800.0
    if early_no_bench_loss_risk(state) and not safer_basic_option_available(state):
        return 900.0
    return -450.0


def score_post_ko_fezandipiti_enabler(state: Any, card_name: str) -> float:
    if not needs_post_ko_fezandipiti(state):
        return 0.0
    if card_name == "Dawn":
        return 6400.0
    if card_name == "Ultra Ball":
        return 6200.0
    if card_name == "Toxel":
        return 5600.0
    return 0.0


def score_pre_ko_fezandipiti_enabler(state: Any, card_name: str) -> float:
    if not pre_ko_fezandipiti_needed(state):
        return 0.0
    if card_name == "Ultra Ball":
        return 3600.0
    if card_name == "Dawn":
        return 3200.0
    if card_name == "Toxel":
        return 3000.0
    return 0.0


def score_fezandipiti_attack_enabler(state: Any, option: Any) -> float:
    active = active_pokemon(state)
    active_name = canonical_name_from_id(card_id(active))
    attack = get_db().get_attack(getv(option, "attackId"))
    attack_name = str(getattr(attack, "name", "") or "")
    if active_name == "Fezandipiti ex" and "flip the script" in attack_name.lower():
        return score_fezandipiti_ability(state)
    if active_name == "Toxel" and "call for family" in attack_name.lower():
        return score_post_ko_fezandipiti_enabler(state, "Toxel")
    return 0.0


def needs_post_ko_fezandipiti(state: Any) -> bool:
    return (
        our_pokemon_knocked_out_last_turn(state)
        and bench_space(state) > 0
        and count_in_play(state, "Fezandipiti ex") == 0
        and not has_in_hand(state, "Fezandipiti ex")
    )


def pre_ko_fezandipiti_needed(state: Any) -> bool:
    if bench_space(state) <= 0 or count_in_play(state, "Fezandipiti ex") > 0:
        return False
    if late_final_prize_liability(state) and not recovery_is_necessary(state):
        return False
    report = identify_disposable_active(state)
    return bool(report.opponent_can_ko and (report.is_disposable or hand_is_weak(state)))


def fezandipiti_draw_available(state: Any) -> bool:
    if not our_pokemon_knocked_out_last_turn(state):
        return False
    for idx, option in enumerate(state.options):
        action = classify_legal_option(state, option, idx)
        if action.category == ActionCategory.USE_ABILITY and (action.card_id == FEZANDIPITI_EX_ID or "fezandipiti" in action.card_name.lower()):
            return True
    return False


def fezandipiti_recovery_available(state: Any) -> bool:
    if fezandipiti_draw_available(state):
        return True
    for option in state.options:
        if card_id_from_option(state, option) == FEZANDIPITI_EX_ID and score_fezandipiti_option(state, option) > 500.0:
            return True
    return False


def hand_is_weak(state: Any) -> bool:
    return hand_count(state) <= 4 or hand_playability_score(state) < 180.0


def early_no_bench_loss_risk(state: Any) -> bool:
    turn = int(getv(state.current, "turn", 0) or 0)
    return turn <= 5 and len(bench_pokemon(state)) == 0


def safer_basic_option_available(state: Any) -> bool:
    for idx, option in enumerate(state.options):
        action = classify_legal_option(state, option, idx)
        if action.card_id in {227, 59, 833}:
            return True
    return False


def late_final_prize_liability(state: Any) -> bool:
    try:
        from core.setup_recovery_planner import weak_board_ignores_prize_liability

        if weak_board_ignores_prize_liability(state):
            return False
    except Exception:
        pass
    return prize_count(state, state.opponent_index) <= 2


def recovery_is_necessary(state: Any) -> bool:
    return our_pokemon_knocked_out_last_turn(state) and (hand_count(state) <= 2 or deino_count(state) == 0)
