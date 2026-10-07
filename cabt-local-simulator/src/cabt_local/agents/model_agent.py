from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cabt_local.memory import MatchMemory
from cabt_local.observation import legal_options, validate_selection
from .base import AgentWrapper
from .random_agent import RandomAgent


@dataclass
class ModelResponse:
    selected_indexes: list[int]
    reason: str = ""


class PromptBuilder:
    def __init__(self, strategy_path: str | Path | None = None) -> None:
        self.strategy_path = Path(strategy_path) if strategy_path else None

    def build(self, obs: dict, memory: MatchMemory | None = None) -> str:
        strategy = self.strategy_path.read_text(encoding="utf-8") if self.strategy_path and self.strategy_path.exists() else ""
        payload = {
            "static_deck_strategy": strategy,
            "current_legal_observation": obs,
            "structured_match_memory": memory.as_dict() if memory else {},
            "legal_choices": legal_options(obs),
            "required_response_format": {"selected_indexes": [0], "reason": "short reason"},
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)


class LocalHttpModelAgent:
    def __init__(self, endpoint: str | None = None, strategy_path: str | Path | None = None, timeout_s: float = 5.0) -> None:
        self.endpoint = endpoint or os.getenv("CABT_LOCAL_MODEL_ENDPOINT", "")
        self.timeout_s = timeout_s
        self.builder = PromptBuilder(strategy_path or os.getenv("CABT_LOCAL_STRATEGY_PROMPT", ""))
        self.agent_id = "local-http-model"
        self.last_reason = ""

    def __call__(self, obs_dict: dict) -> list[int]:
        if not self.endpoint:
            raise RuntimeError("CABT_LOCAL_MODEL_ENDPOINT is not configured")
        body = json.dumps({"prompt": self.builder.build(obs_dict)}).encode("utf-8")
        req = urllib.request.Request(self.endpoint, data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"local model request failed: {exc}") from exc
        parsed = parse_model_response(payload)
        clean, errors = validate_selection(obs_dict, parsed.selected_indexes)
        if errors:
            raise RuntimeError("; ".join(errors))
        self.last_reason = parsed.reason
        return clean


def parse_model_response(payload: Any) -> ModelResponse:
    if isinstance(payload, str):
        payload = json.loads(payload)
    if not isinstance(payload, dict):
        raise ValueError("Model response must be a JSON object")
    indexes = payload.get("selected_indexes")
    if not isinstance(indexes, list):
        raise ValueError("Model response missing selected_indexes list")
    return ModelResponse([int(idx) for idx in indexes], str(payload.get("reason", "")))


def make_http_model_agent(timeout_s: float = 5.0) -> AgentWrapper:
    fallback = RandomAgent(seed=0)
    return AgentWrapper(LocalHttpModelAgent(timeout_s=timeout_s), fallback, agent_id="local-http-model", timeout_s=timeout_s + 0.5)

