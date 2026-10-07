from __future__ import annotations

import unittest

from agent import agent
from card_db import get_db
from policy import debug_scores
from state_eval import AREA_ACTIVE, AREA_BENCH, AREA_HAND, CTX_ATTACH_TO, CTX_MAIN, OPT_ATTACH, OPT_ATTACK, OPT_CARD, OPT_END, OPT_PLAY


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


class ResourceUsageTests(unittest.TestCase):
    def test_lillie_weak_hand_is_used_before_low_value_attack(self):
        attacks = get_db().get_card(59).attacks
        p0 = player(pokemon(59), hand=[card(1227), card(1182)])
        p1 = player(pokemon(227, hp=70, max_hp=70, player=1), hand=None, player_index=1)
        obs = {
            "current": current(p0=p0, p1=p1),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": OPT_PLAY, "index": 0}, {"type": OPT_ATTACK, "attackId": attacks[0].attack_id}],
            },
        }
        self.assertEqual(agent(obs), [0])

    def test_rare_candy_combo_holds_lillie(self):
        p0 = player(pokemon(227), hand=[card(1079), card(229), card(1227)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": [{"type": OPT_PLAY, "index": 0}, {"type": OPT_PLAY, "index": 2}]},
        }
        self.assertEqual(agent(obs), [0])

    def test_lillie_not_held_for_evolution_unless_evolution_option_is_legal(self):
        p0 = player(pokemon(227), hand=[card(1227), card(1079), card(229)])
        obs = {
            "current": current(p0=p0, turn=7),
            "logs": [],
            "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": [{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}]},
        }
        self.assertEqual(agent(obs), [0])

    def test_crispin_improves_hydreigon_energy_plan(self):
        p0 = player(pokemon(229), hand=[card(1198)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": [{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}]},
        }
        self.assertEqual(agent(obs), [0])

    def test_best_supporter_is_used_before_low_value_attack_or_pass(self):
        attacks = get_db().get_card(227).attacks
        p0 = player(pokemon(227), hand=[card(1182), card(1198)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [
                    {"type": OPT_PLAY, "index": 0},
                    {"type": OPT_PLAY, "index": 1},
                    {"type": OPT_ATTACK, "attackId": attacks[0].attack_id},
                    {"type": OPT_END},
                ],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_dawn_is_used_before_low_value_attack_or_pass(self):
        attacks = get_db().get_card(59).attacks
        p0 = player(pokemon(59), bench=[pokemon(227)], hand=[card(1231)])
        obs = {
            "current": current(p0=p0, turn=7),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": OPT_PLAY, "index": 0}, {"type": OPT_ATTACK, "attackId": attacks[0].attack_id}, {"type": OPT_END}],
            },
        }
        self.assertEqual(agent(obs), [0])

    def test_petrel_is_used_before_low_value_attack_or_pass_when_supporter_unused(self):
        attacks = get_db().get_card(59).attacks
        p0 = player(pokemon(59), bench=[pokemon(227), pokemon(833), pokemon(59)], hand=[card(1219)])
        obs = {
            "current": current(p0=p0, turn=7),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": OPT_PLAY, "index": 0}, {"type": OPT_ATTACK, "attackId": attacks[0].attack_id}, {"type": OPT_END}],
            },
        }
        self.assertEqual(agent(obs), [0])

    def test_manual_energy_attaches_to_hydreigon_line(self):
        p0 = player(pokemon(227), hand=[card(8)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": OPT_ATTACH, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0}, {"type": OPT_END}],
            },
        }
        self.assertEqual(agent(obs), [0])

    def test_metal_energy_can_be_held_when_only_bad_targets_exist(self):
        p0 = player(pokemon(59), hand=[card(8)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": OPT_ATTACH, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0}, {"type": OPT_END}],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_psychic_energy_is_not_attached_to_mega_gengar(self):
        p0 = player(pokemon(772), hand=[card(5)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": OPT_ATTACH, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0}, {"type": OPT_END}],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_darkness_energy_is_not_attached_to_toxtricity(self):
        p0 = player(pokemon(834), hand=[card(7)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": OPT_ATTACH, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0}, {"type": OPT_END}],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_darkness_energy_is_not_attached_to_pecharunt(self):
        p0 = player(pokemon(141), hand=[card(7)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": OPT_ATTACH, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0}, {"type": OPT_END}],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_darkness_energy_prefers_mega_gengar_over_pecharunt(self):
        p0 = player(pokemon(141), bench=[pokemon(772, energies=[card(7)])], hand=[card(7)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [
                    {"type": OPT_ATTACH, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
                    {"type": OPT_ATTACH, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_BENCH, "inPlayIndex": 0},
                ],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_toxtricity_ability_avoids_pecharunt_target(self):
        p0 = player(pokemon(834), bench=[pokemon(141), pokemon(772)], hand=[])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_ATTACH_TO,
                "type": 1,
                "minCount": 1,
                "maxCount": 1,
                "effect": card(834),
                "option": [
                    {"type": OPT_CARD, "area": AREA_BENCH, "index": 0, "playerIndex": 0},
                    {"type": OPT_CARD, "area": AREA_BENCH, "index": 1, "playerIndex": 0},
                ],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_effect_energy_attach_target_avoids_pecharunt(self):
        p0 = player(pokemon(141), bench=[pokemon(229, energies=[card(7), card(8)])], hand=[])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_ATTACH_TO,
                "type": 1,
                "minCount": 1,
                "maxCount": 1,
                "effect": card(1198),
                "option": [
                    {"type": OPT_CARD, "area": AREA_ACTIVE, "index": 0, "playerIndex": 0},
                    {"type": OPT_CARD, "area": AREA_BENCH, "index": 0, "playerIndex": 0},
                ],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_tool_attach_avoids_pecharunt_resource_sink(self):
        p0 = player(pokemon(141), bench=[pokemon(229)], hand=[card(1174)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [
                    {"type": OPT_ATTACH, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
                    {"type": OPT_ATTACH, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_BENCH, "inPlayIndex": 0},
                ],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_secret_box_waits_when_discard_cost_is_unsafe(self):
        p0 = player(pokemon(59), bench=[pokemon(227)], hand=[card(1092), card(7)])
        obs = {
            "current": current(p0=p0, supporterPlayed=False),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [
                    {"type": OPT_PLAY, "index": 0},
                    {"type": OPT_ATTACH, "area": AREA_HAND, "index": 1, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
                    {"type": OPT_END},
                ],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_secret_box_waits_before_low_value_attack_when_discard_cost_is_unsafe(self):
        attacks = get_db().get_card(59).attacks
        p0 = player(pokemon(59), bench=[pokemon(229, energies=[card(5), card(8)])], hand=[card(1092), card(7)])
        obs = {
            "current": current(p0=p0, supporterPlayed=False),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [
                    {"type": OPT_PLAY, "index": 0},
                    {"type": OPT_ATTACK, "attackId": attacks[0].attack_id},
                    {"type": OPT_END},
                ],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_crispin_is_used_for_hydreigon_fourth_energy_before_pass(self):
        p0 = player(pokemon(229, energies=[card(7), card(8), card(5)]), hand=[card(1198)])
        obs = {
            "current": current(p0=p0, supporterPlayed=False),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}],
            },
        }
        self.assertEqual(agent(obs), [0])

    def test_empty_bench_can_bench_fezandipiti_early_if_no_safer_basic(self):
        p0 = player(pokemon(59), hand=[card(140)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": [{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}]},
        }
        self.assertEqual(agent(obs), [0])

    def test_darkness_energy_to_mega_gengar_is_not_wasted(self):
        p0 = player(pokemon(772, energies=[card(7)]), hand=[card(7)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": OPT_ATTACH, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0}, {"type": OPT_END}],
            },
        }
        self.assertEqual(agent(obs), [0])

    def test_pass_score_rejects_unused_supporter_and_energy(self):
        p0 = player(pokemon(227), hand=[card(1227), card(8)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [
                    {"type": OPT_PLAY, "index": 0},
                    {"type": OPT_ATTACH, "area": AREA_HAND, "index": 1, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
                    {"type": OPT_END},
                ],
            },
        }
        _, rows = debug_scores(obs)
        scores = {idx: score for idx, score, _ in rows}
        self.assertLess(scores[2], scores[0])
        self.assertLess(scores[2], scores[1])


if __name__ == "__main__":
    unittest.main()
