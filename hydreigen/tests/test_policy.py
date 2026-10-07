from __future__ import annotations

import unittest

from action_classifier import ActionCategory, classify_legal_option
from action_reasoner import ActionClass, classify_option
from agent import agent
from card_db import get_db
from decision_reason import build_decision_record, explain_choice
from policy import MomentType, classify_all_options, debug_scores, identify_moment_type, parse_select, parse_state
from state_eval import (
    AREA_ACTIVE,
    AREA_BENCH,
    AREA_DECK,
    AREA_DISCARD,
    AREA_HAND,
    AREA_PRIZE,
    CTX_TO_ACTIVE,
    CTX_TO_HAND,
    CTX_TO_PRIZE,
    CTX_IS_FIRST,
    CTX_MAIN,
    CTX_DISCARD,
    CTX_SETUP_BENCH,
    OPT_NO,
    OPT_ABILITY,
    OPT_ATTACH,
    OPT_ATTACK,
    OPT_CARD,
    OPT_END,
    OPT_PLAY,
    OPT_RETREAT,
    OPT_YES,
    normalize_state,
)


def card(cid, serial=None, player=0):
    return {"id": cid, "serial": serial or cid, "playerIndex": player}


def pokemon(cid, hp=None, max_hp=None, energies=None, tools=None, player=0):
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
        "tools": [card(tid, player=player) for tid in (tools or [])],
        "preEvolution": [],
    }


def player(active, bench=None, hand=None, discard=None, prizes=6, player_index=0):
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


def current(p0=None, p1=None):
    return {
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
            p0 or player(pokemon(721), hand=[]),
            p1 or player(pokemon(722, player=1), hand=None, player_index=1),
        ],
    }


def with_current(**overrides):
    p0 = overrides.pop("p0", None)
    p1 = overrides.pop("p1", None)
    data = current(p0=p0, p1=p1)
    data.update(overrides)
    return data


