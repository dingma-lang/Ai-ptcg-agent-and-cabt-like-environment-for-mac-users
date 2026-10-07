from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cabt_local.replay_engine import LogReplayEngine, replay_engine_status
from cabt_local.replay_visualizer import episode_payload_from_path, parse_battle_log


class ReplayVisualizerTests(unittest.TestCase):
    def test_parse_battle_log_infers_basic_timeline_and_board(self) -> None:
        payload = parse_battle_log(
            "\n".join(
                [
                    "Setup",
                    "Alice played Finizen to the Active Spot.",
                    "Bob played N's Zorua to the Active Spot.",
                    "Alice's Turn",
                    "Alice drew Buddy-Buddy Poffin.",
                    "Alice played Buddy-Buddy Poffin.",
                    "- Alice drew 2 cards and played them to the Bench.",
                    "   \u2022 Finizen",
                    "   \u2022 Dratini",
                    "Alice attached Basic {W} Energy to Finizen in the Active Spot.",
                    "Alice evolved Finizen to Palafin on the Bench.",
                    "Alice's Palafin used Zero to Hero.",
                    "Alice took a Prize card.",
                    "Alice wins.",
                ]
            )
        )
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["summary"]["winner"], "Alice")
        self.assertGreaterEqual(payload["summary"]["prizes_taken"], 1)
        final = payload["snapshots"][-1]
        self.assertEqual(final["players"]["Alice"]["active"], "Finizen")
        self.assertIn("Palafin", final["players"]["Alice"]["bench"])
        self.assertIn("Basic {W} Energy", final["players"]["Alice"]["attachments"]["Finizen"])

    def test_real_log_patterns_are_classified_and_reconstructed(self) -> None:
        payload = parse_battle_log(
            "\n".join(
                [
                    "Setup",
                    "Alice chose heads for the opening coin flip.",
                    "Alice won the coin toss.",
                    "Alice decided to go first.",
                    "Alice drew 7 cards for the opening hand.",
                    "   • Finizen, Palafin, Basic Water Energy",
                    "Alice played Finizen to the Active Spot.",
                    "Bob played Zorua to the Active Spot.",
                    "Alice's Turn",
                    "Alice attached Basic Water Energy to Finizen in the Active Spot.",
                    "Alice's Finizen used Call for Family.",
                    "- Alice drew 2 cards and played them to the Bench.",
                    "   • Finizen, Dratini",
                    "Alice ended their turn.",
                    "Bob's Turn",
                    "Bob's Zorua used Scratch on Alice’s Finizen for 50 damage.",
                    "Alice's Finizen was Knocked Out!",
                    "Bob took 2 Prize cards.",
                    "A card was added to Bob's hand.",
                    "A card was added to Bob's hand.",
                    "Alice's Dratini is now in the Active Spot.",
                    "Opponent conceded. Bob wins.",
                ]
            )
        )
        self.assertEqual(payload["coverage"]["percent"], 100.0)
        self.assertEqual(payload["summary"]["prizes_taken"], 2)
        self.assertEqual(payload["summary"]["winner"], "Bob")
        final = payload["snapshots"][-1]
        self.assertEqual(final["players"]["Alice"]["active"], "Dratini")
        self.assertIn("Finizen", final["players"]["Alice"]["bench"])
        self.assertEqual(final["players"]["Bob"]["hand_count"], 2)

    def test_html_log_and_replay_cursor(self) -> None:
        engine = LogReplayEngine.from_text(
            "<html><body><pre>Setup\nAlice played Finizen to the Active Spot.\nAlice's Turn\nAlice ended their turn.</pre></body></html>"
        )
        self.assertTrue(replay_engine_status().available)
        self.assertEqual(engine.audit()["coverage"]["percent"], 100.0)
        self.assertEqual(engine.seek(1)["state"]["players"]["Alice"]["active"], "Finizen")
        self.assertEqual(engine.step(1)["event"]["action"], "TURN_START")

    def test_episode_payload_from_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "episode.jsonl"
            path.write_text(
                '{"turn": 1, "player": 0, "features": {"legal_option_count": 1}, "legal_options": ["End"], "selected_indexes": [0]}\n',
                encoding="utf-8",
            )
            payload = episode_payload_from_path(path)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["summary"]["decisions"], 1)
        self.assertEqual(payload["decisions"][0]["selected_options"], ["End"])


if __name__ == "__main__":
    unittest.main()
