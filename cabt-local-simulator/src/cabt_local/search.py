from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from .engine import CabtUnavailable, get_card_api
from .remote_engine import RemoteCabtSearch


@dataclass
class SearchHandle:
    search_id: Optional[int]
    state: Any


class SearchAdapter:
    """Thin wrapper around documented cabt search functions.

    Disabled by default in the runner because hidden-state inputs must be
    supplied by a legal inference model, not by full engine knowledge.
    """

    def __init__(self, cg_path: str | None = None) -> None:
        self.remote = False
        try:
            self.api = get_card_api(cg_path)
        except CabtUnavailable:
            self.api = RemoteCabtSearch()
            self.remote = True

    def begin(
        self,
        *,
        agent_observation: dict,
        your_deck: list[int],
        your_prize: list[int],
        opponent_deck: list[int],
        opponent_prize: list[int],
        opponent_hand: list[int],
        opponent_active: list[int],
        manual_coin: bool = False,
    ) -> SearchHandle:
        if not hasattr(self.api, "search_begin"):
            raise CabtUnavailable("search_begin is not available in this cabt API")
        if self.remote:
            state = self.api.search_begin(
                agent_observation=agent_observation,
                your_deck=your_deck,
                your_prize=your_prize,
                opponent_deck=opponent_deck,
                opponent_prize=opponent_prize,
                opponent_hand=opponent_hand,
                opponent_active=opponent_active,
                manual_coin=manual_coin,
            )
            return SearchHandle(_search_id(state), state.get("observation"))
        observation = self.api.to_observation_class(agent_observation)
        state = self.api.search_begin(
            observation,
            your_deck,
            your_prize,
            opponent_deck,
            opponent_prize,
            opponent_hand,
            opponent_active,
            manual_coin,
        )
        return SearchHandle(_search_id(state), state)

    def step(self, handle: SearchHandle, select: list[int]) -> SearchHandle:
        if handle.search_id is None:
            raise ValueError("search handle has no search_id")
        if self.remote:
            state = self.api.search_step(handle.search_id, select)
            return SearchHandle(_search_id(state), state.get("observation"))
        state = self.api.search_step(handle.search_id, select)
        return SearchHandle(_search_id(state) or handle.search_id, state)

    def release(self, handle: SearchHandle) -> None:
        try:
            if handle.search_id is not None and hasattr(self.api, "search_release"):
                self.api.search_release(handle.search_id)
        finally:
            if hasattr(self.api, "search_end"):
                self.api.search_end()


def _search_id(state: Any) -> Optional[int]:
    value = state.get("search_id") if isinstance(state, dict) else getattr(state, "searchId", None)
    return int(value) if value is not None else None
