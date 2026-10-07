from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .replay_visualizer import parse_battle_log


@dataclass(frozen=True)
class ReplayEngineStatus:
    available: bool
    status: str
    mode: str
    capabilities: list[str]
    limitations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "status": self.status,
            "mode": self.mode,
            "capabilities": list(self.capabilities),
            "limitations": list(self.limitations),
        }


def replay_engine_status() -> ReplayEngineStatus:
    return ReplayEngineStatus(
        available=True,
        status="log replay engine ready",
        mode="event-sourced reconstruction",
        capabilities=[
            "parse cabt/Kaggle text or HTML logs",
            "reconstruct public Active, Bench, attachments, damage, conditions, Stadium, and Prizes",
            "step backward or forward through immutable snapshots",
            "report parser coverage and every unclassified line",
            "inspect recorded JSONL observations and selected legal actions",
        ],
        limitations=[
            "does not calculate legal actions or card effects that are absent from the log",
            "does not reveal hidden hands, deck order, or face-down Prize identities",
            "does not replace the official cabt match engine",
        ],
    )


class LogReplayEngine:
    """Deterministic cursor over public states reconstructed from a battle log."""

    def __init__(self, payload: dict[str, Any]) -> None:
        if not payload.get("ok"):
            raise ValueError(str(payload.get("error") or "Invalid replay payload"))
        self.payload = payload
        self.events = list(payload.get("events") or [])
        self.snapshots = list(payload.get("snapshots") or [])
        self.position = -1

    @classmethod
    def from_text(cls, text: str) -> "LogReplayEngine":
        return cls(parse_battle_log(text))

    def reset(self) -> dict[str, Any]:
        self.position = -1
        return self.current()

    def seek(self, index: int) -> dict[str, Any]:
        if not self.events:
            self.position = -1
        else:
            self.position = max(0, min(int(index), len(self.events) - 1))
        return self.current()

    def step(self, amount: int = 1) -> dict[str, Any]:
        if not self.events:
            return self.current()
        return self.seek(self.position + int(amount))

    def current(self) -> dict[str, Any]:
        if self.position < 0 or not self.events:
            return {"position": -1, "event": None, "state": {"players": {}, "winner": ""}}
        state = self.snapshots[self.position] if self.position < len(self.snapshots) else {}
        return {
            "position": self.position,
            "event": deepcopy(self.events[self.position]),
            "state": deepcopy(state),
        }

    def audit(self) -> dict[str, Any]:
        return {
            "summary": deepcopy(self.payload.get("summary") or {}),
            "coverage": deepcopy(self.payload.get("coverage") or {}),
            "unparsed_lines": deepcopy(self.payload.get("unparsed_lines") or []),
        }
