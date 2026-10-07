from __future__ import annotations

import unittest

from agent import agent
from card_db import get_db
from core.expert_logs import EXPERT_LOG_2_LESSONS
from core.disposable_active_planner import identify_disposable_active
from core.opponent_model import infer_opponent_next_turn_threat
from policy import debug_scores
from state_eval import (
    AREA_ACTIVE,
    AREA_BENCH,
    AREA_DECK,
    AREA_DISCARD,
    AREA_HAND,
    CTX_DAMAGE,
    CTX_MAIN,
    CTX_TO_ACTIVE,
    CTX_TO_HAND,
    OPT_ATTACH,
    OPT_ATTACK,
    OPT_CARD,
    OPT_END,
    OPT_EVOLVE,
    OPT_PLAY,
)


def card(cid, player=0):
    return {"id": cid, "serial": cid, "playerIndex": player}


def pokemon(cid, hp=None, max_hp=None, energies=None, player=0, tools=None):
    info = get_db().get_card(cid)
    max_hp = max_hp if max_hp is not None else (info.hp if info else 100)
    hp = hp if hp is not None else max_hp
    return {
        "id": cid,
        "serial": cid,
        "playerIndex": player,
        "hp": hp,
        "maxHp": max_hp,
        "appearThisTurn": False,
        "energies": energies or [],
        "energyCards": [],
        "tools": tools or [],
        "preEvolution": [],
    }


def player(active=None, bench=None, hand=None, discard=None, prizes=6, player_index=0):
    return {
        "active": [active] if active is not None else [],
        "bench": bench or [],
        "benchMax": 5,
        "deckCount": 40,
        "discard": discard or [],
        "prize": [None] * prizes,
        "handCount": len(hand or []),
        "hand": hand or [],
        "poisoned": False,
        "burned": False,
        "asleep": False,
        "paralyzed": False,
        "confused": False,
    }


def current(p0=None, p1=None, **overrides):
    data = {
        "turn": 1,
        "turnActionCount": 0,
        "yourIndex": 0,
        "firstPlayer": 0,
        "supporterPlayed": False,
        "stadiumPlayed": False,
        "energyAttached": False,
        "retreated": False,
        "result": -1,
        "stadium": [],
        "looking": None,
        "players": [
            p0 or player(pokemon(227), hand=[]),
            p1 or player(pokemon(320, player=1), hand=None, player_index=1),
        ],
    }
    data.update(overrides)
    return data


