from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

from card_db import get_db
from state_eval import OPT_ATTACK, active_pokemon, card_id, getv, option_type, pokemon_energy_count
from core.copy_target_planner import CopyChoice, choose_best_benched_n_attack_to_copy
from core.damage_math_planner import calculate_zoroark_damage
from core.target_board import ZOROARK_EX, pokemon_name


@dataclass(frozen=True)
class NightJokerPlan:
    should_attack: bool
    option_index: Optional[int] = None
    copy_choice: CopyChoice = CopyChoice()
    score: float = 0.0
    reason: str = ""


def evaluate_night_joker_options(state: Any, legal_options: Sequence[Any], opponent_model: Any = None) -> NightJokerPlan:
    active = active_pokemon(state)
    if pokemon_name(active) != ZOROARK_EX:
        return NightJokerPlan(False, reason="Active is not N's Zoroark ex.")
    if pokemon_energy_count(active) < 2:
        return NightJokerPlan(False, reason="N's Zoroark ex does not have two Darkness Energy.")
    choice = choose_best_benched_n_attack_to_copy(state, opponent_model)
    if choice.score <= -10000.0:
        return NightJokerPlan(False, copy_choice=choice, score=-3000.0, reason=choice.reason)

    best_idx: Optional[int] = None
    best_score = -99999.0
    for idx, option in enumerate(legal_options):
        if option_type(option) != OPT_ATTACK:
            continue
        score = score_night_joker_option(state, option, idx)
        if score > best_score:
            best_idx = idx
            best_score = score
    if best_idx is None:
        return NightJokerPlan(False, copy_choice=choice, score=choice.score, reason="Night Joker attack is not legal.")
    return NightJokerPlan(best_score > 0.0, best_idx, choice, best_score, choice.reason)


def score_night_joker_option(state: Any, option: Any, option_index: int = 0) -> float:
    if option_type(option) != OPT_ATTACK:
        return 0.0
    active = active_pokemon(state)
    if pokemon_name(active) != ZOROARK_EX:
        return 0.0
    attack_name = option_attack_name(state, option, option_index)
    if attack_name and "night joker" not in attack_name.lower():
        return 0.0
    if pokemon_energy_count(active) < 2:
        return -5000.0
    choice = choose_best_benched_n_attack_to_copy(state)
    if choice.score <= -9000.0:
        return -2500.0
    math = calculate_zoroark_damage(state, choice, {}, None)
    score = 2200.0 + choice.score
    if math.is_ko:
        score += 7000.0 + math.prize_value * 850.0
    if "Flamebody Cannon" in choice.copied_attack_name and choice.score < 0:
        score -= 6000.0
    if zoroark_attack_locked_by_logs(state):
        score -= 500.0
    return score


def option_attack_name(state: Any, option: Any, option_index: int = 0) -> str:
    for key in ("attackName", "name", "label"):
        value = str(getv(option, key, "") or "")
        if value:
            return value
    attack = get_db().get_attack(getv(option, "attackId"))
    if attack:
        return attack.name
    active = active_pokemon(state)
    card = get_db().get_card(card_id(active))
    if card and card.attacks:
        attacks = [idx for idx, item in enumerate(getattr(state, "options", []) or []) if option_type(item) == OPT_ATTACK]
        try:
            pos = attacks.index(option_index)
        except ValueError:
            pos = 0
        if 0 <= pos < len(card.attacks):
            return card.attacks[pos].name
    return ""


def zoroark_attack_locked_by_logs(state: Any) -> bool:
    logs = getv(state.obs, "logs", []) or []
    if not isinstance(logs, list):
        return False
    text = " ".join(str(log) for log in logs[-12:]).lower()
    return "zoroark" in text and "rampaging thunder" in text and ("can't use attacks" in text or "cannot use attacks" in text)
