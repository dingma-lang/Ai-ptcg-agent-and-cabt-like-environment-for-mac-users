from __future__ import annotations

import time
import json
import tempfile
import unittest
from pathlib import Path

from cabt_local.agents.base import AgentWrapper
from cabt_local.agents.file_agent import _read_latest_trace
from cabt_local.agents.model_agent import parse_model_response
from cabt_local.agents.random_agent import RandomAgent
from cabt_local.observation import legal_options, random_legal_selection, redact_hidden_information, validate_selection


def obs(min_count: int = 1, max_count: int = 1) -> dict:
    return {
        "logs": [],
        "current": {
            "yourIndex": 0,
            "turn": 1,
            "players": [
                {"hand": [{"id": 1}], "handCount": 1, "prize": [None] * 6, "deckCount": 40, "active": [], "bench": []},
                {"hand": [{"id": 99}], "handCount": 1, "prize": [{"id": 77}], "deckCount": 40, "active": [], "bench": []},
            ],
        },
        "select": {"minCount": min_count, "maxCount": max_count, "option": [{"type": 7}, {"type": 14}, {"type": 3}]},
    }


class ObservationAgentTests(unittest.TestCase):
    def test_legal_options_and_validation(self) -> None:
        clean, errors = validate_selection(obs(), [1])
        self.assertEqual(clean, [1])
        self.assertEqual(errors, [])
        _, bad = validate_selection(obs(), [9])
        self.assertTrue(bad)

    def test_multi_index_selection(self) -> None:
        fixture = obs(min_count=2, max_count=2)
        clean, errors = validate_selection(fixture, [2, 0])
        self.assertEqual(clean, [2, 0])
        self.assertEqual(errors, [])
        self.assertEqual(len(random_legal_selection(fixture, RandomAgent(seed=1).rng)), 2)

    def test_optional_empty_selection_is_valid(self) -> None:
        clean, errors = validate_selection(obs(min_count=0, max_count=2), [])
        self.assertEqual(clean, [])
        self.assertEqual(errors, [])

    def test_hidden_information_redaction(self) -> None:
        redacted = redact_hidden_information(obs(), player=0)
        opponent = redacted["current"]["players"][1]
        self.assertEqual(opponent["hand"], [None])
        self.assertEqual(opponent["prize"], [None])

    def test_model_response_parser(self) -> None:
        parsed = parse_model_response({"selected_indexes": [2], "reason": "test"})
        self.assertEqual(parsed.selected_indexes, [2])

    def test_agent_wrapper_falls_back_on_invalid_response(self) -> None:
        wrapper = AgentWrapper(lambda _obs: [99], RandomAgent(seed=2), timeout_s=1.0)
        choice = wrapper(obs())
        self.assertTrue(choice)
        self.assertEqual(wrapper.invalid_response_count, 1)

    def test_agent_wrapper_timeout_falls_back(self) -> None:
        def slow(_obs: dict) -> list[int]:
            time.sleep(0.05)
            return [0]

        wrapper = AgentWrapper(slow, RandomAgent(seed=3), timeout_s=0.001)
        started = time.perf_counter()
        choice = wrapper(obs())
        elapsed = time.perf_counter() - started
        self.assertTrue(choice)
        self.assertLess(elapsed, 0.05)

    def test_empty_select_is_safe(self) -> None:
        self.assertEqual(legal_options({"select": None}), [])
        self.assertEqual(RandomAgent(seed=0)({"select": None}), [])

    def test_incremental_agent_trace_reader(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trace.jsonl"
            path.write_text(json.dumps({"reason": "first"}) + "\n", encoding="utf-8")
            first, offset = _read_latest_trace(path, 0)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"reason": "second"}) + "\n")
            second, next_offset = _read_latest_trace(path, offset)
        self.assertEqual(first["reason"], "first")
        self.assertEqual(second["reason"], "second")
        self.assertGreater(next_offset, offset)


if __name__ == "__main__":
    unittest.main()
