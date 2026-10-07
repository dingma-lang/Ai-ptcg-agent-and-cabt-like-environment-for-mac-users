from __future__ import annotations

import unittest

from agent import agent
from state_eval import AREA_DECK, CTX_MAIN, CTX_TO_BENCH, CTX_TO_HAND, OPT_ATTACK, OPT_CARD, OPT_END, OPT_PLAY
from tests.test_round_plan import card, current, player, pokemon


class PoffinPokePadPriorityTests(unittest.TestCase):
    def test_round_one_poffin_beats_supporter_attack_and_pass(self):
        p0 = player(pokemon(59), hand=[card(1086), card(1227)])
        attacks = __import__("card_db").get_db().get_card(59).attacks
        obs = {
            "current": current(p0=p0, turn=1),
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
        self.assertEqual(agent(obs), [0])

    def test_round_two_one_bench_poffin_is_still_best(self):
        p0 = player(pokemon(59), bench=[pokemon(227)], hand=[card(1086), card(1227)])
        obs = {
            "current": current(p0=p0, turn=2),
            "logs": [],
            "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": [{"type": OPT_PLAY, "index": 0}, {"type": OPT_PLAY, "index": 1}, {"type": OPT_END}]},
        }
        self.assertEqual(agent(obs), [0])

    def test_bench_two_missing_core_basics_uses_poffin(self):
        p0 = player(pokemon(59), bench=[pokemon(227), pokemon(140)], hand=[card(1086)])
        obs = {
            "current": current(p0=p0, turn=3),
            "logs": [],
            "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": [{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}]},
        }
        self.assertEqual(agent(obs), [0])

    def test_poffin_is_held_when_core_basics_present_and_bench_is_developed(self):
        p0 = player(pokemon(59), bench=[pokemon(227), pokemon(227), pokemon(59), pokemon(833)], hand=[card(1086), card(1227)])
        obs = {
            "current": current(p0=p0, turn=5),
            "logs": [],
            "select": {
                "context": CTX_MAIN,
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": OPT_PLAY, "index": 1}, {"type": OPT_PLAY, "index": 0}, {"type": OPT_END}],
            },
        }
        self.assertEqual(agent(obs), [0])

    def test_poffin_search_no_deino_takes_deino_first(self):
        p0 = player(pokemon(59), hand=[])
        obs = poffin_prompt(p0, [card(59), card(227), card(833)])
        self.assertIn(1, agent(obs))

    def test_poffin_search_one_deino_takes_missing_gastly_and_toxel(self):
        p0 = player(pokemon(227), hand=[])
        obs = poffin_prompt(p0, [card(227), card(59), card(833)])
        self.assertEqual(set(agent(obs)), {1, 2})

    def test_poffin_active_deino_low_bench_takes_toxel_not_two_more_deino(self):
        p0 = player(pokemon(227), hand=[])
        obs = poffin_prompt_to_bench(p0, [card(227), card(227), card(833)], min_count=0, max_count=2)
        result = agent(obs)
        self.assertIn(2, result)
        self.assertNotEqual(set(result), {0, 1})

    def test_poffin_search_rejects_non_basic_and_high_hp_pokemon(self):
        p0 = player(pokemon(59), hand=[])
        obs = poffin_prompt(p0, [card(229), card(140), card(834), card(227), card(59)])
        self.assertEqual(set(agent(obs)), {3, 4})

    def test_poffin_to_bench_prompt_uses_basic_70_hp_or_less(self):
        p0 = player(pokemon(59), hand=[])
        obs = poffin_prompt_to_bench(p0, [card(141), card(833), card(228), card(227)])
        self.assertEqual(set(agent(obs)), {1, 3})

    def test_poffin_prompt_with_raw_effect_id_uses_only_eligible_basics(self):
        p0 = player(pokemon(59), hand=[])
        obs = poffin_prompt_to_bench(p0, [card(229), card(140), card(833), card(227)], effect=1086, min_count=0)
        self.assertEqual(set(agent(obs)), {2, 3})

    def test_poffin_prompt_with_effect_card_id_uses_only_eligible_basics(self):
        p0 = player(pokemon(59), hand=[])
        obs = poffin_prompt_to_bench(p0, [card(229), card(140), card(833), card(227)], effect=None, effect_card_id=1086, min_count=0)
        self.assertEqual(set(agent(obs)), {2, 3})

    def test_optional_poffin_prompt_takes_no_cards_when_no_eligible_basic_exists(self):
        p0 = player(pokemon(59), hand=[])
        obs = poffin_prompt_to_bench(p0, [card(229), card(140), card(834)], effect=1086, min_count=0)
        self.assertEqual(agent(obs), [])

    def test_poffin_prompt_caps_selection_to_open_bench_slots(self):
        p0 = player(pokemon(59), bench=[pokemon(227), pokemon(59), pokemon(833), pokemon(140)], hand=[])
        obs = poffin_prompt_to_bench(p0, [card(227), card(59), card(833)], effect=1086, min_count=0, max_count=2)
        self.assertEqual(len(agent(obs)), 1)

    def test_pokepad_legal_no_deino_uses_and_selects_deino(self):
        p0 = player(pokemon(59), hand=[card(1152)])
        play_obs = {"current": current(p0=p0, turn=2), "logs": [], "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": [{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}]}}
        self.assertEqual(agent(play_obs), [0])
        search_obs = pokepad_prompt(p0, [card(229), card(227)])
        self.assertEqual(agent(search_obs), [1])

    def test_pokepad_active_deino_low_bench_gets_toxel_bridge(self):
        p0 = player(pokemon(227), hand=[])
        obs = pokepad_prompt(p0, [card(227), card(833), card(59)])
        self.assertEqual(agent(obs), [1])

    def test_active_deino_benches_toxel_before_extra_deino(self):
        p0 = player(pokemon(227), hand=[card(227), card(833)])
        obs = {
            "current": current(p0=p0, turn=2),
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

    def test_pokepad_gastly_in_play_selects_haunter(self):
        p0 = player(pokemon(59), bench=[pokemon(227), pokemon(59)], hand=[])
        obs = pokepad_prompt(p0, [card(771), card(833), card(229)])
        self.assertEqual(agent(obs), [0])

    def test_pokepad_gets_basic_when_full_gengar_chain_is_in_hand(self):
        p0 = player(pokemon(227), hand=[card(771), card(772)])
        obs = pokepad_prompt(p0, [card(833), card(59), card(228)])
        self.assertEqual(agent(obs), [1])

    def test_pokepad_gets_stage_one_when_stage_two_is_in_hand(self):
        p0 = player(pokemon(59), hand=[card(772)])
        obs = pokepad_prompt(p0, [card(833), card(771), card(228)])
        self.assertEqual(agent(obs), [1])

    def test_ultra_ball_gets_missing_stage_two_for_live_chain(self):
        p0 = player(pokemon(771), hand=[])
        obs = {
            "current": current(p0=p0, turn=5),
            "logs": [],
            "select": {
                "context": CTX_TO_HAND,
                "type": 1,
                "minCount": 1,
                "maxCount": 1,
                "effect": card(1121),
                "deck": [card(228), card(772), card(833)],
                "option": [{"type": OPT_CARD, "area": AREA_DECK, "index": idx, "playerIndex": 0} for idx in range(3)],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_petrel_does_not_search_poffin_when_poffin_is_already_in_hand(self):
        p0 = player(pokemon(59), hand=[card(1086)])
        obs = {
            "current": current(p0=p0, turn=2),
            "logs": [],
            "select": {
                "context": CTX_TO_HAND,
                "type": 1,
                "minCount": 1,
                "maxCount": 1,
                "effect": card(1219),
                "deck": [card(1086), card(1092), card(1152)],
                "option": [{"type": OPT_CARD, "area": AREA_DECK, "index": idx, "playerIndex": 0} for idx in range(3)],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_pokepad_avoids_rule_box_targets(self):
        p0 = player(pokemon(59), hand=[])
        obs = pokepad_prompt(p0, [card(772), card(140), card(227)])
        self.assertEqual(agent(obs), [2])


def poffin_prompt(p0, deck):
    return {
        "current": current(p0=p0),
        "logs": [],
        "select": {
            "context": CTX_TO_HAND,
            "type": 1,
            "minCount": 2,
            "maxCount": 2,
            "effect": card(1086),
            "deck": deck,
            "option": [{"type": OPT_CARD, "area": AREA_DECK, "index": idx, "playerIndex": 0} for idx in range(len(deck))],
        },
    }


def poffin_prompt_to_bench(p0, deck, effect=None, effect_card_id=None, min_count=2, max_count=2):
    select = {
        "context": CTX_TO_BENCH,
        "type": 1,
        "minCount": min_count,
        "maxCount": max_count,
        "deck": deck,
        "option": [{"type": OPT_CARD, "area": AREA_DECK, "index": idx, "playerIndex": 0} for idx in range(len(deck))],
    }
    if effect_card_id is not None:
        select["effectCardId"] = effect_card_id
    else:
        select["effect"] = card(1086) if effect is None else effect
    return {
        "current": current(p0=p0),
        "logs": [],
        "select": select,
    }


def pokepad_prompt(p0, deck):
    return {
        "current": current(p0=p0),
        "logs": [],
        "select": {
            "context": CTX_TO_HAND,
            "type": 1,
            "minCount": 1,
            "maxCount": 1,
            "effect": card(1152),
            "deck": deck,
            "option": [{"type": OPT_CARD, "area": AREA_DECK, "index": idx, "playerIndex": 0} for idx in range(len(deck))],
        },
    }


if __name__ == "__main__":
    unittest.main()
