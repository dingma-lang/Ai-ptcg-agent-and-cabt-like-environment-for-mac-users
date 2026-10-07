from __future__ import annotations

import concurrent.futures
import time
from typing import Any, Callable, Protocol

from cabt_local.observation import random_legal_selection, validate_selection


class AgentFailure(RuntimeError):
    pass


class AgentProtocol(Protocol):
    agent_id: str

    def __call__(self, obs_dict: dict) -> list[int]:
        ...


class AgentWrapper:
    def __init__(self, agent: Callable[[dict], list[int]], fallback: Callable[[dict], list[int]], agent_id: str = "callable", timeout_s: float = 5.0) -> None:
        self.agent = agent
        self.fallback = fallback
        self.agent_id = agent_id
        self.timeout_s = timeout_s
        self.last_error: str | None = None
        self.last_latency_s: float = 0.0
        self.invalid_response_count = 0

    def __call__(self, obs_dict: dict) -> list[int]:
        started = time.perf_counter()
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(self.agent, obs_dict)
            raw = future.result(timeout=self.timeout_s)
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            self.last_latency_s = time.perf_counter() - started
            return self.fallback(obs_dict)
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
        self.last_latency_s = time.perf_counter() - started
        clean, errors = validate_selection(obs_dict, raw)
        if errors:
            self.last_error = "; ".join(errors)
            self.invalid_response_count += 1
            return self.fallback(obs_dict)
        self.last_error = None
        return clean
