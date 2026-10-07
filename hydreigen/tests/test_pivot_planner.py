from __future__ import annotations

import unittest

from agent import agent
from card_db import get_db
from core.pivot_planner import score_pecharunt_ability
from state_eval import AREA_ACTIVE, AREA_BENCH, AREA_HAND, CTX_MAIN, OPT_ABILITY, OPT_ATTACH, OPT_ATTACK, OPT_END, OPT_PLAY


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
            p1 or player(pokemon(227, player=1), hand=None, player_index=1),
        ],
    }
    data.update(overrides)
    return data


class PivotPlannerTests(unittest.TestCase):
    def test_pecharunt_ability_pivots_into_darkness_attacker(self):
        p0 = player(pokemon(59, hp=30, max_hp=70), bench=[pokemon(141), pokemon(229, energies=[card(7), card(7)])], hand=[])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": [{"type": OPT_ABILITY, "area": AREA_BENCH, "index": 0, "playerIndex": 0}, {"type": OPT_END}]},
        }
        self.assertEqual(agent(obs), [0])

    def test_pecharunt_does_not_switch_to_poisoned_weak_no_gain_target(self):
        p0 = player(pokemon(229, energies=[card(7), card(7)]), bench=[pokemon(141), pokemon(227, hp=10, max_hp=70)], hand=[])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": [{"type": OPT_ABILITY, "area": AREA_BENCH, "index": 0, "playerIndex": 0}, {"type": OPT_END}]},
        }
        self.assertEqual(agent(obs), [1])

    def test_air_balloon_protects_high_resource_active(self):
        attacks = get_db().get_card(229).attacks
        p0 = player(pokemon(229, hp=80, max_hp=330, energies=[card(7), card(8)]), bench=[pokemon(227)], hand=[card(1174)])
        p1 = player(pokemon(772, energies=[card(7), card(7)], player=1), hand=None, player_index=1)
        obs = {
            "current": current(p0=p0, p1=p1),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [
                    {"type": OPT_ATTACH, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
                    {"type": OPT_ATTACK, "attackId": attacks[1].attack_id},
                ],
            },
        }
        self.assertEqual(agent(obs), [0])

    def test_attach_darkness_to_bench_for_later_pecharunt_attack_plan(self):
        p0 = player(pokemon(59), bench=[pokemon(141), pokemon(229, energies=[card(7)])], hand=[card(7)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [
                    {"type": OPT_ATTACH, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_BENCH, "inPlayIndex": 1},
                    {"type": OPT_ABILITY, "area": AREA_BENCH, "index": 0, "playerIndex": 0},
                ],
            },
        }
        self.assertEqual(agent(obs), [0])

    def test_pecharunt_is_not_treated_as_energy_acceleration(self):
        p0 = player(pokemon(59), bench=[pokemon(141)], hand=[])
        obs = {"current": current(p0=p0), "logs": [], "select": {"context": CTX_MAIN, "type": 0, "minCount": 0, "maxCount": 0, "option": []}}
        state = __import__("state_eval").normalize_state(obs)
        self.assertLess(score_pecharunt_ability(state), 0)

    def test_pecharunt_ability_is_held_when_switch_has_no_gain(self):
        p0 = player(pokemon(229, energies=[card(7), card(8), card(5)]), bench=[pokemon(141), pokemon(772)], hand=[])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": [{"type": OPT_ABILITY, "area": AREA_BENCH, "index": 0, "playerIndex": 0}, {"type": OPT_END}]},
        }
        self.assertEqual(agent(obs), [1])


if __name__ == "__main__":
    unittest.main()
