from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from .agents.callable_agent import make_callable_agent
from .agents.file_agent import parse_file_agent_spec
from .agents.model_agent import make_http_model_agent
from .agents.random_agent import RandomAgent
from .deck import load_deck
from .engine import CabtInitializationError, CabtUnavailable, MatchResult, get_game_api, run_kaggle_env_match, startdata_to_dict, write_summary
from .memory import MatchMemory
from .observation import acting_player, int_or, legal_options, validate_selection
from .official_visualizer import write_official_replay
from .recorder import JsonlEpisodeRecorder
from .remote_engine import RemoteCabtGame


AgentCallable = Callable[[dict], list[int]]


def resolve_agent(spec: str, timeout_s: float = 5.0) -> AgentCallable:
    if spec == "random":
        return RandomAgent(seed=0)
    if spec in {"http", "model", "local-http"}:
        return make_http_model_agent(timeout_s=timeout_s)
    if spec.startswith("module:"):
        return make_callable_agent(spec, timeout_s=timeout_s)
    if spec.startswith("file:"):
        return parse_file_agent_spec(spec, timeout_s=timeout_s)
    raise ValueError(f"Unknown agent spec {spec!r}. Use random, http, module:pkg.mod:function, or file:path.py:function.")


class TwoDeckRunner:
    def __init__(self, out_dir: str | Path = "data", cg_path: str | Path | None = None, timeout_s: float = 5.0) -> None:
        self.out_dir = Path(out_dir)
        self.cg_path = cg_path
        self.timeout_s = timeout_s

    def play_paths(
        self,
        deck_a_path: str | Path,
        deck_b_path: str | Path,
        agent_a_spec: str,
        agent_b_spec: str,
        record: bool = False,
        prefer_kaggle_env: bool = True,
        agent_a_name: str | None = None,
        agent_b_name: str | None = None,
    ) -> MatchResult:
        deck_a = load_deck(deck_a_path)
        deck_b = load_deck(deck_b_path)
        agent_a = resolve_agent(agent_a_spec, self.timeout_s)
        agent_b = resolve_agent(agent_b_spec, self.timeout_s)
        try:
            return self.play(
                deck_a,
                deck_b,
                agent_a,
                agent_b,
                str(deck_a_path),
                str(deck_b_path),
                record,
                prefer_kaggle_env,
                agent_a_name or agent_name_from_spec(agent_a_spec),
                agent_b_name or agent_name_from_spec(agent_b_spec),
            )
        finally:
            for loaded_agent in (agent_a, agent_b):
                close = getattr(loaded_agent, "close", None)
                if callable(close):
                    close()

    def play(
        self,
        deck_a: list[int],
        deck_b: list[int],
        agent_a: AgentCallable,
        agent_b: AgentCallable,
        deck_a_id: str = "deck_a",
        deck_b_id: str = "deck_b",
        record: bool = False,
        prefer_kaggle_env: bool = True,
        agent_a_name: str | None = None,
        agent_b_name: str | None = None,
    ) -> MatchResult:
        match_id = formal_match_id(
            self.out_dir,
            agent_a_name or getattr(agent_a, "agent_id", "agent-a"),
            agent_b_name or getattr(agent_b, "agent_id", "agent-b"),
        )
        replay_path = self.out_dir / "replays" / f"{match_id}.html"
        summary_path = self.out_dir / "summaries" / f"{match_id}.json"
        recorder = JsonlEpisodeRecorder(self.out_dir / "episodes", episode_id=match_id) if record else None
        try:
            if prefer_kaggle_env:
                try:
                    result = self._play_kaggle(deck_a, deck_b, agent_a, agent_b, deck_a_id, deck_b_id, match_id, replay_path, recorder)
                    write_summary(summary_path, result)
                    return result
                except CabtUnavailable:
                    pass
            result = self._play_direct_cg(deck_a, deck_b, agent_a, agent_b, deck_a_id, deck_b_id, match_id, replay_path, recorder)
            write_summary(summary_path, result)
            return result
        finally:
            if recorder is not None:
                recorder.close()

    def _play_kaggle(
        self,
        deck_a: list[int],
        deck_b: list[int],
        agent_a: AgentCallable,
        agent_b: AgentCallable,
        deck_a_id: str,
        deck_b_id: str,
        match_id: str,
        replay_path: Path,
        recorder: Optional[JsonlEpisodeRecorder],
    ) -> MatchResult:
        memories = [MatchMemory(0), MatchMemory(1)]
        wrapped = [
            self._recording_agent(agent_a, memories[0], recorder, match_id, 0, deck_a_id, deck_b_id),
            self._recording_agent(agent_b, memories[1], recorder, match_id, 1, deck_b_id, deck_a_id),
        ]
        result = run_kaggle_env_match(deck_a, deck_b, wrapped[0], wrapped[1], replay_path)
        result.match_id = match_id
        return result

    def _play_direct_cg(
        self,
        deck_a: list[int],
        deck_b: list[int],
        agent_a: AgentCallable,
        agent_b: AgentCallable,
        deck_a_id: str,
        deck_b_id: str,
        match_id: str,
        replay_path: Path,
        recorder: Optional[JsonlEpisodeRecorder],
    ) -> MatchResult:
        engine_name = "cg.game"
        try:
            game = get_game_api(self.cg_path)
        except CabtUnavailable:
            game = RemoteCabtGame(timeout_s=max(15.0, self.timeout_s))
            game.health()
            engine_name = "cg.game via Lima/Rosetta worker"
        memories = [MatchMemory(0), MatchMemory(1)]
        obs = None
        start_data = None
        decisions = 0
        winner: Optional[int] = None
        termination = ""
        try:
            obs, start_data = game.battle_start(deck_a, deck_b)
            if obs is None:
                details = startdata_to_dict(start_data)
                raise CabtInitializationError("battle_start returned no observation: " + json.dumps(details, sort_keys=True))
            while decisions < 10000:
                if is_terminal_observation(obs):
                    winner = winner_from_observation(obs)
                    termination = "terminal observation"
                    break
                if not legal_options(obs):
                    termination = "no legal options in observation"
                    break
                player = acting_player(obs, default=0)
                player = player if player in (0, 1) else 0
                agent = agent_a if player == 0 else agent_b
                memory = memories[player]
                memory.update(obs)
                raw_selection = agent(obs)
                agent_trace = decision_trace_from_agent(agent)
                selected, errors = validate_selection(obs, raw_selection)
                if errors:
                    if recorder is not None:
                        recorder.record_invalid_response({"match_id": match_id, "player": player, "raw": raw_selection, "errors": errors})
                    selected = RandomAgent(seed=decisions)(obs)
                if recorder is not None:
                    recorder.record_decision(
                        match_id=match_id,
                        player=player,
                        turn=int_or((obs.get("current") or {}).get("turn", 0), 0),
                        observation=obs,
                        memory=memory.as_dict(),
                        selected_indexes=selected,
                        deck_id=deck_a_id if player == 0 else deck_b_id,
                        opponent_deck_id=deck_b_id if player == 0 else deck_a_id,
                        agent_id=getattr(agent, "agent_id", "callable"),
                        agent_trace=agent_trace,
                    )
                obs = game.battle_select(selected)
                decisions += 1
            else:
                termination = "max decision limit reached"
            try:
                replay_text = game.visualize_data()
                write_visualizer_html(replay_path, replay_text)
            except Exception:
                pass
            return MatchResult(
                match_id=match_id,
                engine=engine_name,
                winner=winner,
                rewards=[],
                done=winner is not None or termination != "",
                turn_count=int_or((obs.get("current") or {}).get("turn", 0), 0) if isinstance(obs, dict) else 0,
                decision_count=decisions,
                termination_reason=termination,
                replay_path=str(replay_path) if replay_path.exists() else None,
            )
        finally:
            try:
                game.battle_finish()
            except Exception:
                pass

    def _recording_agent(
        self,
        agent: AgentCallable,
        memory: MatchMemory,
        recorder: Optional[JsonlEpisodeRecorder],
        match_id: str,
        player: int,
        deck_id: str,
        opponent_deck_id: str,
    ) -> AgentCallable:
        def wrapped(obs: dict) -> list[int]:
            memory.update(obs)
            raw = agent(obs)
            agent_trace = decision_trace_from_agent(agent)
            selected, errors = validate_selection(obs, raw)
            if errors:
                if recorder is not None:
                    recorder.record_invalid_response({"match_id": match_id, "player": player, "raw": raw, "errors": errors})
                selected = RandomAgent(seed=memory.decision_count)(obs)
            if recorder is not None:
                recorder.record_decision(
                    match_id=match_id,
                    player=player,
                    turn=int_or((obs.get("current") or {}).get("turn", 0), 0),
                    observation=obs,
                    memory=memory.as_dict(),
                    selected_indexes=selected,
                    deck_id=deck_id,
                    opponent_deck_id=opponent_deck_id,
                    agent_id=getattr(agent, "agent_id", "callable"),
                    agent_trace=agent_trace,
                )
            return selected

        return wrapped


