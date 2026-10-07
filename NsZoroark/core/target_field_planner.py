from __future__ import annotations

from typing import Any, Optional

from card_db import get_db
from state_eval import OPT_CARD, OPT_EVOLVE, OPT_PLAY, bench_pokemon, bench_space, card_id_from_option, option_type, prize_count
from core.deck_operating_system import compute_deck_goal_state
from core.priority_tables import canonical_name_from_id, count_in_play, context_source_name, has_in_hand, has_in_play


TARGET_WEIGHTS = {
    "Deino": 7600.0,
    "Gastly": 7000.0,
    "Toxel": 6500.0,
    "Zweilous": 4200.0,
    "Haunter": 4300.0,
    "Toxtricity": 4200.0,
    "Hydreigon ex": 8200.0,
    "Mega Gengar ex": 7800.0,
    "Rare Candy": 7600.0,
    "Fezandipiti ex": 5000.0,
    "Pecharunt ex": 4200.0,
}


def score_target_field_option(state: Any, option: Any) -> float:
    cid = card_id_from_option(state, option)
    name = canonical_name_from_id(cid)
    if not name:
        return 0.0
    typ = option_type(option)
    if typ == OPT_PLAY:
        return score_play_toward_target_field(state, name)
    if typ == OPT_EVOLVE:
        return score_evolve_toward_target_field(state, name)
    if typ == OPT_CARD:
        return score_search_target_toward_field(state, cid, name)
    return 0.0


def score_play_toward_target_field(state: Any, name: str) -> float:
    card = get_db().get_card_id if False else None
    del card
    goal = compute_deck_goal_state(state)
    if goal.target_board_complete:
        return 0.0
    if name == "Buddy-Buddy Poffin" and bench_space(state) > 0 and missing_poffin_basic_targets(state):
        return 7200.0
    if name in {"Poke Pad", "Ultra Ball", "Dawn", "Team Rocket's Petrel", "Secret Box"} and not goal.target_board_complete:
        return min(5200.0, goal.setup_urgency)
    if name == "Rare Candy" and rare_candy_is_target_field_evolve(state):
        return 9000.0
    return piece_score(state, name, source="play")


def score_evolve_toward_target_field(state: Any, name: str) -> float:
    if name == "Hydreigon ex":
        return 1600.0 if count_in_play(state, "Hydreigon ex") < 2 else 200.0
    if name == "Mega Gengar ex":
        return 1500.0 if not has_in_play(state, "Mega Gengar ex") else 200.0
    if name == "Toxtricity":
        return 1200.0 if not has_in_play(state, "Toxtricity") else 100.0
    if name in {"Zweilous", "Haunter"}:
        return 4200.0
    return 0.0


def score_search_target_toward_field(state: Any, cid: Optional[int], name: str) -> float:
    source = context_source_name(state)
    if source == "Poke Pad":
        return 0.0
    if source == "Buddy-Buddy Poffin":
        return piece_score(state, name, source="poffin")
    if source in {"Poke Pad", "Ultra Ball", "Dawn", "Team Rocket's Petrel", "Secret Box", "Toxel"}:
        return piece_score(state, name, source=source)
    return 0.0


def piece_score(state: Any, name: str, source: str = "") -> float:
    goal = compute_deck_goal_state(state)
    score = 0.0
    if name == "Deino":
        if count_in_play(state, "Deino") == 0:
            score = TARGET_WEIGHTS[name]
        elif count_in_play(state, "Deino") == 1:
            score = 6200.0
        else:
            score = 900.0
    elif name == "Gastly":
        score = TARGET_WEIGHTS[name] if goal.gengar_chains_current == 0 else 900.0
    elif name == "Toxel":
        score = TARGET_WEIGHTS[name] if goal.toxtricity_chains_current == 0 else 800.0
    elif name == "Fezandipiti ex":
        if support_ex_final_prize_liability(state):
            return -5000.0
        score = 6500.0 if should_setup_fezandipiti(state) else (TARGET_WEIGHTS[name] if not goal.has_fezandipiti_ex and goal.open_bench_slots > 0 else 500.0)
    elif name == "Pecharunt ex":
        if support_ex_final_prize_liability(state):
            return -5000.0
        score = 5800.0 if should_setup_pecharunt(state) else (TARGET_WEIGHTS[name] if not goal.has_pecharunt_ex and goal.open_bench_slots > 0 else 400.0)
    elif name == "Hydreigon ex":
        score = TARGET_WEIGHTS[name] if count_in_play(state, "Hydreigon ex") < 2 and (has_in_hand(state, "Rare Candy") or has_in_play(state, "Zweilous") or source == "Dawn") else 1800.0
    elif name == "Mega Gengar ex":
        score = TARGET_WEIGHTS[name] if not has_in_play(state, "Mega Gengar ex") and (has_in_play(state, "Haunter") or source == "Dawn") else 1600.0
    elif name in TARGET_WEIGHTS:
        score = TARGET_WEIGHTS[name]
    if name == goal.next_best_setup_piece:
        score += 1600.0
    return score


def missing_poffin_basic_targets(state: Any) -> bool:
    goal = compute_deck_goal_state(state)
    return bench_space(state) > 0 and bool(set(goal.missing_core_pieces) & {"Deino", "Gastly", "Toxel"})


def rare_candy_is_target_field_evolve(state: Any) -> bool:
    return has_in_play(state, "Deino") and has_in_hand(state, "Hydreigon ex") and count_in_play(state, "Hydreigon ex") < 2


def should_setup_fezandipiti(state: Any) -> bool:
    try:
        from core.danger_evaluator import our_pokemon_knocked_out_last_turn

        if our_pokemon_knocked_out_last_turn(state):
            return True
    except Exception:
        pass
    return len(getattr(state, "options", []) or []) > 0 and bench_space(state) > 0 and count_in_play(state, "Deino") >= 1


def should_setup_pecharunt(state: Any) -> bool:
    try:
        from core.pivot_planner import active_is_stuck_or_exposed, darkness_attacker_on_bench

        return bench_space(state) > 0 and (active_is_stuck_or_exposed(state) or darkness_attacker_on_bench(state))
    except Exception:
        return bench_space(state) > 0 and count_in_play(state, "Deino") >= 1 and has_in_play(state, "Gastly")


def support_ex_final_prize_liability(state: Any) -> bool:
    return prize_count(state, state.opponent_index) <= 2 and len(bench_pokemon(state)) >= 2
