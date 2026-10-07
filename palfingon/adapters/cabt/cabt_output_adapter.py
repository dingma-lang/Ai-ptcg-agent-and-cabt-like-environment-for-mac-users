from __future__ import annotations

from typing import Any, Iterable, List

from core.action_intent import ActionIntent
from state_eval import OPT_END, getv, int_or, option_type


def intent_to_option_indices(intent: ActionIntent, select: Any) -> List[int]:
    options = getv(select, "option", []) or []
    if not isinstance(options, list) or not options:
        return []

    min_count = max(0, int_or(getv(select, "minCount", 0), 0))
    max_count = min(len(options), max(min_count, int_or(getv(select, "maxCount", min_count), min_count)))
    if max_count <= 0:
        return []

    clean = legal_unique_indices(intent.selected_option_indices, len(options), max_count)
    if len(clean) >= min_count:
        return clean
    if min_count == 0:
        return []

    for idx, option in enumerate(options):
        if idx not in clean and option_type(option) == OPT_END:
            clean.append(idx)
            if len(clean) >= min_count:
                return clean[:max_count]

    for idx in range(len(options)):
        if idx not in clean:
            clean.append(idx)
            if len(clean) >= min_count:
                break
    return clean[:max_count]


def legal_unique_indices(raw_indices: Iterable[Any], option_count: int, max_count: int) -> List[int]:
    clean: List[int] = []
    seen = set()
    for raw in raw_indices or []:
        try:
            idx = int(raw)
        except (TypeError, ValueError):
            continue
        if 0 <= idx < option_count and idx not in seen:
            clean.append(idx)
            seen.add(idx)
        if len(clean) >= max_count:
            break
    return clean
