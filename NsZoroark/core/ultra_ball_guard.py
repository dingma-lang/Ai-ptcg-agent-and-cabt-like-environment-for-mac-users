from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from card_db import get_db
from state_eval import bench_pokemon, bench_space, card_id, card_id_from_option, getv, hand_cards
from core.priority_tables import LOW_PRIORITY_DISCARD_IDS, PROTECTED_IDS, canonical_name_from_id, count_in_play, has_in_hand, has_in_play


LINE_PREVIOUS = {
    "Zweilous": "Deino",
    "Hydreigon ex": "Zweilous",
    "Haunter": "Gastly",
    "Mega Gengar ex": "Haunter",
    "Toxtricity": "Toxel",
}


BASIC_FOR_STAGE2 = {
    "Hydreigon ex": "Deino",
    "Mega Gengar ex": "Gastly",
}


@dataclass(frozen=True)
class UltraBallDiscardPlan:
    safe_count: int
    protected_count: int
    reason: str


def score_ultra_ball_play_safety(state: Any) -> float:
    plan = ultra_ball_discard_plan(state)
    if plan.safe_count >= 2:
        return 0.0
    if poffin_must_be_used_before_ultra_ball(state):
        return -5200.0
    return -2600.0


def ultra_ball_discard_plan(state: Any) -> UltraBallDiscardPlan:
    safe = 0
    protected = 0
    for card in hand_cards(state):
        cid = card_id(card)
        if canonical_name_from_id(cid) == "Ultra Ball":
            continue
        score = score_ultra_ball_discard_card(state, cid)
        if score > 0:
            safe += 1
        if score <= -2500:
            protected += 1
    return UltraBallDiscardPlan(safe, protected, f"Ultra Ball safe discards={safe}, protected={protected}.")


def score_ultra_ball_discard_card(state: Any, cid: Optional[int]) -> float:
    if cid is None:
        return 0.0
    name = canonical_name_from_id(cid)
    if name == "Buddy-Buddy Poffin" and poffin_must_be_used_before_ultra_ball(state):
        return -12000.0
    if card_can_be_used_this_turn(state, cid):
        return -7200.0
    if cid in PROTECTED_IDS:
        return -2600.0
    disposable = disposable_evolution_score(state, cid)
    if disposable:
        return disposable
    if cid in LOW_PRIORITY_DISCARD_IDS:
        return 650.0
    if duplicate_in_hand(state, cid):
        return 550.0
    if name == "Basic Darkness Energy":
        return 260.0
    return 0.0


def poffin_must_be_used_before_ultra_ball(state: Any) -> bool:
    if not has_in_hand(state, "Buddy-Buddy Poffin") or bench_space(state) <= 0:
        return False
    if len(bench_pokemon(state)) == 0:
        return True
    return missing_core_basic(state)


def missing_core_basic(state: Any) -> bool:
    return count_in_play(state, "Deino") < 2 or not has_in_play(state, "Gastly") or not (has_in_play(state, "Toxel") or has_in_play(state, "Toxtricity"))


def card_can_be_used_this_turn(state: Any, cid: int) -> bool:
    name = canonical_name_from_id(cid)
    if name == "Buddy-Buddy Poffin":
        return poffin_must_be_used_before_ultra_ball(state)
    if name == "Rare Candy":
        return has_in_play(state, "Deino") and has_in_hand(state, "Hydreigon ex")
    if name in {"Lillie's Determination", "Dawn", "Team Rocket's Petrel", "Crispin", "Boss's Orders"}:
        return not bool(getv(state.current, "supporterPlayed", False))
    if name in {"Poke Pad", "Secret Box", "Energy Recycler", "Sacred Ash", "Night Stretcher"}:
        return item_is_useful_now(state, name)
    if name in {"Basic Darkness Energy", "Basic Metal Energy", "Basic Psychic Energy"}:
        return not bool(getv(state.current, "energyAttached", False)) and useful_energy_in_hand(state, cid)

    card = get_db().get_card(cid)
    if not card or card.card_type != "Pokemon":
        return False
    if card.basic:
        return bench_space(state) > 0 and name in {"Deino", "Gastly", "Toxel"}
    if card.stage1:
        previous = LINE_PREVIOUS.get(name) or card.evolves_from
        return bool(previous and has_in_play(state, previous))
    if card.stage2:
        previous = LINE_PREVIOUS.get(name) or card.evolves_from
        basic = BASIC_FOR_STAGE2.get(name)
        return bool((previous and has_in_play(state, previous)) or (basic and has_in_play(state, basic) and has_in_hand(state, "Rare Candy")))
    return False


def item_is_useful_now(state: Any, name: str) -> bool:
    if name == "Poke Pad":
        try:
            from core.combo_presence_planner import evolution_bridge_needed

            return missing_core_basic(state) or evolution_bridge_needed(state)
        except Exception:
            return missing_core_basic(state)
    if name == "Secret Box":
        try:
            from core.secret_box_planner import choose_secret_box_package

            return choose_secret_box_package(state).should_use
        except Exception:
            return False
    if name == "Energy Recycler":
        try:
            from core.recovery_timing_planner import score_energy_recycler

            return score_energy_recycler(state) > 0
        except Exception:
            return False
    if name == "Sacred Ash":
        try:
            from core.recovery_timing_planner import score_sacred_ash

            return score_sacred_ash(state) > 0
        except Exception:
            return False
    if name == "Night Stretcher":
        try:
            from core.recovery_timing_planner import score_night_stretcher

            return score_night_stretcher(state) > 0
        except Exception:
            return False
    return False


def useful_energy_in_hand(state: Any, cid: int) -> bool:
    try:
        from core.energy_planner import score_energy_attachment
        from state_eval import iter_in_play

        return any(score_energy_attachment(state, cid, pokemon) >= 500.0 for _, _, pokemon in iter_in_play(state))
    except Exception:
        return False


def disposable_evolution_score(state: Any, cid: int) -> float:
    name = canonical_name_from_id(cid)
    card = get_db().get_card(cid)
    if not card or card.card_type != "Pokemon":
        return 0.0
    if card.stage1:
        previous = LINE_PREVIOUS.get(name) or card.evolves_from
        if previous and not has_in_play(state, previous) and not has_in_hand(state, previous):
            return 900.0
    if card.stage2:
        previous = LINE_PREVIOUS.get(name) or card.evolves_from
        basic = BASIC_FOR_STAGE2.get(name)
        if previous and not has_in_play(state, previous) and not (basic and has_in_play(state, basic) and has_in_hand(state, "Rare Candy")):
            return 750.0
    return 0.0


def duplicate_in_hand(state: Any, cid: int) -> bool:
    return sum(1 for card in hand_cards(state) if card_id(card) == cid) >= 2
