from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

from action_classifier import ActionCategory, classify_legal_option
from state_eval import OPT_PLAY, card_id_from_option, deck_count, getv, hand_count, option_type
from core.priority_tables import canonical_name, canonical_name_from_id, hand_ids, has_in_hand
from core.search_planner_zoroark import black_belt_math_needed, boss_line_needed, safe_discard_count_zoroark
from core.target_board import ZOROARK_EX, ZORUA, evaluate_target_board


@dataclass(frozen=True)
class SupporterDecision:
    should_use: bool
    option_index: Optional[int] = None
    supporter_name: str = ""
    score: float = 0.0
    reason: str = ""


def choose_best_supporter_zoroark(state: Any, legal_options: Sequence[Any]) -> SupporterDecision:
    if bool(getv(state.current, "supporterPlayed", False)):
        return SupporterDecision(False, reason="Supporter already used.")
    best = SupporterDecision(False, reason="No legal N's Zoroark Supporter.")
    for idx, option in enumerate(legal_options):
        action = classify_legal_option(state, option, idx)
        if action.category != ActionCategory.PLAY_SUPPORTER and option_type(option) != OPT_PLAY:
            continue
        name = canonical_name(action.card_name or canonical_name_from_id(card_id_from_option(state, option)))
        score, reason = score_supporter_name_zoroark(state, name)
        if score > best.score:
            best = SupporterDecision(score > 0.0, idx, name, score, reason)
    return best


def score_supporter_option_zoroark(state: Any, option: Any) -> float:
    if option_type(option) != OPT_PLAY:
        return 0.0
    name = canonical_name_from_id(card_id_from_option(state, option))
    score, _reason = score_supporter_name_zoroark(state, name)
    return score


def score_supporter_name_zoroark(state: Any, name: str) -> tuple[float, str]:
    report = evaluate_target_board(state)
    if name == "Boss's Orders":
        if boss_line_needed(state):
            return 9000.0, "Use Boss because it creates a Night Joker prize route."
        return -1200.0, "Hold Boss; no visible KO or prize-map target."
    if name == "Black Belt's Training":
        if black_belt_math_needed(state):
            return 8200.0, "Use Black Belt because +40 KOs an opponent Pokemon ex."
        return -1800.0, "Do not burn Black Belt unless +40 changes KO math."
    if name == "Cyrano":
        if report.zorua_count > report.zoroark_ex_count:
            return 7800.0, "Use Cyrano for N's Zoroark ex."
        if not report.has_pecharunt_ex and (boss_line_needed(state) or black_belt_math_needed(state)):
            return 3200.0, "Use Cyrano for Pecharunt ex only when damage math needs it."
        return 600.0, "Cyrano has low value after Zoroark ex pieces are found."
    if name == "Ciphermaniac's Codebreaking":
        return score_ciphermaniac_zoroark(state)
    if name == "Lillie's Determination":
        return score_lillie_zoroark(state)
    if name == "Ruffian":
        return 1800.0 if opponent_has_tool_or_special_energy(state) else -500.0, "Use Ruffian only if removal changes tempo."
    if name == "Special Red Card":
        opp_prizes = safe_prize_count(state, getattr(state, "opponent_index", 1))
        opp_hand = int(getv(getattr(state, "current", {}), "opponentHandCount", 0) or 0)
        if opp_prizes <= 3 or opp_hand >= 7:
            return 3000.0, "Use Special Red Card as late disruption."
        return -1300.0, "Avoid early disruption before setup is stable."
    return 0.0, "Unknown Supporter."


def score_ciphermaniac_zoroark(state: Any) -> tuple[float, str]:
    report = evaluate_target_board(state)
    try:
        from core.trade_planner import evaluate_trade

        trade_live = evaluate_trade(state).should_use
    except Exception:
        trade_live = False
    if trade_live and (report.zoroark_ex_count < 2 or report.ready_zoroark_count == 0 or not report.has_n_zekrom):
        return 6200.0, "Use Ciphermaniac because Trade can draw the exact stacked setup cards."
    if report.zoroark_ex_count < 2 or report.ready_zoroark_count == 0:
        return 2800.0, "Use Ciphermaniac to stack missing Zoroark/Energy pieces for the next draw."
    return 900.0, "Ciphermaniac is low priority when no draw conversion or exact setup need exists."


def score_lillie_zoroark(state: Any) -> tuple[float, str]:
    if deck_count(state) <= 3:
        return -9000.0, "Do not use Lillie because deck-out risk is too high."
    precheck = useful_action_before_lillie_zoroark(state)
    base = 0.0
    if hand_count(state) <= 2:
        base = 9200.0
    elif hand_count(state) <= 4:
        base = 7600.0
    elif too_many_zoroark_ex_in_hand(state):
        base = 6800.0
    elif not evaluate_target_board(state).ready_zoroark_count:
        base = 4200.0
    else:
        base = 1500.0
    if precheck:
        base -= 5200.0
        return base, f"Check useful action before Lillie: {precheck}"
    return base, "Use Lillie after bench/evolve/item/Energy checks when hand needs refresh."


def useful_action_before_lillie_zoroark(state: Any) -> str:
    for idx, option in enumerate(getattr(state, "options", []) or []):
        action = classify_legal_option(state, option, idx)
        name = canonical_name(action.card_name or canonical_name_from_id(card_id_from_option(state, option)))
        if name == "Lillie's Determination":
            continue
        if action.category in {ActionCategory.PLAY_BASIC_TO_BENCH, ActionCategory.EVOLVE, ActionCategory.RARE_CANDY_EVOLVE, ActionCategory.ATTACH_ENERGY}:
            return action.category
        if name in {"Buddy-Buddy Poffin", "Poke Pad", "N's PP Up", "Binding Mochi", "N's Castle", "Unfair Stamp", "Air Balloon", "Transformation Tome", "Tool Scrapper"}:
            return name
    return ""


def too_many_zoroark_ex_in_hand(state: Any) -> bool:
    return hand_ids(state).count(293) > 1


def opponent_has_tool_or_special_energy(state: Any) -> bool:
    text = " ".join(str(log) for log in (getv(state.obs, "logs", []) or [])[-12:]).lower()
    return "tool" in text or "special energy" in text


def safe_prize_count(state: Any, player_index: int) -> int:
    try:
        from state_eval import prize_count

        return prize_count(state, player_index)
    except Exception:
        return 6
