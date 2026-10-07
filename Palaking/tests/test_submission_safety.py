from __future__ import annotations

import ast
import importlib.util
import tempfile
import unittest
from pathlib import Path

import config
from agent import agent
from make_submission import build_file_list, make_archive, validate_archive
from state_eval import CTX_MAIN, OPT_END


FORBIDDEN_IMPORTS = {
    "pyautogui",
    "selenium",
    "cv2",
    "pytesseract",
    "Quartz",
    "AppKit",
}


class SubmissionSafetyTests(unittest.TestCase):
    def test_kaggle_entry_imports_submission_agent(self):
        root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location("repo_main_for_safety_test", root / "main.py")
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        main = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(main)

        self.assertTrue(callable(agent))
        self.assertTrue(callable(main.agent))

    def test_submission_mode_config_forces_safe_flags(self):
        self.assertEqual(config.MODE, "CABT_SUBMISSION_MODE")
        self.assertTrue(config.SUBMISSION_SAFE)
        self.assertFalse(config.ENABLE_UI_AUTOMATION)
        self.assertFalse(config.ENABLE_MEMORY_FILE_WRITES)

    def test_no_forbidden_imports_in_submission_path(self):
        root = Path(__file__).resolve().parents[1]
        paths = [root / "agent.py", root / "main.py", root / "config.py"]
        paths.extend((root / "adapters" / "cabt").glob("*.py"))
        paths.extend((root / "core").glob("*.py"))
        paths.extend(root / name for name in ["policy.py", "action_classifier.py", "state_eval.py", "turn_sequencer.py"])
        imported = set()
        for path in paths:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".")[0])
        self.assertFalse(imported & FORBIDDEN_IMPORTS)

    def test_agent_returns_legal_indices_and_safe_empty_values(self):
        self.assertEqual(agent({"current": {}, "logs": []}), [])
        self.assertEqual(agent({"current": {}, "logs": [], "select": {"context": CTX_MAIN, "type": 0, "minCount": 0, "maxCount": 0, "option": []}}), [])

        obs = {
            "current": {
                "turn": 3,
                "yourIndex": 0,
                "firstPlayer": 0,
                "result": -1,
                "players": [{"active": [], "bench": [], "deckCount": 40, "discard": [], "prize": [], "hand": [], "handCount": 0}],
            },
            "logs": [],
            "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": [{"type": OPT_END}]},
        }
        result = agent(obs)
        self.assertIsInstance(result, list)
        self.assertTrue(all(isinstance(idx, int) for idx in result))
        self.assertEqual(result, [0])

    def test_submission_archive_excludes_forbidden_outputs(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "submission.zip"
            make_archive(archive, build_file_list(root), root)
            self.assertEqual(validate_archive(archive), [])
            import zipfile

            with zipfile.ZipFile(archive, "r") as handle:
                names = handle.namelist()
        self.assertIn("agent.py", names)
        self.assertIn("adapters/cabt/submission_entry.py", names)
        self.assertFalse(any(name.startswith("local_results/") or name.startswith("memory/") for name in names))


if __name__ == "__main__":
    unittest.main()
