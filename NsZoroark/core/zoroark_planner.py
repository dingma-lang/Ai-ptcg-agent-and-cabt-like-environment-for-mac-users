from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

from action_classifier import ActionCategory, classify_legal_option
from state_eval import (
    CTX_ATTACH_FROM,
    CTX_ATTACH_TO,
    CTX_SWITCH,
    CTX_TO_ACTIVE,
    OPT_ABILITY,
    OPT_ATTACH,
    OPT_ATTACK,
    OPT_END,
    OPT_EVOLVE,
    OPT_PLAY,
    active_pokemon,
    attach_target_from_option,
    card_id,
    card_id_from_option,
    option_type,
    pokemon_energy_count,
    pokemon_from_card_option,
)
from core.copy_target_planner import zoroark_has_copy_source
from core.energy_planner_zoroark import score_attach_target_zoroark, score_energy_option_zoroark
from core.night_joker_planner import evaluate_night_joker_options, score_night_joker_option
from core.pecharunt_planner import score_pecharunt_option, score_pecharunt_switch_target
from core.poison_mochi_planner import score_mochi_target_zoroark, score_poison_mochi_option
from core.priority_tables import canonical_name, canonical_name_from_id
from core.recovery_planner_zoroark import score_recovery_option_zoroark
from core.search_planner_zoroark import (
    best_basic_bench_from_hand_zoroark,
    score_discard_selection_zoroark,
    score_search_option_zoroark,
    score_search_selection_zoroark,
    score_setup_basic_play_zoroark,
    should_use_poffin_zoroark,
)
from core.supporter_router_zoroark import choose_best_supporter_zoroark, score_supporter_option_zoroark
from core.target_board import RESHIRAM, ZEKROM, ZOROARK_EX, ZORUA, evaluate_target_board, pokemon_name
from core.trade_planner import score_trade_option
from core.transformation_tome_planner import score_transformation_tome_option


@dataclass(frozen=True)
class ZoroarkPlan:
    should_act: bool
    option_index: Optional[int] = None
    score: float = 0.0
    reason: str = ""


def score_zoroark_plan(state: Any, legal_options: Sequence[Any]) -> ZoroarkPlan:
    best = choose_zoroark_priority_action(state, legal_options, [0.0] * len(legal_options))
    if best is None:
        return ZoroarkPlan(False, reason="No forced N's Zoroark action.")
    return ZoroarkPlan(True, best, 0.0, "N's Zoroark priority action.")


def choose_zoroark_priority_action(state: Any, legal_options: Sequence[Any], scores: Sequence[float]) -> Optional[int]:
    night = evaluate_night_joker_options(state, legal_options)
    if night.should_attack and night.option_index is not None and night.score >= 10000.0:
        return night.option_index

    basic_idx = best_basic_bench_from_hand_zoroark(state, legal_options)
    if basic_idx is not None:
        return basic_idx

    poffin = should_use_poffin_zoroark(state, legal_options)
    if poffin.should_act and poffin.option_index is not None and poffin.score >= 4200.0:
        return poffin.option_index

    evolution = best_zoroark_evolution_index(state, legal_options, scores)
    if evolution is not None:
        return evolution

    energy = best_zoroark_energy_index(state, legal_options, scores)
    if energy is not None:
        return energy

    copy_source = best_copy_source_setup_index(state, legal_options)
    if copy_source is not None:
        return copy_source

    trade = best_trade_index(state, legal_options)
    if trade is not None:
        return trade

    search = best_zoroark_search_index(state, legal_options)
    if search is not None:
        return search

    supporter = choose_best_supporter_zoroark(state, legal_options)
    if supporter.should_use and supporter.option_index is not None and supporter.score >= 2800.0:
        return supporter.option_index

    if night.should_attack and night.option_index is not None and night.score >= 2500.0:
        return night.option_index
    return None


def score_zoroark_option(state: Any, option: Any, current_score: float = 0.0, option_index: int = 0) -> float:
    del current_score
    typ = option_type(option)
    cid = card_id_from_option(state, option)
    name = canonical_name_from_id(cid)
    bonus = 0.0
    if typ == OPT_PLAY:
        bonus += score_setup_basic_play_zoroark(state, option)
        bonus += score_search_option_zoroark(state, option)
        bonus += score_supporter_option_zoroark(state, option)
        bonus += score_recovery_option_zoroark(state, option)
        bonus += score_poison_mochi_option(state, option)
        bonus += score_transformation_tome_option(state, option)
        if name == "N's Castle":
            bonus += 1800.0
    elif typ == OPT_EVOLVE:
        bonus += score_zoroark_evolve_option(state, option)
    elif typ == OPT_ATTACH:
        bonus += score_energy_option_zoroark(state, option)
    elif typ == OPT_ABILITY:
        bonus += score_trade_option(state, option)
        bonus += score_pecharunt_option(state, option)
    elif typ == OPT_ATTACK:
        if pokemon_name(active_pokemon(state)) != ZOROARK_EX:
            bonus -= 9500.0
        else:
            bonus += score_night_joker_option(state, option, option_index)
    elif typ == OPT_END:
        bonus += zoroark_end_turn_penalty(state, [])
    return bonus


