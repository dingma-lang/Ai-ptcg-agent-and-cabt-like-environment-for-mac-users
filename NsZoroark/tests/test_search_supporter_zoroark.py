import unittest

from core.search_planner_zoroark import score_discard_selection_zoroark, score_pokepad_target
from core.supporter_router_zoroark import choose_best_supporter_zoroark
from policy import choose_action
from state_eval import CTX_MAIN, CTX_TO_HAND, OPT_CARD, OPT_END, OPT_PLAY, normalize_state


def pokemon(card_id, hp=100, energy=None):
    return {"id": card_id, "hp": hp, "maxHp": hp, "energyCards": [{"id": cid} for cid in (energy or [])], "tools": []}


def card(card_id):
    return {"id": card_id}


def obs(hand=None, active=None, bench=None, options=None, logs=None):
    return {
        "logs": logs or [],
        "current": {
            "yourIndex": 0,
            "turn": 3,
            "supporterPlayed": False,
            "players": [
                {"active": [active or pokemon(292, 70)], "bench": bench or [], "hand": hand or [], "discard": [], "prize": [None] * 6, "deckCount": 40},
                {"active": [pokemon(141, 190)], "bench": [], "hand": [], "discard": [], "prize": [None] * 6, "deckCount": 40},
            ],
        },
        "select": {"context": CTX_MAIN, "minCount": 1, "maxCount": 1, "option": options or []},
    }


class SearchSupporterTests(unittest.TestCase):
    def test_cyrano_for_zoroark_ex_when_zorua_ready(self):
        game = obs(hand=[card(1205)], options=[{"type": OPT_PLAY, "cardId": 1205}, {"type": OPT_END}])
        self.assertEqual(choose_action(game), [0])

    def test_pokepad_blocks_rulebox_zoroark_ex_target(self):
        s = normalize_state(obs())
        self.assertLess(score_pokepad_target(s, 293, "N's Zoroark ex"), 0)

    def test_ultra_ball_discard_only_zekrom_is_bad(self):
        game = obs(hand=[card(1121), card(906), card(293)], options=[{"type": OPT_CARD, "cardId": 906}], active=pokemon(292, 70))
        game["select"]["context"] = 8
        s = normalize_state(game)
        self.assertLess(score_discard_selection_zoroark(s, 906), 0)

    def test_fezandipiti_after_ko_is_searchable(self):
        game = obs(logs=["Our Pokemon was Knocked Out last turn."], active=pokemon(293, 280), hand=[card(1121), card(1227), card(1227)], options=[{"type": OPT_PLAY, "cardId": 1121}, {"type": OPT_END}])
        self.assertEqual(choose_action(game), [0])

    def test_lillie_only_hand_card_is_playable(self):
        game = obs(hand=[card(1227)], options=[{"type": OPT_PLAY, "cardId": 1227}, {"type": OPT_END}])
        s = normalize_state(game)
        decision = choose_best_supporter_zoroark(s, s.options)
        self.assertTrue(decision.should_use)
        self.assertEqual(decision.supporter_name, "Lillie's Determination")


if __name__ == "__main__":
    unittest.main()
