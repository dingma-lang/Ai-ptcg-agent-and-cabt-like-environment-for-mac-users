from __future__ import annotations

from typing import Any, Optional, Sequence

from card_db import get_db
from state_eval import OPT_PLAY, bench_pokemon, bench_space, card_id_from_option, option_type, prize_count
from core.priority_tables import CARD_IDS, canonical_name_from_id, count_in_play, has_in_play


CORE_BASIC_IDS = {CARD_IDS["Deino"], CARD_IDS["Gastly"], CARD_IDS["Toxel"]}
SUPPORT_BASIC_IDS = {CARD_IDS["Fezandipiti ex"], CARD_IDS["Pecharunt ex"]}


def best_basic_bench_from_hand(state: Any, options: Sequence[Any] | None = None) -> Optional[int]:
    if bench_space(state) <= 0:
        return None
    legal_options = list(options or getattr(state, "options", []) or [])
    best_idx: Optional[int] = None
    best_score = -1.0
    for idx, option in enumerate(legal_options):
        score = score_basic_bench_play(state, option, idx)
        if score > best_score:
            best_idx = idx
            best_score = score
    return best_idx if best_score > 0.0 else None


def score_basic_bench_play(state: Any, option: Any, option_index: int = 0) -> float:
    if bench_space(state) <= 0 or option_type(option) != OPT_PLAY:
        return 0.0
    cid = card_id_from_option(state, option)
    card = get_db().get_card(cid)
    if not card or card.card_type != "Pokemon" or not card.basic:
        return 0.0

    name = canonical_name_from_id(cid)
    duplicate_count = count_in_play(state, cid)
    bridge_needed = call_for_family_bench_bridge_needed(state)
    score = 2400.0

    if cid == CARD_IDS["Deino"]:
        if duplicate_count == 0:
            score = 7600.0
        elif bridge_needed:
            score = 2800.0
        else:
            score = 7000.0 if duplicate_count == 1 else 2600.0
    elif cid == CARD_IDS["Gastly"]:
        score = 6900.0 if duplicate_count == 0 else 2400.0
        try:
            from core.opponent_model import infer_opponent_next_turn_threat

            threat = infer_opponent_next_turn_threat(state)
            if threat.has_rulebox_attacker or threat.likely_ex_heavy:
                score += 1200.0
        except Exception:
            pass
    elif cid == CARD_IDS["Toxel"]:
        if bridge_needed:
            score = 8200.0
        else:
            score = 6600.0 if not (has_in_play(state, "Toxel") or has_in_play(state, "Toxtricity")) else 2200.0
    elif cid == CARD_IDS["Fezandipiti ex"]:
        if support_ex_is_final_prize_liability(state):
            return 0.0
        score = 5600.0 if duplicate_count == 0 else 1300.0
        try:
            from core.danger_evaluator import our_pokemon_knocked_out_last_turn

            if our_pokemon_knocked_out_last_turn(state):
                score += 2800.0
        except Exception:
            pass
    elif cid == CARD_IDS["Pecharunt ex"]:
        if support_ex_is_final_prize_liability(state):
            return 0.0
        score = 4800.0 if duplicate_count == 0 else 1100.0
    elif cid in CORE_BASIC_IDS:
        score = 4200.0
    elif cid in SUPPORT_BASIC_IDS:
        score = 3600.0

    score += useful_basic_attack_bonus(card)
    if duplicate_count >= 2:
        score -= 1200.0
    if name:
        score += min(300.0, len(name) * 3.0)
    return max(100.0, score)


def useful_basic_attack_bonus(card: Any) -> float:
    bonus = 0.0
    for attack in getattr(card, "attacks", []) or []:
        attack_name = str(getattr(attack, "name", "") or "").lower()
        attack_text = str(getattr(attack, "text", "") or "").lower()
        damage = int(getattr(attack, "damage", 0) or 0)
        if "call for family" in attack_name or "put them onto your bench" in attack_text:
            bonus += 1400.0
        elif damage >= 100:
            bonus += 500.0
        elif damage > 0:
            bonus += min(250.0, damage * 4.0)
    return min(1600.0, bonus)


def call_for_family_bench_bridge_needed(state: Any) -> bool:
    return (
        bench_space(state) > 0
        and len(bench_pokemon(state)) <= 1
        and has_in_play(state, "Deino")
        and not (has_in_play(state, "Toxel") or has_in_play(state, "Toxtricity"))
    )


def basic_bench_available(state: Any) -> bool:
    return best_basic_bench_from_hand(state) is not None


def support_ex_is_final_prize_liability(state: Any) -> bool:
    try:
        from core.setup_recovery_planner import weak_board_ignores_prize_liability

        if weak_board_ignores_prize_liability(state):
            return False
    except Exception:
        pass
    try:
        from core.danger_evaluator import our_pokemon_knocked_out_last_turn

        if our_pokemon_knocked_out_last_turn(state):
            return False
    except Exception:
        pass
    return prize_count(state, state.opponent_index) <= 2 and len(bench_pokemon(state)) >= 2
