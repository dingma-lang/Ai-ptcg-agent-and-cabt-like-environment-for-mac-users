from __future__ import annotations

import unittest

from core.energy_planner import crispin_energy_selection_score, score_energy_attachment
from state_eval import normalize_state
from tests.test_palafin_strategy import DRATINI, LIGHTNING, PALAFIN_EX, WATER, obs_for, pokemon


class PalafinEnergyPlannerTests(unittest.TestCase):
    def test_water_to_palafin_ex_once_only(self):
        state = normalize_state(obs_for(pokemon(PALAFIN_EX), bench=[]))
        self.assertGreater(score_energy_attachment(state, WATER, pokemon(PALAFIN_EX)), 6000)
        self.assertLess(score_energy_attachment(state, WATER, pokemon(PALAFIN_EX, energies=[WATER])), -8000)

    def test_crispin_values_water_and_lightning_for_palaking(self):
        state = normalize_state(obs_for(pokemon(DRATINI), bench=[]))
        self.assertGreater(crispin_energy_selection_score(state, LIGHTNING), 6000)
        self.assertGreater(crispin_energy_selection_score(state, WATER), 3000)


if __name__ == "__main__":
    unittest.main()
