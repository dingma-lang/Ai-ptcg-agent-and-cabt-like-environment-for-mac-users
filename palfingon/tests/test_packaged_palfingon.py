from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from make_submission import build_file_list, make_archive
from tests.test_palafin_strategy import card, obs_for, pokemon
from tests.test_expert_battles import finisher_obs
from tests.test_stall_regressions import recorded
from state_eval import OPT_ATTACK, OPT_END, OPT_PLAY


class PackagedPalfingonTests(unittest.TestCase):
    def test_isolated_archive_import_and_real_decisions(self):
        root = Path(__file__).resolve().parents[1]
        cases = [
            ({"current": None, "select": None}, [int(x) for x in (root / "deck.csv").read_text().splitlines()]),
            (obs_for(pokemon(105), hand=[card(1086)], options=[{"type": OPT_END}, {"type": OPT_PLAY, "cardId": 1086}]), [1]),
            (obs_for(pokemon(51, [3]), options=[{"type": OPT_END}, {"type": OPT_ATTACK, "attackId": 51}]), [1]),
            (obs_for(pokemon(105), hand=[card(1213)], options=[{"type": OPT_END}, {"type": OPT_PLAY, "cardId": 1213}]), [1]),
            (finisher_obs(), [1]),
            (recorded(76), [1]),
            (recorded(77), [1]),
            (recorded(78), [2]),
            (recorded(83), [9]),
        ]
        reviewed = json.loads((root / "tests/fixtures/battle24_review.json").read_text())["decisions"]
        for case in reviewed.values():
            cases.append(({"current": None, "select": None},
                          [int(x) for x in (root / "deck.csv").read_text().splitlines()]))
            cases.append((case["observation"], [case["expected"]]))
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "submission.zip"
            make_archive(archive, build_file_list(root), root)
            with zipfile.ZipFile(archive) as handle:
                handle.extractall(Path(tmp) / "isolated")
                self.assertIn("core/palfingon_cards.py", handle.namelist())
                self.assertIn("core/expert_battle_planner.py", handle.namelist())
                self.assertIn("core/reviewed_turn_planner.py", handle.namelist())
                self.assertFalse(any(name.startswith("tests/") for name in handle.namelist()))
                self.assertFalse(any(name.startswith("expert_logs/") for name in handle.namelist()))
                self.assertIn("cabt_attacks.json", handle.namelist())
                self.assertNotIn("study_rules.json", handle.namelist())
            script = (
                "import json,sys; from agent import agent; "
                "from card_db import get_db; "
                "assert get_db().get_attack(134).name == 'Giga Impact'; "
                "cases=json.load(sys.stdin); "
                "assert all(agent(obs)==want for obs,want in cases)"
            )
            result = subprocess.run([sys.executable, "-I", "-c",
                "import sys; sys.path.insert(0, '.'); " + script],
                cwd=Path(tmp) / "isolated", input=json.dumps(cases), text=True,
                capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
