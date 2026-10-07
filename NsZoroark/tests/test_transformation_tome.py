import unittest

from core.transformation_tome_planner import score_transformation_tome_option, score_transformation_tome_selection_zoroark
from state_eval import CTX_MAIN, CTX_TO_HAND, OPT_CARD, OPT_PLAY, normalize_state


def pokemon(card_id, hp=100):
    return {"id": card_id, "hp": hp, "maxHp": hp, "energyCards": [], "tools": []}


def state(hand, discard=None, options=None, context=CTX_MAIN):
    return normalize_state({
        "logs": [],
        "current": {
            "yourIndex": 0,
            "turn": 3,
            "players": [
                {"active": [pokemon(122, 70)], "bench": [], "hand": hand, "discard": discard or [], "prize": [None] * 6, "deckCount": 40},
                {"active": [pokemon(235, 30)], "bench": [], "hand": [], "discard": [], "prize": [None] * 6, "deckCount": 40},
            ],
        },
        "select": {"context": context, "contextCardName": "Transformation Tome", "minCount": 1, "maxCount": 1, "option": options or []},
    })


class TransformationTomeTests(unittest.TestCase):
    def test_one_tome_is_blocked(self):
        s = state([{"name": "Transformation Tome"}], options=[{"type": OPT_PLAY, "cardName": "Transformation Tome"}])
        self.assertLess(score_transformation_tome_option(s, s.options[0]), 0)

    def test_two_tome_with_useful_basic_is_valued(self):
        s = state(
            [{"name": "Transformation Tome"}, {"name": "Transformation Tome"}],
            discard=[{"id": 906}],
            options=[{"type": OPT_PLAY, "cardName": "Transformation Tome"}],
        )
        self.assertGreater(score_transformation_tome_option(s, s.options[0]), 0)

    def test_tome_target_zekrom_when_copy_source_missing(self):
        s = state(
            [{"name": "Transformation Tome"}, {"name": "Transformation Tome"}],
            discard=[{"id": 906}],
            options=[{"type": OPT_CARD, "cardId": 906}],
            context=CTX_TO_HAND,
        )
        self.assertGreater(score_transformation_tome_selection_zoroark(s, 906), 6000)

    def test_random_tome_swap_is_avoided(self):
        s = state(
            [{"name": "Transformation Tome"}, {"name": "Transformation Tome"}],
            discard=[],
            options=[{"type": OPT_PLAY, "cardName": "Transformation Tome"}],
        )
        self.assertLess(score_transformation_tome_option(s, s.options[0]), 0)


if __name__ == "__main__":
    unittest.main()
