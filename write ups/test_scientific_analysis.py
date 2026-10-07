import itertools
import math
import unittest
from fractions import Fraction

from scientific_analysis import at_least_each, energy_deficit, target_count_given_basic, trace_comparison, transition_counts


class ScientificTests(unittest.TestCase):
    def test_hypergeometric_against_exhaustive_small_deck(self):
        hands = list(itertools.combinations(range(8), 3))
        count = sum(any(i < 2 for i in hand) and any(2 <= i < 5 for i in hand) for hand in hands)
        self.assertEqual(at_least_each(8, [2, 3], 3), Fraction(count, len(hands)))

    def test_conditioning_against_exhaustive_small_deck(self):
        hands = [h for h in itertools.combinations(range(8), 4) if any(i < 2 for i in h)]
        count = sum(sum(2 <= i < 5 for i in h) >= 2 for h in hands)
        self.assertEqual(target_count_given_basic(8, 2, 3, 4, 2), Fraction(count, len(hands)))

    def test_inclusion_exclusion_limits(self):
        self.assertEqual(at_least_each(60, [0], 7), 0)
        self.assertEqual(at_least_each(60, [60], 7), 1)
        self.assertEqual(at_least_each(60, [], 7), 1)
        with self.assertRaises(ValueError):
            at_least_each(8, [5, 5], 3)

    def test_energy_is_typed_not_just_counted(self):
        self.assertEqual(energy_deficit({3: 1}, [4]), 1)
        self.assertEqual(energy_deficit({3: 1, 4: 2}, [3, 3, 3]), 2)
        self.assertEqual(energy_deficit({3: 1, 4: 2}, [3, 4, 4]), 0)

    def test_transition_gaps_and_players_are_not_linked(self):
        def turn(player, number, passed):
            return dict(match_id="a", player=player, turn=number, pass_only=passed, verified=True)
        counts = transition_counts([turn(0, 1, True), turn(0, 3, True), turn(0, 7, False),
                                    turn(1, 2, False), turn(1, 4, True)])
        self.assertEqual(counts, {"00": 0, "01": 1, "10": 0, "11": 1})

    def test_discordance_is_complete_and_tie_aware(self):
        row = {"match_id": "x", "decision_index": 1, "turn": 1, "agent_id": "random",
               "selected_indexes": [1], "observation": {"select": {"context": 0, "minCount": 1,
                "maxCount": 1, "option": [{"type": 7}, {"type": 13}]}},
               "agent_trace": {"chosen_index": [1], "legal_options": [{"index": 0, "score": 10},
                                                                        {"index": 1, "score": 10}]}}
        self.assertFalse(trace_comparison(row)["discordant"])
        row["agent_trace"]["legal_options"][1]["score"] = -10
        self.assertEqual(trace_comparison(row)["score_gap"], 20)
        self.assertEqual(trace_comparison(row)["rank_loss"], 1)
        row["agent_trace"]["legal_options"][1]["score"] = math.nan
        self.assertIsNone(trace_comparison(row))
        row["agent_trace"]["legal_options"].pop()
        self.assertIsNone(trace_comparison(row))


if __name__ == "__main__":
    unittest.main()
