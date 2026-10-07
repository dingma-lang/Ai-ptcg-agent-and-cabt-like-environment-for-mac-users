from __future__ import annotations

import unittest

from core.deck_operating_system import compute_deck_goal_state
from core.target_field_planner import piece_score
from state_eval import normalize_state
from tests.test_round_plan import card, current, player, pokemon


def state_for(p0):
    return normalize_state({"current": current(p0=p0), "logs": [], "select": {"option": [], "minCount": 0, "maxCount": 0}})


class DeckOperatingSystemTests(unittest.TestCase):
    def test_missing_second_hydreigon_chain_stays_priority(self):
        state = state_for(player(pokemon(229), bench=[pokemon(59), pokemon(833)]))
        goal = compute_deck_goal_state(state)
        self.assertLess(goal.hydreigon_chains_current, 2)
        self.assertGreater(piece_score(state, "Deino"), 0)

    def test_missing_mega_gengar_chain_is_priority(self):
        state = state_for(player(pokemon(229), bench=[pokemon(227), pokemon(833)]))
        goal = compute_deck_goal_state(state)
        self.assertIn("Gastly", goal.missing_core_pieces)
        self.assertGreater(piece_score(state, "Gastly"), piece_score(state, "Pecharunt ex"))

    def test_missing_toxtricity_chain_is_energy_engine_priority(self):
        state = state_for(player(pokemon(227), bench=[pokemon(59)]))
        goal = compute_deck_goal_state(state)
        self.assertIn("Toxel", goal.missing_energy_engine)
        self.assertGreater(piece_score(state, "Toxel"), 0)

    def test_missing_fezandipiti_before_ko_gets_priority(self):
        state = state_for(player(pokemon(227), bench=[pokemon(59), pokemon(833)]))
        self.assertGreater(piece_score(state, "Fezandipiti ex"), 0)

    def test_missing_pecharunt_when_pivot_useful_gets_priority(self):
        state = state_for(player(pokemon(59), bench=[pokemon(229, energies=[card(7), card(8), card(5)])]))
        self.assertGreaterEqual(piece_score(state, "Pecharunt ex"), 0)


if __name__ == "__main__":
    unittest.main()
