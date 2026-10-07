from __future__ import annotations

from typing import Any

from state_eval import NormalizedState, normalize_state

NormalizedGameState = NormalizedState


def parse_state(raw_input: Any) -> NormalizedGameState:
    return normalize_state(raw_input)
