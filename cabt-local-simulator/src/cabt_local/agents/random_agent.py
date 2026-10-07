from __future__ import annotations

import random
from typing import Any

from cabt_local.observation import random_legal_selection


class RandomAgent:
    agent_id = "random"

    def __init__(self, seed: int | None = None) -> None:
        self.rng = random.Random(seed)

    def __call__(self, obs_dict: dict) -> list[int]:
        return random_legal_selection(obs_dict, self.rng)


def agent(obs_dict: dict) -> list[int]:
    return RandomAgent().__call__(obs_dict)

