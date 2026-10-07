from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from card_db import get_db
from state_eval import OPT_ATTACK, active_pokemon, card_id, getv, int_or, option_type
from core.palafin_planner import PALAFIN_EX
from core.priority_tables import canonical_name_from_id


@dataclass(frozen=True)
class GigaImpactStatus:
    palafin_instance_id: str = ""
    used_giga_impact_last_turn: bool = False
    currently_active: bool = False
    restriction_applies_now: bool = False
    can_attack_now: bool = True
    can_reset_by_switching: bool = False
    reset_options_available: bool = False
    reason: str = "Do not globally block Palafin attacks."


def track_giga_impact_lock(state: Any, memory: Any = None) -> GigaImpactStatus:
    del memory
    active = active_pokemon(state)
    active_name = canonical_name_from_id(card_id(active))
    active_id = pokemon_instance_id(active, "active")
    locked_id = explicit_locked_instance_id(state)
    active_flag = bool(getv(active, "gigaImpactLocked", False) or getv(active, "usedGigaImpactLastTurn", False) or getv(active, "cannotAttack", False))

    if active_name != "Palafin ex":
        return GigaImpactStatus(
            palafin_instance_id=active_id,
            used_giga_impact_last_turn=bool(locked_id),
            currently_active=False,
            restriction_applies_now=False,
            can_attack_now=True,
            can_reset_by_switching=False,
            reset_options_available=False,
            reason="Giga Impact lock applies only to this Palafin ex.",
        )

    applies = active_flag or (bool(locked_id) and locked_id == active_id)
    # A currently legal Giga Impact overrides stale inferred/history flags.
    if legal_giga_impact(state):
        applies = False
    if not applies and locked_id and locked_id != active_id:
        return GigaImpactStatus(
            palafin_instance_id=active_id,
            used_giga_impact_last_turn=True,
            currently_active=True,
            restriction_applies_now=False,
            can_attack_now=True,
            can_reset_by_switching=False,
            reset_options_available=False,
            reason="Another Palafin ex can still attack.",
        )
    return GigaImpactStatus(
        palafin_instance_id=active_id,
        used_giga_impact_last_turn=applies,
        currently_active=True,
        restriction_applies_now=applies,
        can_attack_now=not applies,
        can_reset_by_switching=applies,
        reset_options_available=applies,
        reason="Switching Palafin ex to Bench can reset the Giga Impact restriction." if applies else "Do not globally block Palafin attacks.",
    )


def explicit_locked_instance_id(state: Any) -> str:
    current = getattr(state, "current", {}) or {}
    for key in ("gigaImpactLockInstanceId", "gigaImpactLockedInstanceId", "palafinGigaImpactLock", "palafinGigaImpactLockedInstanceId"):
        value = getv(current, key)
        if value is not None:
            return str(value)
    serial = pokemon_instance_id(active_pokemon(state), "active")
    locks = getattr(state, "giga_impact_locks", None)
    if locks is None:
        locks = observe_giga_locks(state, {})
    if locks.get(serial) == int_or(getv(state.current, "turn"), 0):
        return serial
    logs = getv(getattr(state, "obs", {}), "logs", []) or []
    if isinstance(logs, list):
        for log in reversed(logs):
            text = str(log)
            if "Giga Impact" in text and "Palafin ex" in text:
                return str(getv(log, "instanceId", "") or getv(log, "serial", "") or "")
    return ""


def legal_giga_impact(state: Any) -> bool:
    return any(option_type(o) == OPT_ATTACK
               and getattr(get_db().get_attack(getv(o, "attackId")), "name", "") == "Giga Impact"
               for o in state.options)


def observe_giga_locks(state: Any, previous: dict[str, int]) -> dict[str, int]:
    """Read public cabt events; values are the absolute turn when the lock applies."""
    turn = int_or(getv(state.current, "turn"), 0)
    locks = {serial: expires for serial, expires in previous.items() if expires >= turn}
    logs = getv(state.obs, "logs", []) or []
    # Logs may span both players' turns. Count starts backwards from the current turn.
    event_turn = turn
    timed_logs = []
    for log in reversed(logs if isinstance(logs, list) else []):
        timed_logs.append((log, event_turn))
        if int_or(getv(log, "type"), -1) == 2:
            event_turn -= 1
    for log, at_turn in reversed(timed_logs):
        if int_or(getv(log, "playerIndex"), -1) != state.your_index:
            continue
        typ = int_or(getv(log, "type"), -1)
        serial = str(getv(log, "serial", ""))
        attack = get_db().get_attack(getv(log, "attackId"))
        if typ == 15 and getv(log, "cardId") == PALAFIN_EX and attack and attack.name == "Giga Impact":
            if serial:
                locks[serial] = at_turn + 2
        elif typ == 8:
            locks.pop(str(getv(log, "serialActive", "")), None)
            locks.pop(str(getv(log, "serialBench", "")), None)
        elif typ == 6 and int_or(getv(log, "fromArea"), -1) == 4:
            locks.pop(serial, None)
    active_serial = pokemon_instance_id(active_pokemon(state), "active")
    locks = {serial: expires for serial, expires in locks.items()
             if serial == active_serial and expires >= turn}
    if legal_giga_impact(state):
        locks.pop(active_serial, None)
    return locks


def pokemon_instance_id(pokemon: Any, fallback: str = "") -> str:
    for key in ("instanceId", "instance_id", "uid", "localId", "serial"):
        value = getv(pokemon, key)
        if value is not None:
            return str(value)
    cid = card_id(pokemon)
    return f"{fallback}:{cid or ''}"


__all__ = ["GigaImpactStatus", "track_giga_impact_lock", "pokemon_instance_id"]
