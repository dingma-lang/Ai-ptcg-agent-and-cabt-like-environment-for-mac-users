from __future__ import annotations

import unittest

from core.supporter_router import choose_best_supporter
from state_eval import OPT_PLAY, normalize_state
from tests.test_palafin_strategy import DRAGONAIR, FINIZEN, HILDA, LILLIE, MEGA_DRAGONITE_EX, PALAFIN, PETREL, POFFIN, obs_for, card, pokemon


class PalafinSupporterRouterTests(unittest.TestCase):
    def test_petrel_finds_exact_setup_when_poffin_absent(self):
        obs = obs_for(
            pokemon(FINIZEN),
            bench=[],
            hand=[card(PETREL)],
            options=[{"type": OPT_PLAY, "cardId": PETREL}],
        )
        decision = choose_best_supporter(normalize_state(obs), obs["select"]["option"])
        self.assertTrue(decision.should_use)
        self.assertEqual(decision.supporter_name, "Team Rocket's Petrel")

    def test_hilda_is_good_when_finizen_can_become_palafin(self):
        obs = obs_for(
            pokemon(FINIZEN),
            bench=[],
            hand=[card(HILDA)],
            options=[{"type": OPT_PLAY, "cardId": HILDA}],
        )
        decision = choose_best_supporter(normalize_state(obs), obs["select"]["option"])
        self.assertTrue(decision.should_use)
        self.assertEqual(decision.supporter_name, "Hilda")

    def test_lillie_waits_when_poffin_setup_is_in_hand(self):
        obs = obs_for(
            pokemon(FINIZEN),
            bench=[],
            hand=[card(LILLIE), card(POFFIN)],
            options=[{"type": OPT_PLAY, "cardId": LILLIE}],
        )
        decision = choose_best_supporter(normalize_state(obs), obs["select"]["option"])
        self.assertFalse(decision.should_use)

    def test_hilda_beats_lillie_when_lillie_would_shuffle_live_evolution_chain(self):
        obs = obs_for(
            pokemon(FINIZEN),
            bench=[],
            hand=[card(LILLIE), card(HILDA), card(PALAFIN)],
            options=[
                {"type": OPT_PLAY, "cardId": LILLIE},
                {"type": OPT_PLAY, "cardId": HILDA},
            ],
        )
        decision = choose_best_supporter(normalize_state(obs), obs["select"]["option"])
        self.assertTrue(decision.should_use)
        self.assertEqual(decision.supporter_name, "Hilda")

    def test_petrel_beats_lillie_when_dragonite_chain_is_held(self):
        obs = obs_for(
            pokemon(FINIZEN),
            bench=[pokemon(DRAGONAIR)],
            hand=[card(LILLIE), card(PETREL), card(MEGA_DRAGONITE_EX)],
            options=[
                {"type": OPT_PLAY, "cardId": LILLIE},
                {"type": OPT_PLAY, "cardId": PETREL},
            ],
        )
        decision = choose_best_supporter(normalize_state(obs), obs["select"]["option"])
        self.assertTrue(decision.should_use)
        self.assertEqual(decision.supporter_name, "Team Rocket's Petrel")


if __name__ == "__main__":
    unittest.main()
