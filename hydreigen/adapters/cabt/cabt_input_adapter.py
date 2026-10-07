from __future__ import annotations

from typing import Any

from core.state_parser import NormalizedGameState, parse_state
from state_eval import getv


def parse_obs(obs_dict: dict) -> NormalizedGameState:
    return parse_state(obs_dict)


def parse_select(obs_dict: dict) -> Any:
    if not isinstance(obs_dict, dict):
        return None
    return getv(obs_dict, "select")
