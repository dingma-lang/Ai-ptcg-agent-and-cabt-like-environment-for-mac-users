from __future__ import annotations

import unittest

from agent import agent
from card_db import get_db
from policy import debug_scores
from state_eval import (
    AREA_ACTIVE,
    AREA_BENCH,
    AREA_DECK,
    AREA_HAND,
    CTX_DISCARD,
    CTX_MAIN,
    CTX_TO_BENCH,
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


def pokemon(cid, hp=None, max_hp=None, energies=None, player=0, appear_this_turn=False):
    info = get_db().get_card(cid)
    max_hp = max_hp if max_hp is not None else (info.hp if info else 100)
    hp = hp if hp is not None else max_hp
    return {
        "id": cid,
        "serial": cid,
        "playerIndex": player,
        "hp": hp,
        "maxHp": max_hp,
        "appearThisTurn": appear_this_turn,
        "energies": energies or [],
        "energyCards": [],
        "tools": [],
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


class HydreigonPolicyTests(unittest.TestCase):
    def test_empty_bench_prefers_buddy_buddy_poffin_before_pass(self):
        p0 = player(pokemon(59), hand=[card(1086)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": [{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}]},
        }
        self.assertEqual(agent(obs), [0])

    def test_empty_bench_prefers_poke_pad_search_before_pass(self):
        p0 = player(pokemon(59), hand=[card(1152)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": [{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}]},
        }
        self.assertEqual(agent(obs), [0])

    def test_rare_candy_hydreigon_line_beats_lillie_and_pass(self):
        p0 = player(pokemon(227), hand=[card(1079), card(229), card(1227)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": OPT_PLAY, "index": 0}, {"type": OPT_PLAY, "index": 2}, {"type": OPT_END}],
            },
        }
        self.assertEqual(agent(obs), [0])

    def test_zweilous_evolves_to_hydreigon_ex(self):
        p0 = player(pokemon(228), hand=[card(229), card(1227)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [
                    {"type": OPT_EVOLVE, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
                    {"type": OPT_PLAY, "index": 1},
                    {"type": OPT_END},
                ],
            },
        }
        self.assertEqual(agent(obs), [0])

    def test_deino_evolves_to_zweilous_when_rare_candy_line_missing(self):
        p0 = player(pokemon(227), hand=[card(228)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": OPT_EVOLVE, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0}, {"type": OPT_END}],
            },
        }
        self.assertEqual(agent(obs), [0])

    def test_evolve_same_name_pokemon_with_more_attached_energy(self):
        active_deino = pokemon(227, energies=[])
        benched_deino = pokemon(227, energies=[card(7), card(7)])
        p0 = player(active_deino, bench=[benched_deino], hand=[card(228)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [
                    {"type": OPT_EVOLVE, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
                    {"type": OPT_EVOLVE, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_BENCH, "inPlayIndex": 0},
                ],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_hydreigon_evolves_energy_ready_target_over_higher_stage(self):
        active_deino = pokemon(227, energies=[card(7), card(8)])
        benched_zweilous = pokemon(228, energies=[])
        p0 = player(active_deino, bench=[benched_zweilous], hand=[card(229)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [
                    {"type": OPT_EVOLVE, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
                    {"type": OPT_EVOLVE, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_BENCH, "inPlayIndex": 0},
                ],
            },
        }
        self.assertEqual(agent(obs), [0])

    def test_hydreigon_evolves_charged_zweilous_over_empty_deino(self):
        active_deino = pokemon(227, energies=[])
        benched_zweilous = pokemon(228, energies=[card(7), card(8)])
        p0 = player(active_deino, bench=[benched_zweilous], hand=[card(229)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [
                    {"type": OPT_EVOLVE, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
                    {"type": OPT_EVOLVE, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_BENCH, "inPlayIndex": 0},
                ],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_metal_energy_attaches_to_hydreigon_line_not_toxel(self):
        p0 = player(pokemon(227), bench=[pokemon(833)], hand=[card(8)])
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
        self.assertEqual(agent(obs), [0])

    def test_psychic_energy_attaches_to_hydreigon_line_not_support_ex(self):
        p0 = player(pokemon(227), bench=[pokemon(140)], hand=[card(5)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [
                    {"type": OPT_ATTACH, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_BENCH, "inPlayIndex": 0},
                    {"type": OPT_ATTACH, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
                ],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_energy_attaches_to_highest_hydreigon_stage_in_play(self):
        p0 = player(pokemon(227), bench=[pokemon(228)], hand=[card(8)])
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

    def test_energy_attaches_to_hydreigon_ex_over_lower_stage(self):
        p0 = player(pokemon(227), bench=[pokemon(229)], hand=[card(5)])
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

    def test_hydreigon_fourth_energy_prefers_extra_darkness(self):
        p0 = player(pokemon(229, energies=[card(7), card(8), card(5)]), hand=[card(7), card(5)])
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
                    {"type": OPT_ATTACH, "area": AREA_HAND, "index": 1, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
                ],
            },
        }
        self.assertEqual(agent(obs), [0])

    def test_hydreigon_does_not_stack_third_darkness_after_obsidian_ready(self):
        p0 = player(pokemon(229, energies=[card(7), card(8), card(5), card(7)]), hand=[card(7)])
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
                    {"type": OPT_END},
                ],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_dead_hand_uses_lillie_before_pass(self):
        p0 = player(pokemon(59), hand=[card(1227), card(1182), card(1139)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": [{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}]},
        }
        self.assertEqual(agent(obs), [0])

    def test_ultra_ball_discard_avoids_protected_combo_piece(self):
        p0 = player(pokemon(227), hand=[card(1079), card(229), card(8), card(1264)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_DISCARD,
                "type": 1,
                "minCount": 1,
                "maxCount": 1,
                "option": [
                    {"type": OPT_CARD, "area": AREA_HAND, "index": 0, "playerIndex": 0},
                    {"type": OPT_CARD, "area": AREA_HAND, "index": 1, "playerIndex": 0},
                    {"type": OPT_CARD, "area": AREA_HAND, "index": 2, "playerIndex": 0},
                    {"type": OPT_CARD, "area": AREA_HAND, "index": 3, "playerIndex": 0},
                ],
            },
        }
        self.assertEqual(agent(obs), [3])

    def test_ultra_ball_discard_protects_poffin_when_bench_empty(self):
        p0 = player(pokemon(227), hand=[card(1086), card(771), card(834), card(1264)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_DISCARD,
                "type": 1,
                "minCount": 2,
                "maxCount": 2,
                "effect": card(1121),
                "option": [
                    {"type": OPT_CARD, "area": AREA_HAND, "index": 0, "playerIndex": 0},
                    {"type": OPT_CARD, "area": AREA_HAND, "index": 1, "playerIndex": 0},
                    {"type": OPT_CARD, "area": AREA_HAND, "index": 2, "playerIndex": 0},
                    {"type": OPT_CARD, "area": AREA_HAND, "index": 3, "playerIndex": 0},
                ],
            },
        }
        self.assertNotIn(0, agent(obs))

    def test_secret_box_discard_protects_lillie_and_poffin(self):
        p0 = player(pokemon(227), hand=[card(1086), card(1227), card(1264), card(1174), card(834), card(771)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_DISCARD,
                "type": 1,
                "minCount": 3,
                "maxCount": 3,
                "effect": card(1092),
                "option": [
                    {"type": OPT_CARD, "area": AREA_HAND, "index": 0, "playerIndex": 0},
                    {"type": OPT_CARD, "area": AREA_HAND, "index": 1, "playerIndex": 0},
                    {"type": OPT_CARD, "area": AREA_HAND, "index": 2, "playerIndex": 0},
                    {"type": OPT_CARD, "area": AREA_HAND, "index": 3, "playerIndex": 0},
                    {"type": OPT_CARD, "area": AREA_HAND, "index": 4, "playerIndex": 0},
                    {"type": OPT_CARD, "area": AREA_HAND, "index": 5, "playerIndex": 0},
                ],
            },
        }
        choice = agent(obs)
        self.assertNotIn(0, choice)
        self.assertNotIn(1, choice)

    def test_ultra_ball_waits_when_poffin_should_be_played_first(self):
        p0 = player(pokemon(59), hand=[card(1121), card(1086), card(229)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": OPT_PLAY, "index": 0}, {"type": OPT_PLAY, "index": 1}, {"type": OPT_END}],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_end_turn_scores_below_useful_resources(self):
        p0 = player(pokemon(227), hand=[card(1086), card(1227), card(8), card(228)])
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
                    {"type": OPT_ATTACH, "area": AREA_HAND, "index": 2, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
                    {"type": OPT_EVOLVE, "area": AREA_HAND, "index": 3, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
                    {"type": OPT_END},
                ],
            },
        }
        _, rows = debug_scores(obs)
        scores = {idx: score for idx, score, _ in rows}
        self.assertLess(scores[4], scores[0])
        self.assertLess(scores[4], scores[1])
        self.assertLess(scores[4], scores[2])
        self.assertLess(scores[4], scores[3])

    def test_pass_scores_lower_than_useful_setup_action(self):
        p0 = player(pokemon(59), hand=[card(1086)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": [{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}]},
        }
        _, rows = debug_scores(obs)
        scores = {idx: score for idx, score, _ in rows}
        self.assertGreater(scores[0], scores[1])

    def test_crispin_prompt_prefers_metal_and_psychic_energy(self):
        p0 = player(pokemon(229), hand=[])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_TO_HAND,
                "type": 1,
                "minCount": 2,
                "maxCount": 2,
                "effect": card(1198),
                "deck": [card(8), card(5), card(7)],
                "option": [
                    {"type": OPT_CARD, "area": AREA_DECK, "index": 0, "playerIndex": 0},
                    {"type": OPT_CARD, "area": AREA_DECK, "index": 1, "playerIndex": 0},
                    {"type": OPT_CARD, "area": AREA_DECK, "index": 2, "playerIndex": 0},
                ],
            },
        }
        self.assertEqual(set(agent(obs)), {0, 1})

    def test_poffin_prompt_chooses_one_deino_then_missing_core_basic(self):
        p0 = player(pokemon(59), hand=[])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_TO_HAND,
                "type": 1,
                "minCount": 2,
                "maxCount": 2,
                "effect": card(1086),
                "deck": [card(227), card(227), card(59), card(833), card(140)],
                "option": [
                    {"type": OPT_CARD, "area": AREA_DECK, "index": 0, "playerIndex": 0},
                    {"type": OPT_CARD, "area": AREA_DECK, "index": 1, "playerIndex": 0},
                    {"type": OPT_CARD, "area": AREA_DECK, "index": 2, "playerIndex": 0},
                    {"type": OPT_CARD, "area": AREA_DECK, "index": 3, "playerIndex": 0},
                    {"type": OPT_CARD, "area": AREA_DECK, "index": 4, "playerIndex": 0},
                ],
            },
        }
        self.assertEqual(set(agent(obs)), {0, 3})

    def test_basic_in_hand_is_benched_before_poffin_supporter_attack_or_pass(self):
        attacks = get_db().get_card(59).attacks
        p0 = player(pokemon(59), hand=[card(1086), card(1227), card(227)])
        obs = {
            "current": current(p0=p0, turn=3),
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
                    {"type": OPT_PLAY, "index": 2},
                    {"type": OPT_END},
                ],
            },
        }
        self.assertEqual(agent(obs), [3])

    def test_next_basic_in_hand_is_benched_when_bench_has_space(self):
        p0 = player(pokemon(59), bench=[pokemon(227)], hand=[card(1227), card(833)])
        obs = {
            "current": current(p0=p0, turn=5),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": OPT_PLAY, "index": 0}, {"type": OPT_PLAY, "index": 1}, {"type": OPT_END}],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_basic_play_with_embedded_card_object_is_classified_and_benched(self):
        p0 = player(pokemon(59), hand=[card(1227)])
        obs = {
            "current": current(p0=p0, turn=3),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": OPT_PLAY, "card": card(227)}, {"type": OPT_PLAY, "index": 0}, {"type": OPT_END}],
            },
        }
        self.assertEqual(agent(obs), [0])

    def test_basic_found_by_search_is_benched_from_card_id_option_before_end(self):
        p0 = player(pokemon(59), hand=[card(227)])
        obs = {
            "current": current(p0=p0, turn=5),
            "logs": ["Tristary drew Deino from Poké Pad."],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": OPT_PLAY, "cardId": 227}, {"type": OPT_END}],
            },
        }
        self.assertEqual(agent(obs), [0])

    def test_basic_play_with_text_only_option_is_classified_and_benched(self):
        p0 = player(pokemon(59), hand=[card(1227)])
        obs = {
            "current": current(p0=p0, turn=3),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": OPT_PLAY, "text": "Play Gastly from your hand onto your Bench."}, {"type": OPT_PLAY, "index": 0}, {"type": OPT_END}],
            },
        }
        self.assertEqual(agent(obs), [0])

    def test_toxel_call_for_family_prompt_chooses_core_basics_first(self):
        p0 = player(pokemon(833, energies=[card(7)]), hand=[])
        obs = {
            "current": current(p0=p0, turn=3),
            "logs": [],
            "select": {
                "context": CTX_TO_BENCH,
                "type": 1,
                "minCount": 0,
                "maxCount": 2,
                "effect": card(833),
                "deck": [card(140), card(141), card(227), card(59), card(229)],
                "option": [{"type": OPT_CARD, "area": AREA_DECK, "index": idx, "playerIndex": 0} for idx in range(5)],
            },
        }
        self.assertEqual(set(agent(obs)), {2, 3})

    def test_toxel_call_for_family_can_take_basic_ex_after_core_basics(self):
        p0 = player(pokemon(833, energies=[card(7)]), bench=[pokemon(227), pokemon(59)], hand=[])
        obs = {
            "current": current(p0=p0, turn=3),
            "logs": [],
            "select": {
                "context": CTX_TO_BENCH,
                "type": 1,
                "minCount": 0,
                "maxCount": 2,
                "effect": card(833),
                "deck": [card(229), card(834), card(140), card(141)],
                "option": [{"type": OPT_CARD, "area": AREA_DECK, "index": idx, "playerIndex": 0} for idx in range(4)],
            },
        }
        self.assertEqual(set(agent(obs)), {2, 3})

    def test_toxel_call_for_family_attack_beats_early_low_value_attack_and_pass(self):
        attacks = get_db().get_card(833).attacks
        call_for_family = next(attack for attack in attacks if attack.name == "Call for Family")
        playful_kick = next(attack for attack in attacks if attack.name == "Playful Kick")
        p0 = player(pokemon(833, energies=[card(7), card(7)]), hand=[])
        obs = {
            "current": current(p0=p0, turn=3),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [
                    {"type": OPT_ATTACK, "attackId": playful_kick.attack_id},
                    {"type": OPT_ATTACK, "attackId": call_for_family.attack_id},
                    {"type": OPT_END},
                ],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_poke_pad_prompt_avoids_rule_box_hydreigon_for_zweilous(self):
        p0 = player(pokemon(227), hand=[])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_TO_HAND,
                "type": 1,
                "minCount": 1,
                "maxCount": 1,
                "effect": card(1152),
                "deck": [card(229), card(228)],
                "option": [
                    {"type": OPT_CARD, "area": AREA_DECK, "index": 0, "playerIndex": 0},
                    {"type": OPT_CARD, "area": AREA_DECK, "index": 1, "playerIndex": 0},
                ],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_hydreigon_ko_attack_beats_low_value_setup(self):
        attacks = get_db().get_card(229).attacks
        p0 = player(pokemon(229, energies=[7, 8, 5]), hand=[card(1086)])
        p1 = player(pokemon(227, hp=10, max_hp=70, player=1), hand=None, player_index=1)
        obs = {
            "current": current(p0=p0, p1=p1),
            "logs": [],
            "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": [{"type": OPT_PLAY, "index": 0}, {"type": OPT_ATTACK, "attackId": attacks[1].attack_id}]},
        }
        self.assertEqual(agent(obs), [1])

    def test_zweilous_does_not_attack_when_it_can_be_protected(self):
        attacks = get_db().get_card(228).attacks
        p0 = player(pokemon(228, energies=[card(7), card(7), card(7)]), hand=[])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": OPT_ATTACK, "attackId": attacks[1].attack_id}, {"type": OPT_END}],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_deck_discard_attack_waits_until_opponent_deck_is_low(self):
        attacks = get_db().get_card(227).attacks
        p0 = player(pokemon(227, energies=[card(7)]), hand=[])
        p1 = player(pokemon(59, player=1), hand=None, player_index=1)
        p1["deckCount"] = 30
        obs = {
            "current": current(p0=p0, p1=p1),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": OPT_ATTACK, "attackId": attacks[0].attack_id}, {"type": OPT_END}],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_deck_discard_attack_is_allowed_when_opponent_deck_is_low(self):
        attacks = get_db().get_card(227).attacks
        p0 = player(pokemon(227, energies=[card(7)]), hand=[])
        p1 = player(pokemon(59, player=1), hand=None, player_index=1)
        p1["deckCount"] = 10
        obs = {
            "current": current(p0=p0, p1=p1),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": OPT_ATTACK, "attackId": attacks[0].attack_id}, {"type": OPT_END}],
            },
        }
        self.assertEqual(agent(obs), [0])


if __name__ == "__main__":
    unittest.main()
