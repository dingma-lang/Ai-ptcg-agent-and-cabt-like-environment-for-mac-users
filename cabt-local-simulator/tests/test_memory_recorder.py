from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cabt_local.memory import MatchMemory
from cabt_local.recorder import EpisodeReader, JsonlEpisodeRecorder, split_episodes


def fixture_obs() -> dict:
    return {
        "logs": [{"type": 4, "playerIndex": 0, "cardId": 107}],
        "current": {
            "yourIndex": 0,
            "turn": 3,
            "supporterPlayed": True,
            "stadiumPlayed": False,
            "energyAttached": True,
            "retreated": False,
            "stadium": [{"id": 1262}],
            "players": [
                {
                    "active": [{"id": 107, "hp": 340, "maxHp": 340, "energyCards": [{"id": 3}], "tools": []}],
                    "bench": [{"id": 903, "hp": 100, "maxHp": 100, "energyCards": [{"id": 4}], "tools": []}],
                    "hand": [{"id": 1227}],
                    "handCount": 1,
                    "deckCount": 34,
                    "discard": [{"id": 105}],
                    "prize": [None] * 5,
                },
                {"active": [{"id": 292}], "bench": [], "hand": [], "handCount": 4, "deckCount": 35, "discard": [], "prize": [None] * 6},
            ],
        },
        "select": {"minCount": 1, "maxCount": 1, "option": [{"type": 13, "attackId": 10702}]},
    }


class MemoryRecorderTests(unittest.TestCase):
    def test_memory_initialization_update_and_reset(self) -> None:
        memory = MatchMemory(player=0)
        memory.update(fixture_obs())
        self.assertEqual(memory.turn, 3)
        self.assertTrue(memory.once_per_turn["supporterPlayed"])
        self.assertTrue(memory.deck_facts["zero_to_hero_completed_visible"])
        memory.reset()
        self.assertEqual(memory.decision_count, 0)
        self.assertEqual(memory.prize_counts, {})

    def test_jsonl_recording_and_stats_survive_partial_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with JsonlEpisodeRecorder(tmp, episode_id="ep1") as rec:
                memory = MatchMemory(player=0)
                memory.update(fixture_obs())
                rec.record_decision(
                    match_id="m1",
                    player=0,
                    turn=3,
                    observation=fixture_obs(),
                    memory=memory.as_dict(),
                    selected_indexes=[0],
                    deck_id="a",
                    opponent_deck_id="b",
                    agent_id="random",
                    agent_trace={"reason": "Take the highest-scored attack", "legal_options": [{"index": 0, "score": 12000}]},
                    done=True,
                    winner=0,
                )
                rec.record_invalid_response({"api_key": "secret-value-12345", "error": "bad index"})
            Path(tmp, "partial.jsonl").write_text("{not-json\n", encoding="utf-8")
            rows = list(EpisodeReader(tmp).rows())
            stats = EpisodeReader(tmp).stats()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["schema_version"], 1)
        self.assertEqual(rows[0]["agent_trace"]["legal_options"][0]["score"], 12000)
        self.assertEqual(stats["games"], 1)
        self.assertEqual(stats["invalid_model_responses"], 1)

    def test_episode_split_is_by_complete_episode_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("a.jsonl", "b.jsonl", "c.jsonl"):
                Path(tmp, name).write_text(json.dumps({"episode_id": name}) + "\n", encoding="utf-8")
            split = split_episodes(tmp, train_fraction=0.67, seed=2)
        self.assertEqual(len(split["train"]) + len(split["validation"]), 3)


if __name__ == "__main__":
    unittest.main()
