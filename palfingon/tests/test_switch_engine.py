from __future__ import annotations

import unittest

from core.switch_engine_planner import score_switch_action
from state_eval import OPT_PLAY, OPT_RETREAT, normalize_state
from tests.test_palafin_strategy import FINIZEN, PALAFIN, SURFING_BEACH, obs_for, pokemon


class SwitchEngineTests(unittest.TestCase):
    def test_surfing_beach_scores_as_palafin_switch_engine(self):
        obs = obs_for(
            pokemon(PALAFIN),
            bench=[pokemon(FINIZEN)],
            options=[{"type": OPT_PLAY, "cardId": SURFING_BEACH}],
        )
        score = score_switch_action(normalize_state(obs), obs["select"]["option"][0])
        self.assertGreater(score.score, 7000)

    def test_retreat_palafin_scores_when_bench_water_exists(self):
        obs = obs_for(pokemon(PALAFIN), bench=[pokemon(FINIZEN)], options=[{"type": OPT_RETREAT}])
        score = score_switch_action(normalize_state(obs), obs["select"]["option"][0])
        self.assertGreater(score.score, 7000)


if __name__ == "__main__":
    unittest.main()
