from __future__ import annotations

import base64
import io
import tempfile
import unittest
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cabt_local.engine import CabtUnavailable, describe_environment, native_file_kind
from cabt_local.agents.random_agent import RandomAgent
from cabt_local.deck import load_deck
from cabt_local.runner import (
    TwoDeckRunner,
    agent_code,
    agent_name_from_spec,
    formal_match_id,
    is_terminal_observation,
    winner_from_observation,
    write_visualizer_html,
)
from cabt_local.webapp import (
    build_status,
    discover_agents,
    find_agent_profile,
    import_agent_payload,
    resolve_match_deck,
    safe_relative_path,
)


class RunnerEngineTests(unittest.TestCase):
    def test_environment_report_contains_runtime_fields(self) -> None:
        report = describe_environment(Path.cwd()).to_dict()
        self.assertIn("python_version", report)
        self.assertIn("native_library", report)

    def test_html_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "replay.html"
            write_visualizer_html(path, '[{"current":{"turn":0,"result":-1,"players":[]}}]')
            self.assertTrue(path.exists())
            page = path.read_text(encoding="utf-8")
            self.assertIn("Battle Lab | Battle Replay", page)
            self.assertIn("Start of turn", page)
            self.assertIn("Actions in order", page)

    def test_formal_match_name_uses_index_local_time_and_agent_codes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            local_time = datetime(2026, 9, 2, 15, 40, tzinfo=timezone(timedelta(hours=-4)))
            first = formal_match_id(tmp, "Palaking", "Palaking 1.25", local_time)
            second = formal_match_id(tmp, "Palaking", "N's Zoroark", local_time)
            self.assertEqual(first, "battle1_15-40_2026-09-02_pal_vs_pal")
            self.assertEqual(second, "battle2_15-40_2026-09-02_pal_vs_nsz")

    def test_agent_name_and_code_from_file_spec(self) -> None:
        self.assertEqual(agent_name_from_spec("file:../Palaking/agent.py:agent"), "Palaking")
        self.assertEqual(agent_code("N's Zoroark"), "nsz")

    def test_native_file_kind_identifies_linux_elf_x86_64(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "libcg.so"
            header = bytearray(64)
            header[:6] = b"\x7fELF\x02\x01"
            header[18:20] = (62).to_bytes(2, "little")
            path.write_bytes(bytes(header))
            self.assertEqual(native_file_kind(path), "Linux ELF x86-64")

    def test_cabt_result_minus_one_is_not_terminal(self) -> None:
        observation = {"current": {"result": -1}}
        self.assertFalse(is_terminal_observation(observation))
        observation["current"]["result"] = 0
        self.assertTrue(is_terminal_observation(observation))
        self.assertEqual(winner_from_observation(observation), 0)

    def test_web_status_and_safe_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "decks").mkdir()
            (root / "decks" / "deck_a.csv").write_text("\n".join(["1"] * 60) + "\n", encoding="utf-8")
            status = build_status(root)
            self.assertEqual(status["decks"][0]["card_count"], 60)
            self.assertTrue(status["replay_engine"]["available"])
            with self.assertRaises(ValueError):
                safe_relative_path(root, "../outside.csv")

    def test_imported_agent_zip_pairs_agent_and_deck(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "simulator"
            root.mkdir()
            archive_data = io.BytesIO()
            with zipfile.ZipFile(archive_data, "w") as archive:
                archive.writestr("submission/agent.py", "def agent(obs_dict):\n    return []\n")
                archive.writestr("submission/deck.csv", "\n".join(["1"] * 60) + "\n")
                archive.writestr("submission/helper.py", "VALUE = 1\n")
            result = import_agent_payload(
                root,
                {
                    "filename": "submission.zip",
                    "name": "Test Agent",
                    "content_base64": base64.b64encode(archive_data.getvalue()).decode("ascii"),
                },
            )
            self.assertTrue(result["ok"])
            self.assertTrue(result["deck_report"]["ok"])
            profile = find_agent_profile(root, result["agent"]["spec"])
            self.assertIsNotNone(profile)
            self.assertEqual(resolve_match_deck(root, "auto", profile, "missing.csv").name, "deck.csv")
            self.assertIn("Test Agent", {row["name"] for row in discover_agents(root)})

    def test_imported_python_agent_uses_selected_fallback_deck(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "simulator"
            (root / "decks").mkdir(parents=True)
            (root / "decks" / "deck_a.csv").write_text("\n".join(["1"] * 60) + "\n", encoding="utf-8")
            source = b"def agent(obs_dict):\n    return []\n"
            result = import_agent_payload(
                root,
                {
                    "filename": "agent.py",
                    "content_base64": base64.b64encode(source).decode("ascii"),
                    "deck": "decks/deck_a.csv",
                },
            )
            self.assertTrue(result["agent"]["ready"])
            self.assertEqual(result["deck_report"]["card_count"], 60)

    def test_agent_zip_rejects_parent_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "simulator"
            root.mkdir()
            archive_data = io.BytesIO()
            with zipfile.ZipFile(archive_data, "w") as archive:
                archive.writestr("../agent.py", "def agent(obs_dict): return []\n")
            with self.assertRaisesRegex(ValueError, "Unsafe path"):
                import_agent_payload(
                    root,
                    {
                        "filename": "unsafe.zip",
                        "content_base64": base64.b64encode(archive_data.getvalue()).decode("ascii"),
                    },
                )

    def test_random_versus_random_integration_skips_when_cabt_unavailable(self) -> None:
        runner = TwoDeckRunner(out_dir=tempfile.mkdtemp())
        root = Path(__file__).resolve().parents[1]
        try:
            result = runner.play(
                load_deck(root / "decks" / "deck_a.csv"),
                load_deck(root / "decks" / "deck_b.csv"),
                RandomAgent(seed=11),
                RandomAgent(seed=29),
                prefer_kaggle_env=False,
            )
        except CabtUnavailable:
            self.skipTest("official cabt engine is unavailable on this machine")
        self.assertGreater(result.decision_count, 0)
        self.assertIn(result.winner, (0, 1, None))


if __name__ == "__main__":
    unittest.main()
