from __future__ import annotations

import unittest

from agent import agent
from card_db import get_db
from core.danger_evaluator import CRITICAL, HIGH, MEDIUM, evaluate_danger
from state_eval import CTX_MAIN, OPT_ATTACK, OPT_END, OPT_PLAY


def card(cid, player=0):
    return {"id": cid, "serial": cid, "playerIndex": player}


def pokemon(cid, hp=None, max_hp=None, energies=None, player=0):
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
        "tools": [],
        "preEvolution": [],
    }


def player(active=None, bench=None, hand=None, prizes=6, player_index=0):
    return {
        "active": [active] if active is not None else [],
        "bench": bench or [],
        "benchMax": 5,
        "deckCount": 40,
        "discard": [],
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
        "turn": 3,
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
            p0 or player(pokemon(59), hand=[]),
            p1 or player(pokemon(229, energies=[card(7), card(7), card(8), card(5)], player=1), hand=None, player_index=1),
        ],
    }
    data.update(overrides)
    return data


class DangerEvaluatorTests(unittest.TestCase):
    def test_empty_bench_and_active_ko_threat_is_critical(self):
        p0 = player(pokemon(59, hp=40, max_hp=70), bench=[], hand=[])
        p1 = player(pokemon(229, energies=[card(7), card(7)], player=1), hand=None, player_index=1)
        obs = {"current": current(p0=p0, p1=p1), "logs": [], "select": {"context": CTX_MAIN, "type": 0, "minCount": 0, "maxCount": 0, "option": []}}
        self.assertEqual(evaluate_danger(__import__("state_eval").normalize_state(obs)).severity, CRITICAL)

    def test_one_weak_bench_and_high_resource_active_is_high(self):
        p0 = player(pokemon(229, hp=100, max_hp=330, energies=[card(7), card(8)]), bench=[pokemon(227)], hand=[])
        p1 = player(pokemon(772, energies=[card(7), card(7)], player=1), hand=None, player_index=1)
        obs = {"current": current(p0=p0, p1=p1), "logs": [], "select": {"context": CTX_MAIN, "type": 0, "minCount": 0, "maxCount": 0, "option": []}}
        self.assertEqual(evaluate_danger(__import__("state_eval").normalize_state(obs)).severity, HIGH)

    def test_ready_backup_reduces_critical_danger_to_medium(self):
        p0 = player(
            pokemon(229, hp=100, max_hp=330, energies=[card(7), card(8)]),
            bench=[pokemon(229, energies=[card(7), card(7)])],
            hand=[],
        )
        p1 = player(pokemon(772, energies=[card(7), card(7)], player=1), hand=None, player_index=1)
        obs = {"current": current(p0=p0, p1=p1), "logs": [], "select": {"context": CTX_MAIN, "type": 0, "minCount": 0, "maxCount": 0, "option": []}}
        self.assertEqual(evaluate_danger(__import__("state_eval").normalize_state(obs)).severity, MEDIUM)

    def test_opponent_final_prize_threat_is_critical(self):
        p0 = player(pokemon(140, hp=80, max_hp=210), bench=[pokemon(227)], hand=[])
        p1 = player(pokemon(772, energies=[card(7), card(7)], player=1), prizes=2, hand=None, player_index=1)
        obs = {"current": current(p0=p0, p1=p1), "logs": [], "select": {"context": CTX_MAIN, "type": 0, "minCount": 0, "maxCount": 0, "option": []}}
        self.assertEqual(evaluate_danger(__import__("state_eval").normalize_state(obs)).severity, CRITICAL)

    def test_policy_prefers_build_over_low_value_attack_in_high_danger(self):
        attacks = get_db().get_card(59).attacks
        p0 = player(pokemon(59, hp=40, max_hp=70), hand=[card(227)])
        p1 = player(pokemon(772, energies=[card(7), card(7)], player=1), hand=None, player_index=1)
        obs = {
            "current": current(p0=p0, p1=p1),
            "logs": [],
            "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": [{"type": OPT_ATTACK, "attackId": attacks[0].attack_id}, {"type": OPT_PLAY, "index": 0}]},
        }
        self.assertEqual(agent(obs), [1])

    def test_policy_still_takes_strong_ko_attack(self):
        attacks = get_db().get_card(229).attacks
        p0 = player(pokemon(229, energies=[card(7), card(8), card(5), card(7)]), hand=[card(227)])
        p1 = player(pokemon(227, hp=20, max_hp=70, player=1), hand=None, player_index=1)
        obs = {
            "current": current(p0=p0, p1=p1),
            "logs": [],
            "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": [{"type": OPT_ATTACK, "attackId": attacks[1].attack_id}, {"type": OPT_PLAY, "index": 0}]},
        }
        self.assertEqual(agent(obs), [0])


if __name__ == "__main__":
    unittest.main()
