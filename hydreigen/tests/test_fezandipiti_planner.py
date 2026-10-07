from __future__ import annotations

import unittest

from agent import agent
from card_db import get_db
from state_eval import AREA_BENCH, AREA_DECK, CTX_MAIN, CTX_TO_BENCH, CTX_TO_HAND, OPT_ABILITY, OPT_ATTACK, OPT_CARD, OPT_END, OPT_PLAY


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


KO_LOG = [{"type": "KNOCK_OUT", "playerIndex": 0, "text": "Your Pokemon was Knocked Out during opponent last turn."}]


class FezandipitiPlannerTests(unittest.TestCase):
    def test_after_ko_uses_fezandipiti_ability_before_supporter(self):
        p0 = player(pokemon(59), bench=[pokemon(140)], hand=[card(1227)])
        obs = {
            "current": current(p0=p0),
            "logs": KO_LOG,
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": OPT_PLAY, "index": 0}, {"type": OPT_ABILITY, "area": AREA_BENCH, "index": 0, "playerIndex": 0}],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_after_ko_uses_fezandipiti_ability_before_secret_box(self):
        p0 = player(pokemon(59), bench=[pokemon(140)], hand=[card(1092)])
        obs = {
            "current": current(p0=p0),
            "logs": KO_LOG,
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": OPT_PLAY, "index": 0}, {"type": OPT_ABILITY, "area": AREA_BENCH, "index": 0, "playerIndex": 0}, {"type": OPT_END}],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_after_ko_searches_fezandipiti_when_hand_needs_recovery(self):
        p0 = player(pokemon(59), hand=[card(1121), card(7)])
        obs = {
            "current": current(p0=p0),
            "logs": KO_LOG,
            "select": {
                "context": CTX_TO_HAND,
                "type": 1,
                "minCount": 1,
                "maxCount": 1,
                "effect": card(1121),
                "deck": [card(140), card(229)],
                "option": [{"type": OPT_CARD, "area": AREA_DECK, "index": 0, "playerIndex": 0}, {"type": OPT_CARD, "area": AREA_DECK, "index": 1, "playerIndex": 0}],
            },
        }
        self.assertEqual(agent(obs), [0])

    def test_late_game_after_ko_still_searches_fezandipiti_for_recovery(self):
        p0 = player(pokemon(227), hand=[card(1121), card(1079), card(8), card(5), card(7)])
        p1 = player(pokemon(227, player=1), prizes=2, hand=None, player_index=1)
        obs = {
            "current": current(p0=p0, p1=p1),
            "logs": KO_LOG,
            "select": {
                "context": CTX_TO_HAND,
                "type": 1,
                "minCount": 1,
                "maxCount": 1,
                "effect": card(1121),
                "deck": [card(140), card(229)],
                "option": [{"type": OPT_CARD, "area": AREA_DECK, "index": 0, "playerIndex": 0}, {"type": OPT_CARD, "area": AREA_DECK, "index": 1, "playerIndex": 0}],
            },
        }
        self.assertEqual(agent(obs), [0])

    def test_after_ko_benches_fezandipiti_when_it_is_in_hand(self):
        p0 = player(pokemon(59), hand=[card(140), card(1231)])
        obs = {
            "current": current(p0=p0),
            "logs": KO_LOG,
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": OPT_PLAY, "index": 1}, {"type": OPT_PLAY, "index": 0}, {"type": OPT_END}],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_after_ko_uses_dawn_to_find_fezandipiti(self):
        p0 = player(pokemon(59), hand=[card(1231), card(1227)])
        obs = {
            "current": current(p0=p0),
            "logs": KO_LOG,
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": OPT_PLAY, "index": 1}, {"type": OPT_PLAY, "index": 0}, {"type": OPT_END}],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_dawn_prompt_after_ko_selects_fezandipiti_basic(self):
        p0 = player(pokemon(59), hand=[card(1231)])
        obs = {
            "current": current(p0=p0),
            "logs": KO_LOG,
            "select": {
                "context": CTX_TO_HAND,
                "type": 1,
                "minCount": 1,
                "maxCount": 1,
                "effect": card(1231),
                "deck": [card(227), card(140), card(229)],
                "option": [{"type": OPT_CARD, "area": AREA_DECK, "index": idx, "playerIndex": 0} for idx in range(3)],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_after_ko_uses_ultra_ball_to_find_fezandipiti(self):
        p0 = player(pokemon(59), hand=[card(1121), card(7), card(8)])
        obs = {
            "current": current(p0=p0),
            "logs": KO_LOG,
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": OPT_END}, {"type": OPT_PLAY, "index": 0}],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_after_ko_uses_toxel_call_for_family_to_find_fezandipiti(self):
        attacks = get_db().get_card(833).attacks
        call_for_family = next(attack for attack in attacks if attack.name == "Call for Family")
        p0 = player(pokemon(833, energies=[card(7)]), hand=[card(1227)])
        obs = {
            "current": current(p0=p0),
            "logs": KO_LOG,
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": OPT_PLAY, "index": 0}, {"type": OPT_ATTACK, "attackId": call_for_family.attack_id}, {"type": OPT_END}],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_toxel_call_for_family_prompt_after_ko_selects_fezandipiti(self):
        p0 = player(pokemon(833, energies=[card(7)]), hand=[])
        obs = {
            "current": current(p0=p0),
            "logs": KO_LOG,
            "select": {
                "context": CTX_TO_BENCH,
                "type": 1,
                "minCount": 1,
                "maxCount": 2,
                "effect": card(833),
                "deck": [card(227), card(140), card(59)],
                "option": [{"type": OPT_CARD, "area": AREA_DECK, "index": idx, "playerIndex": 0} for idx in range(3)],
            },
        }
        self.assertIn(1, agent(obs))

    def test_without_ko_does_not_prioritize_fezandipiti_for_no_reason(self):
        p0 = player(pokemon(59), hand=[card(1121)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_TO_HAND,
                "type": 1,
                "minCount": 1,
                "maxCount": 1,
                "deck": [card(140), card(227)],
                "option": [{"type": OPT_CARD, "area": AREA_DECK, "index": 0, "playerIndex": 0}, {"type": OPT_CARD, "area": AREA_DECK, "index": 1, "playerIndex": 0}],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_early_empty_bench_can_bench_fezandipiti(self):
        p0 = player(pokemon(59), hand=[card(140)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": [{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}]},
        }
        self.assertEqual(agent(obs), [0])


if __name__ == "__main__":
    unittest.main()
