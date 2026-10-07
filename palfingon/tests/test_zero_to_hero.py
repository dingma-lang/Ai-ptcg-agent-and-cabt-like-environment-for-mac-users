from __future__ import annotations

import unittest

from core.zero_to_hero_planner import detect_zero_to_hero_opportunity
from state_eval import OPT_END, OPT_RETREAT, normalize_state
from tests.test_palafin_strategy import FINIZEN, PALAFIN, obs_for, pokemon


class ZeroToHeroTests(unittest.TestCase):
    def test_active_palafin_retreat_is_zero_to_hero_setup(self):
        obs = obs_for(
            pokemon(PALAFIN),
            bench=[pokemon(FINIZEN)],
            options=[{"type": OPT_RETREAT}, {"type": OPT_END}],
        )
        plan = detect_zero_to_hero_opportunity(normalize_state(obs), obs["select"]["option"])
        self.assertTrue(plan.available)
        self.assertEqual(plan.option_index, 0)
        self.assertGreater(plan.score, 8000)


if __name__ == "__main__":
    unittest.main()
