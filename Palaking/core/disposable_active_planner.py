from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from action_classifier import ActionCategory, classify_legal_option
from state_eval import (
    AREA_ACTIVE,
    AREA_BENCH,
    OPT_ATTACH,
    OPT_PLAY,
    active_pokemon,
    attach_target_from_option,
    bench_pokemon,
    bench_space,
    card_id,
    card_id_from_option,
    getv,
    option_type,
    pokemon_energy_count,
)
from core.danger_evaluator import evaluate_danger
from core.opponent_model import OpponentThreat, infer_opponent_next_turn_threat
from core.priority_tables import CARD_IDS, HYDREIGON_LINE_IDS, canonical_name_from_id, has_in_hand, has_in_play


@dataclass(frozen=True)
class DisposableActiveReport:
    is_disposable: bool
    active_id: Optional[int]
    active_name: str
    reason: str
    benched_deino_index: Optional[int] = None
    fezandipiti_ready: bool = False
    opponent_can_ko: bool = False


def identify_disposable_active(state: Any, opponent_model: Optional[OpponentThreat] = None) -> DisposableActiveReport:
    active = active_pokemon(state)
    active_id = card_id(active)
    active_name = canonical_name_from_id(active_id)
    threat = opponent_model or infer_opponent_next_turn_threat(state)
    danger = evaluate_danger(state)
    opponent_can_ko = bool(threat.can_take_active_ko or danger.active_can_be_koed)
    benched_deino = first_benched_deino_index(state)
    low_resource = pokemon_energy_count(active) <= 1
    main_attacker = active_name in {"Hydreigon ex", "Mega Gengar ex"}
    fez_ready = has_in_play(state, "Fezandipiti ex") or has_in_hand(state, "Fezandipiti ex") or bench_space(state) > 0

    disposable = bool(
        active_id == CARD_IDS["Deino"]
        and opponent_can_ko
        and low_resource
        and not main_attacker
        and not active_basic_has_complete_chain_in_hand(state)
        and benched_deino is not None
        and fez_ready
    )
    reason = (
        "Active Deino is disposable; attach Energy to Benched Deino."
        if disposable
        else "Active is not a disposable setup Pokemon."
    )
    return DisposableActiveReport(disposable, active_id, active_name, reason, benched_deino, fez_ready, opponent_can_ko)


def score_disposable_active_option(state: Any, option: Any) -> float:
    report = identify_disposable_active(state)
    if not report.is_disposable:
        return 0.0

    typ = option_type(option)
    cid = card_id_from_option(state, option)
    if typ == OPT_ATTACH:
        target = attach_target_from_option(state, option)
        target_id = card_id(target)
        target_area = int(getv(option, "inPlayArea", -1) or -1)
        if target_id in HYDREIGON_LINE_IDS and target_area == AREA_BENCH:
            return 3000.0
        if target_id == report.active_id and target_area == AREA_ACTIVE:
            return -2500.0
    if typ == OPT_PLAY:
        action = classify_legal_option(state, option, 0)
        if action.category == ActionCategory.PLAY_SUPPORTER and obvious_setup_action_exists(state):
            return -2000.0
        name = canonical_name_from_id(cid)
        if name == "Ultra Ball" and not has_in_play(state, "Fezandipiti ex"):
            return 3600.0
        if name == "Fezandipiti ex" and not late_boss_risk_loses_game(state):
            return 3200.0
    return 0.0


def first_benched_deino_index(state: Any) -> Optional[int]:
    for idx, pokemon in enumerate(bench_pokemon(state)):
        if card_id(pokemon) == CARD_IDS["Deino"]:
            return idx
    return None


def active_basic_has_complete_chain_in_hand(state: Any) -> bool:
    active_id = card_id(active_pokemon(state))
    if active_id == CARD_IDS["Deino"]:
        return has_in_hand(state, "Zweilous") and has_in_hand(state, "Hydreigon ex")
    if active_id == CARD_IDS["Gastly"]:
        return has_in_hand(state, "Haunter") and has_in_hand(state, "Mega Gengar ex")
    return False


def obvious_setup_action_exists(state: Any) -> bool:
    for idx, option in enumerate(getattr(state, "options", []) or []):
        action = classify_legal_option(state, option, idx)
        name = action.card_name or canonical_name_from_id(card_id_from_option(state, option))
        if action.category in (ActionCategory.PLAY_BASIC_TO_BENCH, ActionCategory.DRAW_OR_SEARCH, ActionCategory.EVOLVE, ActionCategory.RARE_CANDY_EVOLVE):
            return True
        if name in {"Poke Pad", "Poké Pad", "Buddy-Buddy Poffin", "Ultra Ball", "Secret Box"}:
            return True
    return False


def late_boss_risk_loses_game(state: Any) -> bool:
    return evaluate_danger(state).opponent_can_take_final_prizes
