from __future__ import annotations

import unittest

from core.mega_dragonite_planner import score_mega_dragonite_plan
from core.palafin_planner import score_energy_attachment
from state_eval import AREA_ACTIVE, OPT_EVOLVE, normalize_state
from tests.test_palafin_strategy import DRAGONAIR, DRATINI, LIGHTNING, MEGA_DRAGONITE_EX, obs_for, pokemon


class MegaDragoniteTests(unittest.TestCase):
    def test_lightning_goes_to_dragonite_line(self):
        state = normalize_state(obs_for(pokemon(DRATINI), bench=[]))
        self.assertGreater(score_energy_attachment(state, LIGHTNING, pokemon(DRATINI)), 5000)

    def test_evolve_dragonair_to_mega_dragonite_is_useful(self):
        obs = obs_for(
            pokemon(DRAGONAIR),
            bench=[],
            options=[{"type": OPT_EVOLVE, "cardId": MEGA_DRAGONITE_EX, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0}],
        )
        state = normalize_state(obs)
        plan = score_mega_dragonite_plan(state, obs["select"]["option"])
        self.assertTrue(plan.should_act)


if __name__ == "__main__":
    unittest.main()
