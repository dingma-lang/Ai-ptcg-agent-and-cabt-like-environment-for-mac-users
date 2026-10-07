from __future__ import annotations

import unittest

from agent import agent
from core.option_scorer import score_options_with_analysis
from state_eval import AREA_ACTIVE, AREA_BENCH, OPT_ATTACH, OPT_END, OPT_PLAY, normalize_state
from tests.test_palafin_strategy import (
    AIR_BALLOON,
    DRAGONAIR,
    FINIZEN,
    HILDA,
    LIGHTNING,
    LILLIE,
    PALAFIN,
    PALAFIN_EX,
    POKE_PAD,
    POFFIN,
    SURFING_BEACH,
    WATER,
    card,
    obs_for,
    pokemon,
)

KIERAN = 1191


class AgentUsesAnalysisTests(unittest.TestCase):
    def analysis_rows(self, obs):
        state = normalize_state(obs)
        return score_options_with_analysis(state)

    def test_poffin_before_lillie_is_visible_to_runtime(self):
        obs = obs_for(
            pokemon(FINIZEN),
            bench=[],
            hand=[card(POFFIN), card(LILLIE)],
            options=[
                {"type": OPT_PLAY, "cardId": POFFIN},
                {"type": OPT_PLAY, "cardId": LILLIE},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [0])
        rows = self.analysis_rows(obs)
        self.assertIn("Finizen", rows[0].supporting_cards)
        self.assertIn("Buddy-Buddy Poffin", rows[1].blocked_by)

    def test_pokepad_and_hilda_are_used_as_bridge_search(self):
        pokepad_obs = obs_for(
            pokemon(FINIZEN),
            bench=[],
            hand=[card(POKE_PAD)],
            options=[
                {"type": OPT_PLAY, "cardId": POKE_PAD},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(pokepad_obs), [0])
        self.assertIn("Palafin", self.analysis_rows(pokepad_obs)[0].supporting_cards)

        hilda_obs = obs_for(
            pokemon(FINIZEN),
            hand=[card(HILDA), card(LILLIE)],
            options=[
                {"type": OPT_PLAY, "cardId": HILDA},
                {"type": OPT_PLAY, "cardId": LILLIE},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(hilda_obs), [0])

    def test_surfing_beach_air_balloon_and_kieran_support_zero_to_hero(self):
        beach_obs = obs_for(
            pokemon(PALAFIN),
            bench=[pokemon(FINIZEN)],
            hand=[card(SURFING_BEACH)],
            options=[
                {"type": OPT_PLAY, "cardId": SURFING_BEACH},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(beach_obs), [0])
        self.assertIn("Palafin ex", self.analysis_rows(beach_obs)[0].supporting_cards)

        balloon_obs = obs_for(
            pokemon(PALAFIN),
            bench=[pokemon(FINIZEN)],
            hand=[card(AIR_BALLOON)],
            options=[
                {"type": OPT_ATTACH, "cardId": AIR_BALLOON, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(balloon_obs), [0])

        kieran_obs = obs_for(
            pokemon(PALAFIN),
            bench=[pokemon(FINIZEN)],
            hand=[card(KIERAN)],
            options=[
                {"type": OPT_PLAY, "cardId": KIERAN},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(kieran_obs), [0])

    def test_energy_relationships_block_lightning_on_palafin_and_pick_dragonair(self):
        obs = obs_for(
            pokemon(PALAFIN_EX, energies=[WATER]),
            bench=[pokemon(DRAGONAIR)],
            hand=[card(LIGHTNING)],
            options=[
                {"type": OPT_ATTACH, "cardId": LIGHTNING, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
                {"type": OPT_ATTACH, "cardId": LIGHTNING, "inPlayArea": AREA_BENCH, "inPlayIndex": 0},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [1])
        rows = self.analysis_rows(obs)
        self.assertIn("Mega Dragonite ex", rows[0].blocked_by)
        self.assertGreater(rows[1].score, rows[0].score)

    def test_water_to_palafin_ex_is_supported_but_capped(self):
        fresh_obs = obs_for(
            pokemon(PALAFIN_EX),
            hand=[card(WATER)],
            options=[
                {"type": OPT_ATTACH, "cardId": WATER, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(fresh_obs), [0])
        self.assertIn("Palafin ex", self.analysis_rows(fresh_obs)[0].supporting_cards)

        powered_obs = obs_for(
            pokemon(PALAFIN_EX, energies=[WATER]),
            hand=[card(WATER)],
            options=[
                {"type": OPT_ATTACH, "cardId": WATER, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(powered_obs), [1])


if __name__ == "__main__":
    unittest.main()