class PolicyTests(unittest.TestCase):
    def moment_for(self, obs):
        state = parse_state(obs)
        select = parse_select(obs)
        options = classify_all_options(state, select)
        return identify_moment_type(state, select, options)

    def test_initial_deck_selection_returns_60_cards(self):
        result = agent({"select": None, "current": None, "logs": []})
        self.assertEqual(len(result), 60)
        self.assertTrue(all(isinstance(cid, int) for cid in result))

    def test_missing_select_is_safe_empty(self):
        self.assertEqual(agent({"current": current(), "logs": []}), [])

    def test_empty_options_is_safe_empty(self):
        obs = {"current": current(), "logs": [], "select": {"context": 0, "type": 0, "minCount": 0, "maxCount": 0, "option": []}}
        self.assertEqual(agent(obs), [])

    def test_min_count_multi_select_unique_legal(self):
        p0 = player(pokemon(721), hand=[card(722), card(721)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_SETUP_BENCH,
                "type": 1,
                "minCount": 2,
                "maxCount": 2,
                "option": [
                    {"type": OPT_CARD, "area": AREA_HAND, "index": 0, "playerIndex": 0},
                    {"type": OPT_CARD, "area": AREA_HAND, "index": 1, "playerIndex": 0},
                ],
            },
        }
        result = agent(obs)
        self.assertEqual(len(result), 2)
        self.assertEqual(len(set(result)), 2)
        self.assertTrue(all(0 <= idx < 2 for idx in result))

    def test_prefers_going_first(self):
        obs = {
            "current": current(),
            "logs": [],
            "select": {
                "context": CTX_IS_FIRST,
                "type": 9,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": OPT_YES}, {"type": OPT_NO}],
            },
        }
        self.assertEqual(agent(obs), [0])

    def test_setup_bench_prefers_deino_over_support_ex(self):
        p0 = player(pokemon(59), hand=[card(140), card(227)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_SETUP_BENCH,
                "type": 1,
                "minCount": 1,
                "maxCount": 1,
                "option": [
                    {"type": OPT_CARD, "area": AREA_HAND, "index": 0, "playerIndex": 0},
                    {"type": OPT_CARD, "area": AREA_HAND, "index": 1, "playerIndex": 0},
                ],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_action_reasoner_classifies_play_from_hand_types(self):
        p0 = player(pokemon(59), hand=[card(1227), card(1121), card(1264), card(227)])
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
                    {"type": OPT_PLAY, "index": 2},
                    {"type": OPT_PLAY, "index": 3},
                ],
            },
        }
        state = normalize_state(obs)
        classes = [classify_option(state, option, idx).action_class for idx, option in enumerate(state.options)]
        self.assertEqual(classes, [ActionClass.PLAY_SUPPORTER, ActionClass.PLAY_ITEM, ActionClass.PLAY_STADIUM, ActionClass.BENCH_BASIC])

    def test_action_classifier_uses_exact_public_categories(self):
        p0 = player(pokemon(59), hand=[card(1227), card(1121), card(1264), card(227), card(1079)])
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
                    {"type": OPT_PLAY, "index": 2},
                    {"type": OPT_PLAY, "index": 3},
                    {"type": OPT_PLAY, "index": 4},
                    {"type": OPT_END},
                ],
            },
        }
        state = normalize_state(obs)
        categories = [classify_legal_option(state, option, idx).category for idx, option in enumerate(state.options)]
        self.assertEqual(
            categories,
            [
                ActionCategory.PLAY_SUPPORTER,
                ActionCategory.DRAW_OR_SEARCH,
                ActionCategory.PLAY_STADIUM,
                ActionCategory.PLAY_BASIC_TO_BENCH,
                ActionCategory.RARE_CANDY_EVOLVE,
                ActionCategory.END_TURN,
            ],
        )

    def test_decision_record_contains_categories_scores_choice_and_reason(self):
        p0 = player(pokemon(59), hand=[card(227), card(140)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_SETUP_BENCH,
                "type": 1,
                "minCount": 1,
                "maxCount": 1,
                "option": [
                    {"type": OPT_CARD, "area": AREA_HAND, "index": 0, "playerIndex": 0},
                    {"type": OPT_CARD, "area": AREA_HAND, "index": 1, "playerIndex": 0},
                ],
            },
        }
        state = normalize_state(obs)
        scores = [100.0, -50.0]
        choice = [0]
        record = build_decision_record(state, scores, choice)
        self.assertEqual(record["turn"], 3)
        self.assertEqual(record["chosen_index"], [0])
        self.assertEqual(record["legal_options"][0]["category"], ActionCategory.SETUP_CHOOSE_BENCH)
        self.assertIn("two-prize liability", record["legal_options"][1]["reason"])
        self.assertIn("reason", record)
        self.assertTrue(explain_choice(state, choice, scores))

    def test_state_machine_identifies_setup_moment(self):
        p0 = player(pokemon(59), hand=[card(227)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_SETUP_BENCH,
                "type": 1,
                "minCount": 0,
                "maxCount": 1,
                "option": [{"type": OPT_CARD, "area": AREA_HAND, "index": 0, "playerIndex": 0}],
            },
        }
        self.assertEqual(self.moment_for(obs), MomentType.SETUP)

    def test_state_machine_identifies_attack_selection_moment(self):
        attacks = get_db().get_card(229).attacks
        p0 = player(pokemon(229, energies=[7, 7]), hand=[])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [
                    {"type": OPT_ATTACK, "attackId": attacks[0].attack_id},
                    {"type": OPT_END},
                ],
            },
        }
        self.assertEqual(self.moment_for(obs), MomentType.ATTACK_SELECTION)

    def test_state_machine_identifies_effect_resolution_moment(self):
        p0 = player(pokemon(59), hand=[])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_TO_HAND,
                "type": 1,
                "minCount": 1,
                "maxCount": 1,
                "deck": [card(227)],
                "option": [{"type": OPT_CARD, "area": AREA_DECK, "index": 0, "playerIndex": 0}],
            },
        }
        self.assertEqual(self.moment_for(obs), MomentType.EFFECT_RESOLUTION)

    def test_state_machine_identifies_prize_and_replacement_moments(self):
        prize_obs = {
            "current": current(p0=player(pokemon(229), prizes=1)),
            "logs": [],
            "select": {
                "context": CTX_TO_HAND,
                "type": 1,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": OPT_CARD, "area": AREA_PRIZE, "index": 0, "playerIndex": 0}],
            },
        }
        promote_obs = {
            "current": current(p0=player(None, bench=[pokemon(229, energies=[7, 7])], hand=[])),
            "logs": [],
            "select": {
                "context": CTX_TO_ACTIVE,
                "type": 1,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": OPT_CARD, "area": AREA_BENCH, "index": 0, "playerIndex": 0}],
            },
        }
        self.assertEqual(self.moment_for(prize_obs), MomentType.PRIZE_SELECTION)
        self.assertEqual(self.moment_for(promote_obs), MomentType.FORCED_REPLACEMENT)

    def test_state_machine_identifies_opponent_turn_response_moment(self):
        obs = {
            "current": with_current(turn=2, firstPlayer=0),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 9,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": OPT_YES}, {"type": OPT_NO}],
            },
        }
        self.assertEqual(self.moment_for(obs), MomentType.OPPONENT_TURN_RESPONSE)

    def test_rule_reasoning_avoids_second_supporter(self):
        p0 = player(pokemon(59), hand=[card(1227), card(1121)])
        obs = {
            "current": with_current(p0=p0, supporterPlayed=True),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [
                    {"type": OPT_PLAY, "index": 0},
                    {"type": OPT_PLAY, "index": 1},
                ],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_rule_reasoning_avoids_second_manual_energy_attachment(self):
        p0 = player(pokemon(229), hand=[card(7)])
        obs = {
            "current": with_current(p0=p0, energyAttached=True),
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

    def test_rule_reasoning_first_player_first_turn_skips_attack_if_end_exists(self):
        db = get_db()
        attacks = db.get_card(229).attacks
        p0 = player(pokemon(229, energies=[7, 8, 5]), hand=[])
        p1 = player(pokemon(227, hp=10, max_hp=70, player=1), hand=None, player_index=1)
        obs = {
            "current": with_current(p0=p0, p1=p1, turn=1, firstPlayer=0),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [
                    {"type": OPT_ATTACK, "attackId": attacks[0].attack_id},
                    {"type": OPT_END},
                ],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_sequencing_immediate_ko_attack_beats_setup_card(self):
        db = get_db()
        attacks = db.get_card(229).attacks
        p0 = player(pokemon(229, energies=[7, 8, 5]), hand=[card(1086)])
        p1 = player(pokemon(227, hp=10, max_hp=70, player=1), hand=None, player_index=1)
        obs = {
            "current": current(p0=p0, p1=p1),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [
                    {"type": OPT_PLAY, "index": 0},
                    {"type": OPT_ATTACK, "attackId": attacks[1].attack_id},
                ],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_sequencing_uses_setup_before_low_impact_attack(self):
        db = get_db()
        attacks = db.get_card(59).attacks
        p0 = player(pokemon(59, energies=[5]), hand=[card(227)])
        p1 = player(pokemon(229, hp=330, max_hp=330, player=1), hand=None, player_index=1)
        obs = {
            "current": current(p0=p0, p1=p1),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [
                    {"type": OPT_PLAY, "index": 0},
                    {"type": OPT_ATTACK, "attackId": attacks[0].attack_id},
                ],
            },
        }
        self.assertEqual(agent(obs), [0])

    def test_sequencing_avoids_unnecessary_draw_at_deckout_risk(self):
        p0 = player(pokemon(229), hand=[card(1227)])
        p0["deckCount"] = 2
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
                    {"type": OPT_END},
                ],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_prize_selection_hidden_prizes_prefers_top_index_deterministically(self):
        p0 = player(pokemon(229), prizes=3)
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_TO_HAND,
                "type": 1,
                "minCount": 1,
                "maxCount": 1,
                "option": [
                    {"type": OPT_CARD, "area": AREA_PRIZE, "index": 0, "playerIndex": 0},
                    {"type": OPT_CARD, "area": AREA_PRIZE, "index": 1, "playerIndex": 0},
                    {"type": OPT_CARD, "area": AREA_PRIZE, "index": 2, "playerIndex": 0},
                ],
            },
        }
        self.assertEqual(agent(obs), [2])

    def test_prize_selection_revealed_prize_prefers_missing_attacker_piece(self):
        p0 = player(pokemon(227), prizes=3)
        p0["prize"] = [card(229), None, None]
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_TO_HAND,
                "type": 1,
                "minCount": 1,
                "maxCount": 1,
                "option": [
                    {"type": OPT_CARD, "area": AREA_PRIZE, "index": 0, "playerIndex": 0},
                    {"type": OPT_CARD, "area": AREA_PRIZE, "index": 2, "playerIndex": 0},
                ],
            },
        }
        self.assertEqual(agent(obs), [0])

    def test_promote_after_ko_prefers_attacker_that_can_attack(self):
        p0 = player(None, bench=[pokemon(227), pokemon(229, energies=[7, 7])], hand=[])
        obs = {
            "current": current(p0=p0),
            "logs": [],
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
        self.assertEqual(agent(obs), [1])

    def test_forced_discard_protects_only_hydreigon_when_energy_available(self):
        p0 = player(pokemon(227), hand=[card(229), card(7)])
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
                ],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_search_choice_prioritizes_deino_when_not_enough_basics(self):
        p0 = player(pokemon(59), hand=[])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_TO_HAND,
                "type": 1,
                "minCount": 1,
                "maxCount": 1,
                "deck": [card(140), card(227)],
                "option": [
                    {"type": OPT_CARD, "area": AREA_DECK, "index": 0, "playerIndex": 0},
                    {"type": OPT_CARD, "area": AREA_DECK, "index": 1, "playerIndex": 0},
                ],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_guardrail_uses_free_draw_ability_before_supporter(self):
        p0 = player(pokemon(59), bench=[pokemon(140)], hand=[card(1227)])
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
                    {"type": OPT_ABILITY, "area": AREA_BENCH, "index": 0, "playerIndex": 0},
                ],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_guardrail_search_before_non_enabling_attachment(self):
        p0 = player(pokemon(229, energies=[]), hand=[card(7), card(1086)])
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
                    {"type": OPT_PLAY, "index": 1},
                ],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_guardrail_boss_without_payoff_loses_to_setup(self):
        p0 = player(pokemon(59), hand=[card(1182), card(1086)])
        p1 = player(pokemon(227, hp=70, max_hp=70, player=1), bench=[pokemon(833, player=1)], hand=None, player_index=1)
        obs = {
            "current": current(p0=p0, p1=p1),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [
                    {"type": OPT_PLAY, "index": 0},
                    {"type": OPT_PLAY, "index": 1},
                ],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_guardrail_recovery_cards_not_used_with_empty_discard(self):
        p0 = player(pokemon(59), hand=[card(1129), card(1086)])
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
                ],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_guardrail_energy_recycler_waits_for_enough_energy_in_discard(self):
        p0 = player(pokemon(59), hand=[card(1139), card(1086)], discard=[card(7)])
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
                ],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_guardrail_bad_retreat_can_pass(self):
        p0 = player(pokemon(229, energies=[7, 7]), bench=[pokemon(227)], hand=[])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [
                    {"type": OPT_RETREAT},
                    {"type": OPT_END},
                ],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_guardrail_end_turn_after_safe_attachment_is_available(self):
        p0 = player(pokemon(229, energies=[]), hand=[card(7)])
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
        self.assertEqual(agent(obs), [0])

    def test_discard_prefers_basic_energy_over_protected_attacker(self):
        p0 = player(pokemon(721), hand=[card(3), card(723)])
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
                ],
            },
        }
        self.assertEqual(agent(obs), [0])

    def test_energy_attach_prefers_active_attacker(self):
        p0 = player(pokemon(721, energies=[]), bench=[pokemon(722)], hand=[card(3)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": 0,
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

    def test_attack_ko_beats_end_turn(self):
        db = get_db()
        attacks = db.get_card(723).attacks
        p0 = player(pokemon(723, energies=[3, 3, 3]), hand=[], discard=[card(3), card(3), card(3)])
        p1 = player(pokemon(721, hp=200, max_hp=200, player=1), hand=None, player_index=1)
        obs = {
            "current": current(p0=p0, p1=p1),
            "logs": [],
            "select": {
                "context": 0,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [
                    {"type": OPT_ATTACK, "attackId": attacks[0].attack_id},
                    {"type": OPT_ATTACK, "attackId": attacks[1].attack_id},
                    {"type": OPT_END},
                ],
            },
        }
        result = agent(obs)
        self.assertIn(result[0], [0, 1])
        choice, rows = debug_scores(obs)
        self.assertIn(choice[0], [0, 1])
        self.assertGreater(max(score for _, score, label in rows if label.startswith("ATTACK")), 10000)


if __name__ == "__main__":
    unittest.main()
