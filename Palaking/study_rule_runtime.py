from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_CACHE_MTIME_NS = -1
_CACHE_RULES: list[dict[str, Any]] = []
_USEFUL_CATEGORIES = {
    "ATTACH_ENERGY",
    "EVOLVE",
    "PLAY_BASIC_TO_BENCH",
    "PLAY_ITEM",
    "PLAY_STADIUM",
    "PLAY_SUPPORTER",
    "RARE_CANDY_EVOLVE",
    "USE_ABILITY",
}


def load_study_rules() -> list[dict[str, Any]]:
    global _CACHE_MTIME_NS, _CACHE_RULES
    path = Path(__file__).with_name("study_rules.json")
    try:
        mtime = path.stat().st_mtime_ns
    except OSError:
        return []
    if mtime == _CACHE_MTIME_NS:
        return list(_CACHE_RULES)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload.get("accepted_rules") if isinstance(payload, dict) else []
        rules = [row for row in (rows or []) if isinstance(row, dict)]
    except (OSError, json.JSONDecodeError):
        rules = []
    _CACHE_MTIME_NS = mtime
    _CACHE_RULES = rules
    return list(_CACHE_RULES)


def apply_study_rules(state: Any, option: Any, option_index: int, base_score: float) -> float:
    try:
        from action_classifier import classify_legal_option

        classified = classify_legal_option(state, option, option_index)
        category = str(classified.category or "UNKNOWN")
    except Exception:
        return base_score

    score = float(base_score)
    for rule in load_study_rules():
        if str(rule.get("target_category") or "UNKNOWN") not in {category, "ANY"}:
            continue
        conditions = rule.get("conditions") or {}
        if not isinstance(conditions, dict) or not conditions_match(state, classified, conditions):
            continue
        effect = str(rule.get("effect") or "review")
        try:
            weight = min(50000.0, max(-50000.0, float(rule.get("weight") or 0.0)))
        except (TypeError, ValueError):
            continue
        if effect == "prefer":
            score += abs(weight)
        elif effect == "avoid":
            score -= abs(weight)
    return score


def conditions_match(state: Any, classified: Any, conditions: dict[str, Any]) -> bool:
    for key, expected in conditions.items():
        if key == "useful_legal_action_exists":
            if bool(expected) != useful_legal_action_exists(state):
                return False
        elif key == "useful_categories":
            wanted = {str(value) for value in expected} if isinstance(expected, list) else set()
            if not wanted or not legal_categories(state).intersection(wanted):
                return False
        elif key == "supporter_unused":
            if bool(expected) == current_flag(state, "supporterPlayed"):
                return False
        elif key == "energy_attachment_unused":
            if bool(expected) == current_flag(state, "energyAttached"):
                return False
        elif key == "card_name_contains":
            if str(expected).lower() not in str(getattr(classified, "card_name", "")).lower():
                return False
        elif key == "target_name_contains":
            if str(expected).lower() not in str(getattr(classified, "target_name", "")).lower():
                return False
        elif key == "turn_at_most":
            if integer(getattr(state, "turn", 0), 0) > integer(expected, 0):
                return False
        elif key == "turn_at_least":
            if integer(getattr(state, "turn", 0), 0) < integer(expected, 0):
                return False
        else:
            # Unknown conditions are deliberately inert until the adapter supports them.
            return False
    return True


def useful_legal_action_exists(state: Any) -> bool:
    return bool(legal_categories(state).intersection(_USEFUL_CATEGORIES))


def legal_categories(state: Any) -> set[str]:
    try:
        from action_classifier import classify_legal_option

        options = list(getattr(state, "options", []) or [])
        return {str(classify_legal_option(state, option, index).category or "UNKNOWN") for index, option in enumerate(options)}
    except Exception:
        return set()


def current_flag(state: Any, name: str) -> bool:
    current = getattr(state, "current", {}) or {}
    if isinstance(current, dict):
        return bool(current.get(name, False))
    return bool(getattr(current, name, False))


def integer(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


__all__ = ["apply_study_rules", "load_study_rules"]