def score_zoroark_evolve_option(state: Any, option: Any) -> float:
    name = canonical_name_from_id(card_id_from_option(state, option))
    target = attach_target_from_option(state, option)
    if target is None:
        from state_eval import get_pokemon_by_area, getv

        target = get_pokemon_by_area(state, getv(option, "inPlayArea"), getv(option, "inPlayIndex"), state.your_index)
    target_name = pokemon_name(target)
    if name == ZOROARK_EX and target_name == ZORUA:
        energy = pokemon_energy_count(target)
        score = 7000.0 + energy * 450.0
        report = evaluate_target_board(state)
        if report.zoroark_ex_count == 0:
            score += 1500.0
        return score
    if name == "N's Darmanitan":
        return 3200.0 if target_name == "N's Darumaka" else 0.0
    return 0.0


def best_zoroark_evolution_index(state: Any, legal_options: Sequence[Any], scores: Sequence[float]) -> Optional[int]:
    best_idx = None
    best_score = 0.0
    for idx, option in enumerate(legal_options):
        if option_type(option) != OPT_EVOLVE:
            continue
        score = score_zoroark_evolve_option(state, option) + (scores[idx] if idx < len(scores) else 0.0) * 0.05
        if score > best_score:
            best_idx = idx
            best_score = score
    return best_idx if best_score >= 2500.0 else None


def best_zoroark_energy_index(state: Any, legal_options: Sequence[Any], scores: Sequence[float]) -> Optional[int]:
    best_idx = None
    best_score = 0.0
    for idx, option in enumerate(legal_options):
        if option_type(option) not in (OPT_ATTACH, OPT_PLAY):
            continue
        score = score_energy_option_zoroark(state, option) + (scores[idx] if idx < len(scores) else 0.0) * 0.05
        if score > best_score:
            best_idx = idx
            best_score = score
    return best_idx if best_score >= 4500.0 else None


def best_copy_source_setup_index(state: Any, legal_options: Sequence[Any]) -> Optional[int]:
    if zoroark_has_copy_source(state):
        return None
    best_idx = None
    best_score = 0.0
    for idx, option in enumerate(legal_options):
        if option_type(option) != OPT_PLAY:
            continue
        name = canonical_name_from_id(card_id_from_option(state, option))
        score = 0.0
        if name == ZEKROM:
            score = 6500.0
        elif name == RESHIRAM:
            score = 5600.0
        elif name == "N's Darumaka":
            score = 3600.0
        if score > best_score:
            best_idx = idx
            best_score = score
    return best_idx if best_score >= 3000.0 else None


def best_trade_index(state: Any, legal_options: Sequence[Any]) -> Optional[int]:
    best_idx = None
    best_score = 0.0
    for idx, option in enumerate(legal_options):
        score = score_trade_option(state, option)
        if score > best_score:
            best_idx = idx
            best_score = score
    return best_idx if best_score >= 3000.0 else None


def best_zoroark_search_index(state: Any, legal_options: Sequence[Any]) -> Optional[int]:
    best_idx = None
    best_score = 0.0
    for idx, option in enumerate(legal_options):
        score = score_search_option_zoroark(state, option)
        if score > best_score:
            best_idx = idx
            best_score = score
    return best_idx if best_score >= 3200.0 else None


def zoroark_useful_action_exists(state: Any, scores: Sequence[float]) -> bool:
    for idx, option in enumerate(getattr(state, "options", []) or []):
        if option_type(option) == OPT_END:
            continue
        if idx < len(scores) and scores[idx] >= 1200.0:
            return True
        if score_zoroark_option(state, option, 0.0, idx) >= 1200.0:
            return True
    return False


def zoroark_end_turn_penalty(state: Any, scores: Sequence[float]) -> float:
    if zoroark_useful_action_exists(state, scores):
        return -7000.0
    return 150.0


def ready_zoroark_on_board(state: Any) -> bool:
    try:
        from core.target_board import ready_zoroarks

        return bool(ready_zoroarks(state))
    except Exception:
        return False


def score_zoroark_selection(state: Any, option: Any, context: int) -> float:
    cid = card_id_from_option(state, option)
    if context in {CTX_ATTACH_FROM, CTX_ATTACH_TO}:
        return score_attach_target_zoroark(state, pokemon_from_card_option(state, option))
    if context in {CTX_SWITCH, CTX_TO_ACTIVE}:
        pokemon = pokemon_from_card_option(state, option)
        return max(score_pecharunt_switch_target(state, pokemon), 3600.0 if pokemon_name(pokemon) == ZOROARK_EX and pokemon_energy_count(pokemon) >= 2 else 0.0)
    return score_search_selection_zoroark(state, option, cid=cid)
