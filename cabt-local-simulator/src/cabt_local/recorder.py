from __future__ import annotations

import json
import os
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from .observation import legal_options, normalized_features, selected_options


SCHEMA_VERSION = 1


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class DecisionRecord:
    episode_id: str
    match_id: str
    player: int
    decision_index: int
    turn: int
    observation: dict
    memory: dict
    selected_indexes: list[int]
    deck_id: str
    opponent_deck_id: str
    agent_id: str
    strategy_id: str = ""
    agent_trace: Optional[dict[str, Any]] = None
    reward: Optional[float] = None
    done: bool = False
    winner: Optional[int] = None

    def to_json(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "episode_id": self.episode_id,
            "match_id": self.match_id,
            "player": self.player,
            "decision_index": self.decision_index,
            "turn": self.turn,
            "observation": self.observation,
            "features": normalized_features(self.observation, self.player),
            "memory": self.memory,
            "legal_options": legal_options(self.observation),
            "selected_indexes": self.selected_indexes,
            "selected_options": selected_options(self.observation, self.selected_indexes),
            "reward": self.reward,
            "done": self.done,
            "winner": self.winner,
            "deck_id": self.deck_id,
            "opponent_deck_id": self.opponent_deck_id,
            "agent_id": self.agent_id,
            "strategy_id": self.strategy_id,
            "agent_trace": self.agent_trace,
            "timestamp": utc_now(),
        }


class JsonlEpisodeRecorder:
    def __init__(self, episode_dir: str | Path, episode_id: str | None = None) -> None:
        self.episode_dir = Path(episode_dir)
        self.episode_dir.mkdir(parents=True, exist_ok=True)
        self.episode_id = episode_id or f"episode-{int(time.time() * 1000)}"
        self.path = self.episode_dir / f"{self.episode_id}.jsonl"
        self.invalid_path = self.episode_dir / f"{self.episode_id}.invalid.jsonl"
        self._decision_index = 0
        self._file = self.path.open("a", encoding="utf-8")
        self._invalid_file = self.invalid_path.open("a", encoding="utf-8")

    def record_decision(
        self,
        *,
        match_id: str,
        player: int,
        turn: int,
        observation: dict,
        memory: dict,
        selected_indexes: list[int],
        deck_id: str,
        opponent_deck_id: str,
        agent_id: str,
        strategy_id: str = "",
        agent_trace: Optional[dict[str, Any]] = None,
        reward: Optional[float] = None,
        done: bool = False,
        winner: Optional[int] = None,
    ) -> None:
        record = DecisionRecord(
            episode_id=self.episode_id,
            match_id=match_id,
            player=player,
            decision_index=self._decision_index,
            turn=turn,
            observation=observation,
            memory=memory,
            selected_indexes=selected_indexes,
            deck_id=deck_id,
            opponent_deck_id=opponent_deck_id,
            agent_id=agent_id,
            strategy_id=strategy_id,
            agent_trace=agent_trace,
            reward=reward,
            done=done,
            winner=winner,
        )
        self._decision_index += 1
        self._write(self._file, record.to_json())

    def record_invalid_response(self, payload: dict[str, Any]) -> None:
        safe = {k: redact_secret(v) for k, v in payload.items() if "token" not in k.lower() and "key" not in k.lower()}
        safe["timestamp"] = utc_now()
        self._write(self._invalid_file, safe)

    def close(self) -> None:
        self._file.close()
        self._invalid_file.close()

    def _write(self, f: Any, payload: dict[str, Any]) -> None:
        f.write(json.dumps(payload, sort_keys=True, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())

    def __enter__(self) -> "JsonlEpisodeRecorder":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()


def redact_secret(value: Any) -> Any:
    if isinstance(value, str) and len(value) > 12:
        return value[:4] + "...REDACTED"
    return value


class EpisodeReader:
    def __init__(self, episode_dir: str | Path) -> None:
        self.episode_dir = Path(episode_dir)

    def rows(self) -> Iterable[dict[str, Any]]:
        for path in sorted(self.episode_dir.glob("*.jsonl")):
            if path.name.endswith(".invalid.jsonl"):
                continue
            with path.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue

    def stats(self) -> dict[str, Any]:
        episodes: dict[str, dict[str, Any]] = {}
        invalid_count = 0
        for path in self.episode_dir.glob("*.invalid.jsonl"):
            with path.open(encoding="utf-8") as f:
                invalid_count += sum(1 for _ in f)
        for row in self.rows():
            eid = row.get("episode_id", "")
            ep = episodes.setdefault(eid, {"decisions": 0, "winner": None, "turns": 0, "matchups": set()})
            ep["decisions"] += 1
            ep["turns"] = max(ep["turns"], int(row.get("turn") or 0))
            if row.get("done"):
                ep["winner"] = row.get("winner")
            ep["matchups"].add((row.get("deck_id"), row.get("opponent_deck_id")))
        wins = sum(1 for ep in episodes.values() if ep["winner"] == 0)
        losses = sum(1 for ep in episodes.values() if ep["winner"] == 1)
        draws = sum(1 for ep in episodes.values() if ep["winner"] is None)
        games = len(episodes)
        return {
            "games": games,
            "wins_player0": wins,
            "losses_player0": losses,
            "draws_or_unknown": draws,
            "average_turns": (sum(ep["turns"] for ep in episodes.values()) / games) if games else 0.0,
            "invalid_model_responses": invalid_count,
        }


def split_episodes(episode_dir: str | Path, train_fraction: float = 0.8, seed: int = 1) -> dict[str, list[str]]:
    paths = sorted(str(path) for path in Path(episode_dir).glob("*.jsonl") if not path.name.endswith(".invalid.jsonl"))
    rng = random.Random(seed)
    rng.shuffle(paths)
    cut = int(len(paths) * train_fraction)
    return {"train": paths[:cut], "validation": paths[cut:]}


def jsonl_to_parquet(episode_dir: str | Path, output_path: str | Path) -> Path:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except Exception as exc:
        raise RuntimeError("Install the optional 'parquet' dependency to export Parquet.") from exc
    rows = list(EpisodeReader(episode_dir).rows())
    table = pa.Table.from_pylist(rows)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, output)
    return output
