from __future__ import annotations

import unittest

from agent import agent
from state_eval import AREA_DECK, CTX_MAIN, CTX_TO_HAND, OPT_ATTACK, OPT_CARD, OPT_END, OPT_PLAY
from tests.test_round_plan import card, current, player, pokemon


class EmergencySetupTests(unittest.TestCase):
    def test_no_basic_and_empty_bench_prefers_lillie_over_secret_box(self):
        obs = main_obs(
            hand=[card(1227), card(1092), card(1219)],
            options=[{"type": OPT_PLAY, "index": 0}, {"type": OPT_PLAY, "index": 1}, {"type": OPT_PLAY, "index": 2}, {"type": OPT_END}],
        )
        self.assertEqual(agent(obs), [0])

    def test_no_basic_and_one_bench_prefers_lillie_over_petrel(self):
        obs = main_obs(
            bench=[pokemon(227)],
            hand=[card(1227), card(1219), card(1231)],
            options=[{"type": OPT_PLAY, "index": 0}, {"type": OPT_PLAY, "index": 1}, {"type": OPT_PLAY, "index": 2}, {"type": OPT_END}],
        )
        self.assertEqual(agent(obs), [0])

    def test_no_basic_uses_pokepad_when_direct_poffin_line_unavailable(self):
        obs = main_obs(
            hand=[card(1227), card(1152), card(1231)],
            options=[{"type": OPT_PLAY, "index": 0}, {"type": OPT_PLAY, "index": 1}, {"type": OPT_PLAY, "index": 2}, {"type": OPT_END}],
        )
        self.assertEqual(agent(obs), [1])

    def test_no_basic_prefers_lillie_over_dawn_when_searchers_missing(self):
        obs = main_obs(
            hand=[card(1227), card(1231)],
            options=[{"type": OPT_PLAY, "index": 0}, {"type": OPT_PLAY, "index": 1}, {"type": OPT_END}],
        )
        self.assertEqual(agent(obs), [0])

    def test_no_basic_uses_lillie_if_only_draw_setup_exists(self):
        obs = main_obs(
            hand=[card(1227)],
            options=[{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}],
        )
        self.assertEqual(agent(obs), [0])

    def test_petrel_prompt_takes_buddy_buddy_poffin(self):
        p0 = player(pokemon(59), hand=[card(1219)])
        obs = {
            "current": current(p0=p0, turn=3),
            "logs": [],
            "select": {
                "context": CTX_TO_HAND,
                "type": 1,
                "minCount": 1,
                "maxCount": 1,
                "effect": card(1219),
                "deck": [card(1227), card(1086), card(1152)],
                "option": [{"type": OPT_CARD, "area": AREA_DECK, "index": idx, "playerIndex": 0} for idx in range(3)],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_petrel_prompt_with_developed_bench_takes_rare_candy_over_poffin(self):
        p0 = player(
            pokemon(59),
            bench=[pokemon(227), pokemon(833), pokemon(140)],
            hand=[card(1219), card(229)],
        )
        obs = {
            "current": current(p0=p0, turn=5),
            "logs": [],
            "select": {
                "context": CTX_TO_HAND,
                "type": 1,
                "minCount": 1,
                "maxCount": 1,
                "effect": card(1219),
                "deck": [card(1086), card(1079), card(1121), card(1227)],
                "option": [{"type": OPT_CARD, "area": AREA_DECK, "index": idx, "playerIndex": 0} for idx in range(4)],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_dawn_prompt_builds_basic_ex_and_evolution_team(self):
        p0 = player(pokemon(59), hand=[card(1231)])
        obs = {
            "current": current(p0=p0, turn=3),
            "logs": [],
            "select": {
                "context": CTX_TO_HAND,
                "type": 1,
                "minCount": 3,
                "maxCount": 3,
                "effect": card(1231),
                "deck": [card(227), card(140), card(834), card(229), card(772)],
                "option": [{"type": OPT_CARD, "area": AREA_DECK, "index": idx, "playerIndex": 0} for idx in range(5)],
            },
        }
        self.assertEqual(set(agent(obs)), {1, 2, 3})

    def test_weak_board_ignores_opponent_prize_liability_for_fezandipiti(self):
        p0 = player(pokemon(59), hand=[card(140)])
        p1 = player(pokemon(227, player=1), prizes=2, hand=None, player_index=1)
        obs = {
            "current": current(p0=p0, p1=p1, turn=7),
            "logs": [],
            "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": [{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}]},
        }
        self.assertEqual(agent(obs), [0])

    def test_emergency_setup_beats_weak_attack_and_end(self):
        from card_db import get_db

        attacks = get_db().get_card(59).attacks
        obs = main_obs(
            hand=[card(1219)],
            options=[{"type": OPT_ATTACK, "attackId": attacks[0].attack_id}, {"type": OPT_PLAY, "index": 0}, {"type": OPT_END}],
        )
        self.assertEqual(agent(obs), [1])


def main_obs(hand, options, bench=None):
    p0 = player(pokemon(59), bench=bench or [], hand=hand)
    return {
        "current": current(p0=p0, turn=3),
        "logs": [],
        "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": options},
    }


if __name__ == "__main__":
    unittest.main()