def decision_trace_from_agent(agent: AgentCallable) -> dict[str, Any] | None:
    trace = getattr(agent, "last_trace", None)
    return dict(trace) if isinstance(trace, dict) else None


def formal_match_id(
    out_dir: str | Path,
    agent_a_name: str,
    agent_b_name: str,
    local_time: datetime | None = None,
) -> str:
    timestamp = local_time or datetime.now().astimezone()
    battle_index = reserve_battle_index(Path(out_dir))
    return (
        f"battle{battle_index}_{timestamp:%H-%M}_{timestamp:%Y-%m-%d}_"
        f"{agent_code(agent_a_name)}_vs_{agent_code(agent_b_name)}"
    )


def reserve_battle_index(out_dir: Path) -> int:
    index_dir = out_dir / ".battle_indexes"
    index_dir.mkdir(parents=True, exist_ok=True)
    existing = [int(path.name) for path in index_dir.iterdir() if path.name.isdigit()]
    candidate = max(existing, default=0) + 1
    while True:
        marker = index_dir / str(candidate)
        try:
            marker.mkdir()
            return candidate
        except FileExistsError:
            candidate += 1


def agent_name_from_spec(spec: str) -> str:
    if spec.startswith("file:"):
        value = spec.removeprefix("file:")
        path_text, separator, _function_name = value.rpartition(":")
        path = Path(path_text if separator else value)
        parent = path.parent
        if parent.name.lower() in {"submission", "sample_submission"}:
            parent = parent.parent
        return parent.name or path.stem
    if spec.startswith("module:"):
        return spec.removeprefix("module:").split(":", 1)[0].split(".")[-1]
    return spec


def agent_code(name: str) -> str:
    clean = re.sub(r"[^a-z0-9]", "", str(name).lower())
    return (clean[:3] or "agt").ljust(3, "x")


def is_terminal_observation(obs: dict) -> bool:
    current = obs.get("current") or {}
    result = int_or(current.get("result"), -1)
    if current.get("winner") is not None or result != -1:
        return True
    return bool(current.get("finished") or current.get("done") or current.get("isFinished"))


def winner_from_observation(obs: dict) -> Optional[int]:
    current = obs.get("current") or {}
    for key in ("result", "winner", "winnerIndex", "winningPlayer"):
        value = current.get(key)
        if value in (0, 1, "0", "1"):
            return int(value)
    return None


def write_visualizer_html(path: Path, visualizer_text: str) -> None:
    write_official_replay(path, visualizer_text)
