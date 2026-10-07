from __future__ import annotations

from typing import List

import config
from adapters.cabt.cabt_input_adapter import parse_obs, parse_select
from adapters.cabt.cabt_output_adapter import intent_to_option_indices
from core.agent_memory import GLOBAL_AGENT_MEMORY
from core.deck_profile import load_deck_ids
from core.policy import choose_intent


def agent(obs_dict: dict) -> List[int]:
    config.assert_submission_safe()
    if not isinstance(obs_dict, dict):
        return []

    select = parse_select(obs_dict)
    if "select" in obs_dict and select is None and obs_dict.get("current") is None:
        GLOBAL_AGENT_MEMORY.attack_lock_observers.clear()
        return load_deck_ids()
    if select is None:
        return []

    options = select.get("option") if isinstance(select, dict) else getattr(select, "option", None)
    if not options:
        return []

    try:
        state = parse_obs(obs_dict)
        GLOBAL_AGENT_MEMORY.update_from_state(state, mode=config.MODE)
        intent = choose_intent(state, GLOBAL_AGENT_MEMORY)
        return intent_to_option_indices(intent, select)
    except Exception:
        return safe_cabt_fallback(select)


def safe_cabt_fallback(select: object) -> List[int]:
    options = select.get("option", []) if isinstance(select, dict) else getattr(select, "option", [])
    if not isinstance(options, list) or not options:
        return []
    min_count = max(0, int((select.get("minCount", 0) if isinstance(select, dict) else getattr(select, "minCount", 0)) or 0))
    max_count_raw = (select.get("maxCount", min_count) if isinstance(select, dict) else getattr(select, "maxCount", min_count)) or min_count
    max_count = min(len(options), max(min_count, int(max_count_raw)))
    if min_count == 0 or max_count <= 0:
        return []
    return list(range(min(min_count, len(options))))
