from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from action_classifier import ActionCategory
from analyze_logs import analyze_files


class AnalyzeLogsTests(unittest.TestCase):
    def analyze_records(self, records):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "decisions.jsonl"
            path.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")
            summary, findings = analyze_files([str(path)], timeout_sec=2.0)
            return summary, findings

    def test_detects_missed_ko_bad_pass_bad_discard_and_illegal_choice(self):
        records = [
            {
                "turn": 5,
                "min_count": 1,
                "max_count": 1,
                "legal_options": [
                    {"index": 0, "category": ActionCategory.ATTACK, "score": 12000.0, "attack_name": "Clean KO"},
                    {"index": 1, "category": ActionCategory.END_TURN, "score": -100.0},
                ],
                "chosen_index": [1],
            },
            {
                "turn": 3,
                "min_count": 1,
                "max_count": 1,
                "legal_options": [
                    {"index": 0, "category": ActionCategory.ATTACH_ENERGY, "score": 120.0, "card_id": 7},
                    {"index": 1, "category": ActionCategory.END_TURN, "score": -50.0},
                ],
                "chosen_index": [1],
            },
            {
                "turn": 4,
                "min_count": 1,
                "max_count": 1,
                "legal_options": [
                    {"index": 0, "category": ActionCategory.DISCARD_COST, "score": -5000.0, "card_id": 229, "card_name": "Hydreigon ex"}
                ],
                "chosen_index": [0],
            },
            {
                "turn": 4,
                "min_count": 1,
                "max_count": 1,
                "legal_options": [{"index": 0, "category": ActionCategory.END_TURN, "score": 0.0}],
                "chosen_index": [9],
            },
        ]
        summary, findings = self.analyze_records(records)
        self.assertEqual(summary["missed_KO_count"], 1)
        self.assertEqual(summary["bad_pass_count"], 1)
        self.assertEqual(summary["bad_discard_count"], 1)
        self.assertEqual(summary["illegal_action_count"], 1)
        self.assertTrue(any(finding["kind"] == "missed_KO" for finding in findings))

    def test_detects_unsafe_support_bench_without_later_use(self):
        records = [
            {
                "turn": 2,
                "min_count": 1,
                "max_count": 1,
                "legal_options": [
                    {"index": 0, "category": ActionCategory.PLAY_BASIC_TO_BENCH, "score": 25.0, "card_id": 140, "card_name": "Fezandipiti ex"}
                ],
                "chosen_index": [0],
            }
        ]
        summary, _ = self.analyze_records(records)
        self.assertEqual(summary["unsafe_bench_count"], 1)


if __name__ == "__main__":
    unittest.main()
