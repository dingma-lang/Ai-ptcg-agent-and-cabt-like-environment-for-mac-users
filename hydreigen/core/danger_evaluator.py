from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, List

from action_classifier import ActionCategory, classify_legal_option
from card_db import get_db
from state_eval import active_pokemon, bench_pokemon, card_id, deck_count, getv, hand_count, iter_in_play, option_type, pokemon_energy_count, pokemon_hp, pokemon_max_hp, prize_count
from core.opponent_model import OpponentThreat, infer_opponent_next_turn_threat, prize_value
from core.priority_tables import HYDREIGON_LINE_IDS, RULE_BOX_IDS


LOW = "LOW"
MEDIUM = "MEDIUM"
HIGH = "HIGH"
CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class DangerAssessment:
    severity: str
    score: float
    reason: str
    active_can_be_koed: bool = False
    active_high_resource: bool = False
    bench_count: int = 0
    bench_low: bool = False
    ready_backup: bool = False
    opponent_can_take_final_prizes: bool = False
    ko_last_turn: bool = False
    protective_action_available: bool = False
    threat: OpponentThreat | None = None


def evaluate_danger(state: Any) -> DangerAssessment:
    active = active_pokemon(state)
    bench = bench_pokemon(state)
    threat = infer_opponent_next_turn_threat(state)
    hp = pokemon_hp(active)
    max_hp = pokemon_max_hp(active)
    active_cid = card_id(active)
    active_high_resource = is_high_resource_active(active)
    active_low_hp = bool(active and hp <= max(70, int(max_hp * 0.35) if max_hp else 70))
    active_can_be_koed = bool(threat.can_take_active_ko or (active_low_hp and threat.max_visible_damage >= 70))
    ready_backup = has_ready_backup_attacker(state)
    bench_count = len(bench)
    bench_low = bench_count <= 1
    ko_last_turn = our_pokemon_knocked_out_last_turn(state)
    final_prizes = bool(threat.can_take_final_prizes or (active_can_be_koed and prize_count(state, state.opponent_index) <= prize_value(active)))
    protective = protective_action_available(state)

    score = 0.0
    reasons: List[str] = []
    if ko_last_turn:
        score += 250.0
        reasons.append("our Pokemon was KO'd last opponent turn")
    if bench_count == 0:
        score += 850.0
        reasons.append("Bench is empty")
    elif bench_count == 1:
        score += 450.0
        reasons.append("Bench has only one Pokemon")
    if active_can_be_koed:
        score += 650.0
        reasons.append("Active is under KO threat")
    if active_high_resource:
        score += 250.0
        reasons.append("Active is a high-resource attacker")
    if not ready_backup:
        score += 350.0
        reasons.append("no ready backup attacker")
    else:
        score -= 450.0
        reasons.append("backup attacker is ready")
    if final_prizes:
        score += 1200.0
        reasons.append("opponent can take final prizes")
    if deck_count(state) <= 3:
        score += 250.0
        reasons.append("deck-out risk is present")

    if final_prizes or (bench_count == 0 and active_can_be_koed):
        severity = CRITICAL
    elif active_can_be_koed and active_high_resource and not ready_backup:
        severity = HIGH
    elif score >= 900:
        severity = HIGH
    elif score >= 350:
        severity = MEDIUM
    else:
        severity = LOW

    if ready_backup and severity == CRITICAL and not final_prizes and bench_count > 0:
        severity = MEDIUM
    if ready_backup and severity == HIGH and not final_prizes:
        severity = MEDIUM

    reason = "; ".join(reasons) if reasons else threat.reason
    if severity in (HIGH, CRITICAL):
        reason = f"Danger {severity}: {reason}"
    return DangerAssessment(
        severity=severity,
        score=score,
        reason=reason,
        active_can_be_koed=active_can_be_koed,
        active_high_resource=active_high_resource,
        bench_count=bench_count,
        bench_low=bench_low,
        ready_backup=ready_backup,
        opponent_can_take_final_prizes=final_prizes,
        ko_last_turn=ko_last_turn,
        protective_action_available=protective,
        threat=threat,
    )


def our_pokemon_knocked_out_last_turn(state: Any) -> bool:
    logs = getv(state.obs, "logs", []) or []
    if not isinstance(logs, list):
        return False
    for log in reversed(logs[-30:]):
        text = " ".join(_string_values(log)).lower()
        event = str(getv(log, "type", "") or getv(log, "event", "") or getv(log, "action", "")).lower()
        padded_text = f" {text} "
        padded_event = f" {event} "
        if not any(term in text or term in event for term in ("knock", "ko'd", "koed", "k.o", "defeated")) and " ko " not in padded_text and " ko " not in padded_event:
            continue
        players = set(_player_values(log))
        if state.your_index in players:
            return True
        if state.opponent_index in players and state.your_index not in players:
            continue
        if any(term in text for term in ("your pokemon", "your pokémon", "our pokemon", "our pokémon")):
            return True
        if "opponent" in text and "last turn" not in text:
            continue
        return True
    return False


def is_high_resource_active(active: Any) -> bool:
    cid = card_id(active)
    card = get_db().get_card(cid)
    if not active:
        return False
    return bool(cid in HYDREIGON_LINE_IDS or cid in RULE_BOX_IDS or pokemon_energy_count(active) >= 2 or (card and card.prize_value > 1))


def has_ready_backup_attacker(state: Any) -> bool:
    for pokemon in bench_pokemon(state):
        if can_attack_now(pokemon):
            return True
    return False


def can_attack_now(pokemon: Any) -> bool:
    cid = card_id(pokemon)
    card = get_db().get_card(cid)
    if not card:
        return False
    energy = pokemon_energy_count(pokemon)
    return any(energy >= len(attack.cost or []) and int(getattr(attack, "damage", 0) or 0) > 0 for attack in card.attacks)


def protective_action_available(state: Any) -> bool:
    for idx, option in enumerate(getattr(state, "options", []) or []):
        action = classify_legal_option(state, option, idx)
        if action.category in (
            ActionCategory.PLAY_BASIC_TO_BENCH,
            ActionCategory.DRAW_OR_SEARCH,
            ActionCategory.EVOLVE,
            ActionCategory.RARE_CANDY_EVOLVE,
            ActionCategory.RETREAT,
            ActionCategory.SWITCH_ACTIVE,
            ActionCategory.PLAY_SUPPORTER,
            ActionCategory.PLAY_ITEM,
        ):
            if option_type(option) != 14:
                return True
    return False


def active_attack_is_low_value(score: float) -> bool:
    return score < 10000.0 and score < 450.0


def _string_values(obj: Any) -> Iterable[str]:
    if isinstance(obj, dict):
        for value in obj.values():
            yield from _string_values(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _string_values(value)
    elif isinstance(obj, str):
        yield obj


def _player_values(obj: Any) -> Iterable[int]:
    if not isinstance(obj, dict):
        return []
    keys = (
        "playerIndex",
        "player",
        "owner",
        "ownerIndex",
        "targetPlayerIndex",
        "pokemonPlayerIndex",
        "knockedOutPlayerIndex",
        "defendingPlayerIndex",
    )
    values: List[int] = []
    for key in keys:
        raw = getv(obj, key)
        try:
            if raw is not None:
                values.append(int(raw))
        except Exception:
            pass
    nested = getv(obj, "pokemon")
    if isinstance(nested, dict):
        values.extend(_player_values(nested))
    return values
