from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from state_eval import OPT_ABILITY, OPT_ATTACK, card_id_from_option, deck_count, getv, hand_cards, hand_count, option_type
from core.energy_planner_zoroark import darkness_in_discard
from core.priority_tables import canonical_name_from_id, context_source_name, count_in_play, hand_ids, has_in_hand
from core.target_board import DARKNESS_ENERGY_ID, ZEKROM, ZOROARK_EX, ZORUA


@dataclass(frozen=True)
class TradeDecision:
    should_use: bool
    score: float = 0.0
    reason: str = ""


def score_trade_option(state: Any, option: Any) -> float:
    if not is_trade_option(state, option):
        return 0.0
    decision = evaluate_trade(state)
    return decision.score if decision.should_use else decision.score


def evaluate_trade(state: Any) -> TradeDecision:
    if deck_count(state) <= 3:
        return TradeDecision(False, -9000.0, "Block Trade because deck-out risk is high.")
    safe = best_trade_discard_score(state)
    if safe < 0.0:
        return TradeDecision(False, -6000.0, "Block Trade because only protected cards can be discarded.")
    weak_hand = hand_count(state) <= 4
    if weak_hand:
        return TradeDecision(True, 3500.0 + safe, "Use Trade with safe discard because hand is weak.")
    if has_in_hand(state, DARKNESS_ENERGY_ID) and pp_up_line_benefits(state):
        return TradeDecision(True, 3000.0 + safe, "Use Trade to discard Darkness for N's PP Up acceleration.")
    if safe >= 900.0:
        return TradeDecision(True, 1800.0 + safe, "Use Trade because a low-value duplicate can be converted into 2 cards.")
    return TradeDecision(False, -500.0, "Hold Trade because hand is already functional.")


def score_trade_discard_selection(state: Any, cid: Optional[int]) -> float:
    name = canonical_name_from_id(cid)
    count = hand_ids(state).count(int(cid)) if cid is not None else 0
    if cid is None:
        return 0.0
    if name == "N's Castle" and count >= 2:
        return 1800.0
    if name == "Buddy-Buddy Poffin":
        return 1400.0 if count_in_play(state, ZORUA) >= 2 else -4500.0
    if name == "Lillie's Determination" and bool(getv(state.current, "supporterPlayed", False)):
        return 1200.0
    if name == "Boss's Orders" and count >= 2:
        return 800.0
    if cid == DARKNESS_ENERGY_ID:
        return 1300.0 if pp_up_line_benefits(state) else -1700.0
    if name == "Binding Mochi":
        return -2600.0
    if name in {"N's Zoroark ex", "N's Zorua", "N's Zekrom", "N's Reshiram"}:
        return -6000.0 if count <= 1 else -500.0
    if name == "Ciphermaniac's Codebreaking":
        return 900.0 if count >= 2 else -200.0
    if name == "Tool Scrapper":
        return 1000.0
    if name == "Team Rocket's Watchtower":
        return 1300.0
    if name == "Air Balloon":
        return -700.0 if count <= 1 else 650.0
    if name == "Unfair Stamp":
        return -3600.0
    if count >= 2:
        return 900.0
    return -100.0


def best_trade_discard_score(state: Any) -> float:
    scores = [score_trade_discard_selection(state, cid) for cid in hand_ids(state)]
    return max(scores, default=-9999.0)


def is_trade_option(state: Any, option: Any) -> bool:
    name = canonical_name_from_id(card_id_from_option(state, option))
    if name == ZOROARK_EX and option_type(option) in (OPT_ABILITY, OPT_ATTACK):
        return True
    attack_name = str(getv(option, "attackName", "") or getv(option, "name", "") or getv(option, "label", "")).lower()
    if "trade" in attack_name:
        return True
    return context_source_name(state) == ZOROARK_EX and "trade" in attack_name


def pp_up_line_benefits(state: Any) -> bool:
    if darkness_in_discard(state) > 0:
        return True
    return has_in_hand(state, "N's PP Up") and (count_in_play(state, ZOROARK_EX) > 0 or count_in_play(state, ZORUA) > 0)
