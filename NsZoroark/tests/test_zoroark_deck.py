import unittest

from policy import choose_action
from state_eval import AREA_ACTIVE, AREA_BENCH, CTX_MAIN, OPT_ATTACH, OPT_END, OPT_EVOLVE, OPT_PLAY


def pokemon(card_id, hp=100, energy=None):
    return {"id": card_id, "hp": hp, "maxHp": hp, "energyCards": [{"id": cid} for cid in (energy or [])], "tools": []}


def card(card_id):
    return {"id": card_id}


def obs(active, bench=None, hand=None, options=None, discard=None, turn=1):
    return {
        "logs": [],
        "current": {
            "yourIndex": 0,
            "turn": turn,
            "firstPlayer": 0,
            "supporterPlayed": False,
            "energyAttached": False,
            "players": [
                {"active": [active] if active else [], "bench": bench or [], "hand": hand or [], "discard": discard or [], "prize": [None] * 6, "deckCount": 40},
                {"active": [pokemon(235, 30)], "bench": [], "hand": [], "discard": [], "prize": [None] * 6, "deckCount": 40},
            ],
        },
        "select": {"context": CTX_MAIN, "minCount": 1, "maxCount": 1, "option": options or []},
    }


class ZoroarkDeckTests(unittest.TestCase):
    def test_opening_uses_poffin_for_zorua_setup(self):
        game = obs(
            active=pokemon(122, 70),
            hand=[card(1086)],
            options=[{"type": OPT_PLAY, "cardId": 1086}, {"type": OPT_END}],
        )
        self.assertEqual(choose_action(game), [0])

    def test_evolves_zorua_to_zoroark_when_legal(self):
        game = obs(
            active=pokemon(292, 70),
            hand=[card(293)],
            options=[{"type": OPT_EVOLVE, "cardId": 293, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0}, {"type": OPT_END}],
        )
        self.assertEqual(choose_action(game), [0])

    def test_attaches_second_darkness_to_zoroark(self):
        game = obs(
            active=pokemon(293, 280, [7]),
            hand=[card(7)],
            options=[{"type": OPT_ATTACH, "cardId": 7, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0}, {"type": OPT_END}],
        )
        self.assertEqual(choose_action(game), [0])

    def test_does_not_attach_third_darkness_to_same_zoroark_when_backup_exists(self):
        game = obs(
            active=pokemon(293, 280, [7, 7]),
            bench=[pokemon(292, 70)],
            hand=[card(7)],
            options=[
                {"type": OPT_ATTACH, "cardId": 7, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
                {"type": OPT_ATTACH, "cardId": 7, "inPlayArea": AREA_BENCH, "inPlayIndex": 0},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(choose_action(game), [1])

    def test_searches_for_zekrom_copy_source_when_missing(self):
        game = obs(
            active=pokemon(293, 280, [7, 7]),
            hand=[card(1152)],
            options=[{"type": OPT_PLAY, "cardId": 1152}, {"type": OPT_END}],
        )
        self.assertEqual(choose_action(game), [0])


if __name__ == "__main__":
    unittest.main()
