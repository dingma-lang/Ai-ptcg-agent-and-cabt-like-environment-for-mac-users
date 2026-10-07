from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable


def getv(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def legal_options(obs: dict) -> list[Any]:
    select = getv(obs, "select", {}) or {}
    options = getv(select, "option", []) or []
    return options if isinstance(options, list) else []


def selection_bounds(obs: dict) -> tuple[int, int]:
    select = getv(obs, "select", {}) or {}
    options = legal_options(obs)
    min_count = max(0, int_or(getv(select, "minCount", 0), 0))
    max_count = int_or(getv(select, "maxCount", min_count), min_count)
    max_count = max(min_count, min(len(options), max_count))
    return min(min_count, len(options)), max_count


def int_or(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except Exception:
        return default


def validate_selection(obs: dict, selected: Iterable[Any]) -> tuple[list[int], list[str]]:
    options = legal_options(obs)
    min_count, max_count = selection_bounds(obs)
    errors: list[str] = []
    clean: list[int] = []
    seen: set[int] = set()
    for raw in selected or []:
        try:
            idx = int(raw)
        except Exception:
            errors.append(f"non-integer selected index: {raw!r}")
            continue
        if idx < 0 or idx >= len(options):
            errors.append(f"selected index {idx} outside legal range 0..{len(options)-1}")
            continue
        if idx in seen:
            errors.append(f"duplicate selected index: {idx}")
            continue
        clean.append(idx)
        seen.add(idx)
        if len(clean) >= max_count:
            break
    if len(clean) < min_count:
        errors.append(f"selected {len(clean)} option(s), but minCount is {min_count}")
    if len(clean) > max_count:
        errors.append(f"selected {len(clean)} option(s), but maxCount is {max_count}")
    return clean, errors


def random_legal_selection(obs: dict, rng: Any) -> list[int]:
    options = legal_options(obs)
    min_count, max_count = selection_bounds(obs)
    if not options or max_count <= 0:
        return []
    count = max_count if min_count == max_count else rng.randint(min_count, max_count)
    count = min(count, len(options))
    return rng.sample(list(range(len(options))), count)


def selected_options(obs: dict, indexes: Iterable[int]) -> list[Any]:
    options = legal_options(obs)
    return [options[idx] for idx in indexes if 0 <= idx < len(options)]


def normalized_features(obs: dict, player: int | None = None) -> dict[str, Any]:
    current = getv(obs, "current", {}) or {}
    players = getv(current, "players", []) or []
    pidx = int_or(getv(current, "yourIndex", player if player is not None else 0), 0)
    player_state = players[pidx] if isinstance(players, list) and 0 <= pidx < len(players) else {}
    opp_state = players[1 - pidx] if isinstance(players, list) and 0 <= 1 - pidx < len(players) else {}
    return {
        "turn": int_or(getv(current, "turn", 0), 0),
        "acting_player": acting_player(obs, pidx),
        "your_index": pidx,
        "bench_count": len(getv(player_state, "bench", []) or []),
        "opponent_bench_count": len(getv(opp_state, "bench", []) or []),
        "hand_count": int_or(getv(player_state, "handCount", len(getv(player_state, "hand", []) or [])), 0),
        "opponent_hand_count": int_or(getv(opp_state, "handCount", 0), 0),
        "deck_count": int_or(getv(player_state, "deckCount", 0), 0),
        "opponent_deck_count": int_or(getv(opp_state, "deckCount", 0), 0),
        "prize_count": len(getv(player_state, "prize", []) or []),
        "opponent_prize_count": len(getv(opp_state, "prize", []) or []),
        "legal_option_count": len(legal_options(obs)),
        "min_max": selection_bounds(obs),
    }


def acting_player(obs: dict, default: int = 0) -> int:
    current = getv(obs, "current", {}) or {}
    for key in ("yourIndex", "selectPlayer", "actingPlayer", "currentPlayer", "turnPlayer", "playerTurn"):
        value = getv(current, key)
        if value in (0, 1, "0", "1"):
            return int(value)
    turn = int_or(getv(current, "turn", 1), 1)
    first = int_or(getv(current, "firstPlayer", default), default)
    if first not in (0, 1):
        return default
    return first if turn % 2 == 1 else 1 - first


def redact_hidden_information(obs: dict, player: int) -> dict:
    redacted = deepcopy(obs)
    current = getv(redacted, "current", {}) or {}
    players = getv(current, "players", []) or []
    if not isinstance(players, list):
        return redacted
    for idx, pstate in enumerate(players):
        if idx == player:
            continue
        if isinstance(pstate, dict):
            pstate["hand"] = [None] * int_or(pstate.get("handCount", 0), 0)
            pstate["prize"] = [None] * len(pstate.get("prize", []) or [])
            pstate.pop("deck", None)
    return redacted
