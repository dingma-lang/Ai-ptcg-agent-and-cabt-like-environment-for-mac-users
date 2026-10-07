from __future__ import annotations

import importlib.util
import json
import multiprocessing
import os
import sys
import tempfile
import uuid
from multiprocessing.connection import Connection
from pathlib import Path
from typing import Any, Callable

from .random_agent import RandomAgent


class ProcessFileAgent:
    """Run one agent file in its own interpreter to isolate deck-specific imports and globals."""

    def __init__(self, path: str | Path, function_name: str = "agent", timeout_s: float = 5.0) -> None:
        self.path = Path(path).expanduser().resolve()
        if not self.path.is_file():
            raise ValueError(f"Agent file does not exist: {self.path}")
        self.function_name = function_name
        self.timeout_s = timeout_s
        self.agent_id = f"file:{self.path}:{function_name}"
        self.fallback = RandomAgent(seed=0)
        self.last_trace: dict[str, Any] | None = None
        context = multiprocessing.get_context("spawn")
        parent, child = context.Pipe()
        self.connection: Connection | None = parent
        self.process = context.Process(
            target=_file_agent_worker,
            args=(str(self.path), self.function_name, child),
            name=f"cabt-agent-{self.path.stem}",
            daemon=True,
        )
        self.process.start()
        child.close()
        if not parent.poll(max(10.0, timeout_s)):
            self.close()
            raise TimeoutError(f"Timed out loading agent file: {self.path}")
        ready = parent.recv()
        if not isinstance(ready, dict) or not ready.get("ok"):
            self.close()
            raise RuntimeError(str((ready or {}).get("error") if isinstance(ready, dict) else ready))

    def __call__(self, observation: dict) -> list[int]:
        self.last_trace = None
        connection = self.connection
        if connection is None or not self.process.is_alive():
            return self.fallback(observation)
        try:
            connection.send({"command": "choose", "observation": observation})
            if not connection.poll(self.timeout_s):
                self.close()
                return self.fallback(observation)
            response = connection.recv()
        except (BrokenPipeError, EOFError, OSError):
            self.close()
            return self.fallback(observation)
        if not isinstance(response, dict) or not response.get("ok"):
            return self.fallback(observation)
        trace = response.get("trace")
        self.last_trace = trace if isinstance(trace, dict) else None
        selection = response.get("selection")
        return selection if isinstance(selection, list) else self.fallback(observation)

    def close(self) -> None:
        connection = self.connection
        self.connection = None
        if connection is not None:
            try:
                if self.process.is_alive():
                    connection.send({"command": "close"})
            except (BrokenPipeError, EOFError, OSError):
                pass
            connection.close()
        if self.process.is_alive():
            self.process.join(timeout=0.5)
        if self.process.is_alive():
            self.process.terminate()
            self.process.join(timeout=1.0)

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass


def parse_file_agent_spec(spec: str, timeout_s: float = 5.0) -> ProcessFileAgent:
    value = spec.removeprefix("file:")
    path_text, separator, function_name = value.rpartition(":")
    if not separator:
        path_text, function_name = value, "agent"
    if not path_text:
        raise ValueError("File agent spec must look like file:/path/to/agent.py:agent")
    return ProcessFileAgent(path_text, function_name or "agent", timeout_s)


def _file_agent_worker(path_text: str, function_name: str, connection: Connection) -> None:
    trace_directory = tempfile.TemporaryDirectory(prefix="cabt-agent-trace-")
    trace_path = Path(trace_directory.name) / "decisions.jsonl"
    trace_path.touch()
    os.environ["PTCG_AGENT_DECISION_LOG"] = str(trace_path)
    trace_offset = 0
    try:
        path = Path(path_text).resolve()
        os.chdir(path.parent)
        sys.path.insert(0, str(path.parent))
        module_name = f"cabt_user_agent_{uuid.uuid4().hex}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load module spec for {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        function: Callable[[dict], Any] = getattr(module, function_name)
        if not callable(function):
            raise TypeError(f"{function_name!r} is not callable in {path}")
        connection.send({"ok": True})
    except Exception as exc:
        connection.send({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
        connection.close()
        return

    while True:
        try:
            request = connection.recv()
        except EOFError:
            break
        if not isinstance(request, dict):
            continue
        if request.get("command") == "close":
            break
        if request.get("command") != "choose":
            continue
        try:
            selection = function(request.get("observation") or {})
            trace, trace_offset = _read_latest_trace(trace_path, trace_offset)
            connection.send({"ok": True, "selection": selection, "trace": trace})
        except Exception as exc:
            connection.send({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
    connection.close()
    trace_directory.cleanup()


def _read_latest_trace(path: Path, offset: int) -> tuple[dict[str, Any] | None, int]:
    latest = None
    try:
        with path.open(encoding="utf-8") as handle:
            handle.seek(offset)
            for line in handle:
                try:
                    value = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(value, dict):
                    latest = value
            return latest, handle.tell()
    except OSError:
        return None, offset
