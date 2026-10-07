from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, DefaultDict, Dict, Set

from state_eval import card_id, enum_int, getv


class MatchMemory:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.known_by_player: DefaultDict[int, Set[int]] = defaultdict(set)
        self.decision_count = 0
        self.total_time_sec = 0.0
        self.last_result = -1

    def update_from_obs(self, obs: Any, elapsed_sec: float = 0.0) -> None:
        self.decision_count += 1
        self.total_time_sec += elapsed_sec
        current = getv(obs, "current")
        if enum_int(getv(current, "result", -1), -1) != -1:
            self.last_result = enum_int(getv(current, "result", -1), -1)
            self.reset()
            return

        for log in getv(obs, "logs", []) or []:
            player = enum_int(getv(log, "playerIndex", -1), -1)
            cid = getv(log, "cardId")
            if player in (0, 1) and cid is not None:
                try:
                    self.known_by_player[player].add(int(cid))
                except (TypeError, ValueError):
                    pass
            for key in ("cardIdActive", "cardIdBench", "cardIdBefore", "cardIdAfter", "cardIdTarget"):
                cid = getv(log, key)
                if player in (0, 1) and cid is not None:
                    try:
                        self.known_by_player[player].add(int(cid))
                    except (TypeError, ValueError):
                        pass

        players = getv(current, "players", []) or []
        for player_index, player in enumerate(players[:2] if isinstance(players, list) else []):
            for zone in ("discard", "hand", "prize"):
                cards = getv(player, zone, []) or []
                if not isinstance(cards, list):
                    continue
                for card in cards:
                    cid = card_id(card)
                    if cid is not None:
                        self.known_by_player[player_index].add(cid)

    @property
    def slow_mode(self) -> bool:
        if self.decision_count < 100:
            return False
        average = self.total_time_sec / max(1, self.decision_count)
        return average > 0.15


GLOBAL_MEMORY = MatchMemory()


def begin_decision_timer() -> float:
    return time.perf_counter()


def finish_decision(obs: Any, started_at: float) -> None:
    GLOBAL_MEMORY.update_from_obs(obs, time.perf_counter() - started_at)
