from __future__ import annotations

from typing import Any

from state_eval import OPT_ATTACH, OPT_CARD, OPT_PLAY, attach_target_from_option, card_id, card_id_from_option, count_card_in_discard, getv, option_type
from core.danger_evaluator import our_pokemon_knocked_out_last_turn
from core.priority_tables import CARD_IDS, canonical_name_from_id
from core.prize_availability_tracker import infer_card_availability


def score_recovery_goal_option(state: Any, option: Any) -> float:
    try:
        from core.recovery_timing_planner import score_recovery_timing_option

        timing = score_recovery_timing_option(state, option)
        if timing <= -1000.0:
            return timing
        if timing >= 3000.0:
            return timing
    except Exception:
        pass
    report = infer_card_availability(state, None)
    urgent_all_deino = report.all_deino_in_discard
    rebuild_needed = urgent_all_deino or key_pokemon_recovery_needed(state)
    if not rebuild_needed:
        return 0.0
    name = canonical_name_from_id(card_id_from_option(state, option))
    typ = option_type(option)
    if typ == OPT_PLAY and name == "Night Stretcher":
        return 34000.0 if urgent_all_deino else (26000.0 if our_pokemon_knocked_out_last_turn(state) else 7200.0)
    if typ == OPT_PLAY and name == "Sacred Ash":
        return 32000.0 if urgent_all_deino else (30000.0 if our_pokemon_knocked_out_last_turn(state) else 7800.0)
    if typ == OPT_PLAY and name == "Lillie's Determination":
        return -2500.0 if recovery_card_legal(state) else 2600.0
    if typ == OPT_ATTACH:
        target_name = canonical_name_from_id(card_id(attach_target_from_option(state, option)))
        if target_name == "Mega Gengar ex":
            return 2800.0
    if typ == OPT_CARD:
        return recovery_card_selection_score(name)
    return 0.0


def recovery_card_legal(state: Any) -> bool:
    for option in getattr(state, "options", []) or []:
        if option_type(option) != OPT_PLAY:
            continue
        if canonical_name_from_id(card_id_from_option(state, option)) in {"Night Stretcher", "Sacred Ash"}:
            return True
    return False


def key_pokemon_recovery_needed(state: Any) -> bool:
    key_ids = (
        CARD_IDS["Deino"],
        CARD_IDS["Zweilous"],
        CARD_IDS["Hydreigon ex"],
        CARD_IDS["Gastly"],
        CARD_IDS["Haunter"],
        CARD_IDS["Mega Gengar ex"],
        CARD_IDS["Toxel"],
        CARD_IDS["Toxtricity"],
    )
    discarded = sum(count_card_in_discard(state, cid) for cid in key_ids)
    if discarded <= 0:
        return False
    if our_pokemon_knocked_out_last_turn(state):
        return True
    turn = int(getv(state.current, "turn", 0) or 0)
    return turn >= 5 and discarded >= 2


def recovery_card_selection_score(name: str) -> float:
    return {
        "Deino": 6200.0,
        "Zweilous": 6000.0,
        "Hydreigon ex": 6100.0,
        "Gastly": 5400.0,
        "Haunter": 5200.0,
        "Mega Gengar ex": 5600.0,
        "Toxel": 4500.0,
        "Toxtricity": 4300.0,
    }.get(name, 0.0)
