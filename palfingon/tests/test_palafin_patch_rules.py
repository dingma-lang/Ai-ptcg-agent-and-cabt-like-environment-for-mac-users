from __future__ import annotations

import unittest

from agent import agent
from core.air_balloon_planner import score_air_balloon_target
from core.palafin_planner import score_discard_selection, score_petrel_target, score_secret_box_target
from state_eval import AREA_ACTIVE, AREA_BENCH, AREA_DECK, AREA_HAND, CTX_DISCARD, CTX_MAIN, CTX_TO_HAND, OPT_ATTACH, OPT_CARD, OPT_END, OPT_EVOLVE, OPT_PLAY, normalize_state
from tests.test_palafin_strategy import (
    AIR_BALLOON,
    DRAGONAIR,
    DRATINI,
    FINIZEN,
    HILDA,
    LILLIE,
    PALAFIN,
    PALAFIN_EX,
    PETREL,
    POKE_PAD,
    POFFIN,
    SECRET_BOX,
    SURFING_BEACH,
    TATSUGIRI,
    card,
    obs_for,
    pokemon,
)

SWITCH = 1123
MEGA_DRAGONITE_EX = 904


class PalafinPatchRuleTests(unittest.TestCase):
    def test_evolve_palafin_before_secret_box_and_block_discard(self):
        obs = obs_for(
            pokemon(FINIZEN),
            hand=[card(PALAFIN), card(SECRET_BOX), card(LILLIE)],
            options=[
                {"type": OPT_PLAY, "cardId": SECRET_BOX, "area": AREA_HAND, "index": 1},
                {"type": OPT_EVOLVE, "cardId": PALAFIN, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [1])

        discard_obs = obs_for(
            pokemon(FINIZEN),
            hand=[card(PALAFIN), card(SECRET_BOX), card(LILLIE), card(SURFING_BEACH)],
            options=[{"type": OPT_CARD, "area": AREA_HAND, "index": idx, "playerIndex": 0} for idx in range(4)],
            select_extra={"context": CTX_DISCARD, "sourceCardId": SECRET_BOX, "minCount": 1, "maxCount": 1},
        )
        state = normalize_state(discard_obs)
        self.assertLess(score_discard_selection(state, PALAFIN), -8000)
        self.assertNotEqual(agent(discard_obs), [0])

    def test_poffin_in_hand_is_used_before_petrel_for_poffin(self):
        obs = obs_for(
            pokemon(FINIZEN),
            bench=[],
            hand=[card(POFFIN), card(PETREL)],
            options=[
                {"type": OPT_PLAY, "cardId": PETREL, "area": AREA_HAND, "index": 1},
                {"type": OPT_PLAY, "cardId": POFFIN, "area": AREA_HAND, "index": 0},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [1])

    def test_petrel_can_get_poffin_when_bench_needs_basics_and_poffin_missing(self):
        obs = obs_for(
            pokemon(TATSUGIRI),
            bench=[],
            hand=[],
            options=[
                {"type": OPT_CARD, "area": AREA_DECK, "index": 0, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_DECK, "index": 1, "playerIndex": 0},
            ],
            select_extra={
                "context": CTX_TO_HAND,
                "effect": card(PETREL),
                "deck": [card(POFFIN), card(POKE_PAD)],
                "minCount": 1,
                "maxCount": 1,
            },
        )
        self.assertEqual(agent(obs), [0])

    def test_secret_box_item_target_is_poffin_when_bench_is_low(self):
        obs = obs_for(
            pokemon(TATSUGIRI),
            bench=[],
            hand=[],
            options=[
                {"type": OPT_CARD, "area": AREA_DECK, "index": 0, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_DECK, "index": 1, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_DECK, "index": 2, "playerIndex": 0},
            ],
            select_extra={
                "context": CTX_TO_HAND,
                "effect": card(SECRET_BOX),
                "deck": [card(POKE_PAD), card(POFFIN), card(SWITCH)],
                "minCount": 1,
                "maxCount": 1,
            },
        )
        self.assertEqual(agent(obs), [1])

    def test_air_balloon_targets_active_palafin_or_tatsugiri_not_random(self):
        palafin_obs = obs_for(
            pokemon(PALAFIN),
            bench=[pokemon(FINIZEN)],
            hand=[card(AIR_BALLOON)],
            options=[
                {"type": OPT_ATTACH, "cardId": AIR_BALLOON, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(palafin_obs), [0])

        random_obs = obs_for(
            pokemon(FINIZEN),
            bench=[pokemon(DRATINI)],
            hand=[card(AIR_BALLOON)],
            options=[
                {"type": OPT_ATTACH, "cardId": AIR_BALLOON, "inPlayArea": AREA_BENCH, "inPlayIndex": 0},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(random_obs), [1])

        tatsu_obs = obs_for(
            pokemon(TATSUGIRI),
            bench=[pokemon(PALAFIN_EX, energies=[3])],
            hand=[card(AIR_BALLOON)],
            options=[
                {"type": OPT_ATTACH, "cardId": AIR_BALLOON, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(tatsu_obs), [0])

    def test_switch_only_for_zero_to_hero_or_reset(self):
        zero_obs = obs_for(
            pokemon(PALAFIN),
            bench=[pokemon(FINIZEN)],
            hand=[card(SWITCH)],
            options=[
                {"type": OPT_PLAY, "cardId": SWITCH},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(zero_obs), [0])

        random_obs = obs_for(
            pokemon(FINIZEN),
            bench=[pokemon(DRATINI)],
            hand=[card(SWITCH)],
            options=[
                {"type": OPT_PLAY, "cardId": SWITCH},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(random_obs), [1])

    def test_bench_finizen_before_pokepad(self):
        obs = obs_for(
            pokemon(TATSUGIRI),
            bench=[],
            hand=[card(FINIZEN), card(POKE_PAD)],
            options=[
                {"type": OPT_PLAY, "cardId": POKE_PAD, "area": AREA_HAND, "index": 1},
                {"type": OPT_PLAY, "cardId": FINIZEN, "area": AREA_HAND, "index": 0},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [1])

    def test_pokepad_searches_dragonite_line_after_finizen_setup_stable(self):
        obs = obs_for(
            pokemon(FINIZEN),
            bench=[pokemon(FINIZEN)],
            hand=[card(PALAFIN)],
            options=[
                {"type": OPT_CARD, "area": AREA_DECK, "index": 0, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_DECK, "index": 1, "playerIndex": 0},
            ],
            select_extra={
                "context": CTX_TO_HAND,
                "effect": card(POKE_PAD),
                "deck": [card(DRATINI), card(DRAGONAIR)],
                "minCount": 1,
                "maxCount": 1,
            },
        )
        self.assertEqual(agent(obs), [0])

    def test_petrel_gets_pokepad_for_non_rulebox_evolution_piece(self):
        obs = obs_for(
            pokemon(FINIZEN),
            bench=[pokemon(TATSUGIRI)],
            hand=[],
            options=[
                {"type": OPT_CARD, "area": AREA_DECK, "index": 0, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_DECK, "index": 1, "playerIndex": 0},
            ],
            select_extra={
                "context": CTX_TO_HAND,
                "effect": card(PETREL),
                "deck": [card(POFFIN), card(POKE_PAD)],
                "minCount": 1,
                "maxCount": 1,
            },
        )
        self.assertEqual(agent(obs), [1])

    def test_petrel_does_not_get_pokepad_for_rulebox_mega_dragonite(self):
        obs = obs_for(
            pokemon(TATSUGIRI),
            bench=[pokemon(DRAGONAIR)],
            hand=[],
            options=[
                {"type": OPT_CARD, "area": AREA_DECK, "index": 0, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_DECK, "index": 1, "playerIndex": 0},
            ],
            select_extra={
                "context": CTX_TO_HAND,
                "effect": card(PETREL),
                "deck": [card(POKE_PAD), card(HILDA)],
                "minCount": 1,
                "maxCount": 1,
            },
        )
        self.assertEqual(agent(obs), [1])


if __name__ == "__main__":
    unittest.main()