class CeruledgeExpertLogTests(unittest.TestCase):
    def test_expert_log_two_lessons_exist(self):
        self.assertIn("disposable_active", EXPERT_LOG_2_LESSONS)
        self.assertIn("crashing_headbutt_when_obsidian_bad", EXPERT_LOG_2_LESSONS)

    def test_ceruledge_discard_energy_damage_counts_for_ko_threat(self):
        p0 = player(pokemon(227, hp=70, max_hp=70), bench=[pokemon(227)], hand=[])
        p1 = player(
            pokemon(320, energies=[card(12, 1)], player=1),
            discard=[card(7, 1), card(8, 1), card(5, 1)],
            hand=None,
            player_index=1,
        )
        obs = {"current": current(p0=p0, p1=p1), "logs": [], "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": [{"type": OPT_END}]}}
        threat = infer_opponent_next_turn_threat(__import__("state_eval").normalize_state(obs))
        self.assertTrue(threat.can_take_active_ko)
        self.assertGreaterEqual(threat.max_visible_damage, 90)

    def test_low_setup_uses_pokepad_before_lillie(self):
        p0 = player(pokemon(227), hand=[card(1152), card(1227), card(7)])
        obs = {
            "current": current(p0=p0, turn=1),
            "logs": [],
            "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": [{"type": OPT_PLAY, "index": 0}, {"type": OPT_PLAY, "index": 1}, {"type": OPT_END}]},
        }
        self.assertEqual(agent(obs), [0])

    def test_disposable_active_attaches_to_benched_deino(self):
        p0 = player(pokemon(227, hp=70), bench=[pokemon(227)], hand=[card(5)])
        p1 = player(pokemon(320, energies=[card(12, 1)], player=1), discard=[card(7, 1), card(8, 1), card(5, 1)], hand=None, player_index=1)
        obs = {
            "current": current(p0=p0, p1=p1, turn=1),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [
                    {"type": OPT_ATTACH, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
                    {"type": OPT_ATTACH, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_BENCH, "inPlayIndex": 0},
                    {"type": OPT_END},
                ],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_full_chain_in_hand_protects_active_basic_from_disposable_plan(self):
        p0 = player(pokemon(227, hp=70), bench=[pokemon(227)], hand=[card(228), card(229)])
        p1 = player(pokemon(320, energies=[card(12, 1)], player=1), discard=[card(7, 1), card(8, 1), card(5, 1)], hand=None, player_index=1)
        obs = {
            "current": current(p0=p0, p1=p1, turn=1),
            "logs": [],
            "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": [{"type": OPT_END}]},
        }
        report = identify_disposable_active(__import__("state_eval").normalize_state(obs))
        self.assertFalse(report.is_disposable)

    def test_pre_ko_ultra_ball_for_fezandipiti_beats_lillie(self):
        p0 = player(pokemon(227, hp=70), bench=[pokemon(227)], hand=[card(1121), card(1227), card(7), card(8)])
        p1 = player(pokemon(320, energies=[card(12, 1)], player=1), discard=[card(7, 1), card(8, 1), card(5, 1)], hand=None, player_index=1)
        obs = {
            "current": current(p0=p0, p1=p1, turn=1),
            "logs": [],
            "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": [{"type": OPT_PLAY, "index": 0}, {"type": OPT_PLAY, "index": 1}, {"type": OPT_END}]},
        }
        self.assertEqual(agent(obs), [0])

    def test_pokepad_gets_gastly_when_gengar_chain_is_in_hand(self):
        p0 = player(pokemon(227), bench=[pokemon(227)], hand=[card(771), card(772)])
        obs = {
            "current": current(p0=p0, turn=1),
            "logs": [],
            "select": {
                "context": CTX_TO_HAND,
                "type": 1,
                "minCount": 1,
                "maxCount": 1,
                "effect": card(1152),
                "deck": [card(59), card(228), card(833)],
                "option": [{"type": OPT_CARD, "area": AREA_DECK, "index": idx, "playerIndex": 0} for idx in range(3)],
            },
        }
        self.assertEqual(agent(obs), [0])

    def test_post_ko_promotes_gastly_pivot_over_unready_hydreigon(self):
        p0 = player(active=None, bench=[pokemon(59), pokemon(229)], hand=[])
        obs = {
            "current": current(p0=p0, turn=3),
            "logs": [{"type": "KNOCK_OUT", "playerIndex": 0, "text": "Your Pokemon was Knocked Out."}],
            "select": {
                "context": CTX_TO_ACTIVE,
                "type": 1,
                "minCount": 1,
                "maxCount": 1,
                "option": [
                    {"type": OPT_CARD, "area": AREA_BENCH, "index": 0, "playerIndex": 0},
                    {"type": OPT_CARD, "area": AREA_BENCH, "index": 1, "playerIndex": 0},
                ],
            },
        }
        self.assertEqual(agent(obs), [0])

    def test_air_balloon_prefers_haunter_pivot(self):
        p0 = player(pokemon(227), bench=[pokemon(771), pokemon(229)], hand=[card(1174)])
        obs = {
            "current": current(p0=p0, turn=3),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [
                    {"type": OPT_ATTACH, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_BENCH, "inPlayIndex": 0},
                    {"type": OPT_ATTACH, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_BENCH, "inPlayIndex": 1},
                ],
            },
        }
        self.assertEqual(agent(obs), [0])

    def test_obsidian_targets_lunatone_solrock_engine(self):
        p0 = player(pokemon(229, energies=[card(7), card(8), card(5), card(7)]), hand=[])
        p1 = player(pokemon(320, hp=270, max_hp=270, player=1), bench=[pokemon(675, player=1), pokemon(676, player=1)], hand=None, player_index=1)
        attacks = get_db().get_card(229).attacks
        obs = {
            "current": current(p0=p0, p1=p1, turn=5),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": OPT_ATTACK, "attackId": attacks[1].attack_id}, {"type": OPT_ATTACK, "attackId": attacks[2].attack_id}],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_crashing_headbutt_when_obsidian_bench_damage_bad(self):
        p0 = player(pokemon(229, energies=[card(7), card(8), card(5), card(7)]), hand=[])
        p1 = player(pokemon(320, hp=200, max_hp=270, player=1), bench=[pokemon(320, player=1)], hand=None, player_index=1)
        attacks = get_db().get_card(229).attacks
        obs = {
            "current": current(p0=p0, p1=p1, turn=5),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": OPT_ATTACK, "attackId": attacks[1].attack_id}, {"type": OPT_ATTACK, "attackId": attacks[2].attack_id}],
            },
        }
        self.assertEqual(agent(obs), [0])

    def test_obsidian_damage_prompt_prefers_lunatone_and_solrock(self):
        p0 = player(pokemon(229), hand=[])
        p1 = player(pokemon(320, player=1), bench=[pokemon(675, player=1), pokemon(676, player=1), pokemon(320, player=1)], hand=None, player_index=1)
        obs = {
            "current": current(p0=p0, p1=p1, turn=5),
            "logs": [],
            "select": {
                "context": CTX_DAMAGE,
                "type": 1,
                "minCount": 2,
                "maxCount": 2,
                "option": [{"type": OPT_CARD, "area": AREA_BENCH, "index": idx, "playerIndex": 1} for idx in range(3)],
            },
        }
        self.assertEqual(set(agent(obs)), {0, 1})

    def test_all_deino_discard_prioritizes_night_stretcher(self):
        p0 = player(pokemon(229), bench=[pokemon(772)], hand=[card(1097), card(1227), card(7)], discard=[card(227), card(227), card(227)])
        obs = {
            "current": current(p0=p0, turn=7),
            "logs": [],
            "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": [{"type": OPT_PLAY, "index": 0}, {"type": OPT_PLAY, "index": 1}, {"type": OPT_END}]},
        }
        self.assertEqual(agent(obs), [0])


if __name__ == "__main__":
    unittest.main()
