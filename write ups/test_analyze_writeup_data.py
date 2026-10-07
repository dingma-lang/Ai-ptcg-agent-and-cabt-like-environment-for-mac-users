import unittest

from analyze_writeup_data import agent_label, comparison_seat, longest_pass_streak, main_turns, selection_status, wilson


def row(indices, minimum=1, maximum=1, turn=1, options=None):
    return {
        "player": 0, "turn": turn, "selected_indexes": indices,
        "observation": {"select": {"context": 0, "minCount": minimum,
                                   "maxCount": maximum,
                                   "option": options if options is not None else [{"type": 14}, {"type": 13}]}},
    }


class AuditTests(unittest.TestCase):
    def test_selection_validation(self):
        for indices in ([True], [1.0], [2], [-1], [0, 0], [], "0"):
            with self.subTest(indices=indices):
                self.assertEqual(selection_status(row(indices)), "invalid")
        self.assertEqual(selection_status(row([1])), "valid")
        self.assertEqual(selection_status(row([0, 1], 1, 2)), "valid")
        self.assertEqual(selection_status(row([], 0, 2)), "valid")

    def test_missing_or_inconsistent_schema(self):
        self.assertEqual(selection_status({}), "unverifiable")
        self.assertEqual(selection_status(row([0], 3, 4)), "unverifiable")

    def test_wilson_not_degenerate_at_perfect_score(self):
        lo, hi = wilson(2, 2)
        self.assertAlmostEqual(lo, 0.3423802275)
        self.assertAlmostEqual(hi, 1.0)
        self.assertIsNone(wilson(0, 0))
        with self.assertRaises(ValueError):
            wilson(2, 1)

    def test_wilson_small_comparison(self):
        lo, hi = wilson(1, 3)
        self.assertAlmostEqual(lo, 0.0614919447)
        self.assertAlmostEqual(hi, 0.7923403992)

    def test_main_turn_definition(self):
        rows = [row([1]), row([0]), row([0], turn=3)]
        prompt = row([0], turn=5)
        prompt["observation"]["select"]["context"] = 7
        turns = main_turns("test", rows + [prompt])
        self.assertEqual(len(turns), 2)
        self.assertFalse(turns[0]["pass_only"])
        self.assertTrue(turns[1]["pass_only"])
        self.assertTrue(turns[0]["attack_option_selected"])

    def test_missing_turn_breaks_streak(self):
        turns = [{"turn": t, "pass_only": True} for t in (1, 3, 7, 9)]
        self.assertEqual(longest_pass_streak(turns), 2)
        turns[1]["pass_only"] = False
        self.assertEqual(longest_pass_streak(turns[:2]), 1)

    def test_imports_are_not_workspace_versions(self):
        self.assertEqual(agent_label("file:/a/palfingon/agent.py:agent"), "workspace:palfingon")
        self.assertEqual(agent_label("file:/a/imported_agents/submission-palfingon-1.3-abc/agent.py:agent"),
                         "import:submission-palfingon-1.3-abc")
        self.assertEqual(agent_label("random"), "random")

    def test_comparison_accepts_reversed_seats(self):
        a = "import:submission-palfingon-1.3-abc"
        b = "import:submission-palfingon-1.2-def"
        self.assertEqual(comparison_seat({"seat_0": a, "seat_1": b}), 0)
        self.assertEqual(comparison_seat({"seat_0": b, "seat_1": a}), 1)
        self.assertIsNone(comparison_seat({"seat_0": a, "seat_1": "workspace:palfingon"}))


if __name__ == "__main__":
    unittest.main()
