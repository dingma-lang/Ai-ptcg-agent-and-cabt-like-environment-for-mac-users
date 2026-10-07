import unittest

from core.energy_planner_zoroark import score_energy_attachment_zoroark, score_ns_pp_up_option
from state_eval import CTX_MAIN, OPT_PLAY, normalize_state


def pokemon(card_id, hp=100, energy=None):
    return {"id": card_id, "hp": hp, "maxHp": hp, "energyCards": [{"id": cid} for cid in (energy or [])], "tools": []}


def state(active=None, bench=None, discard=None):
    return normalize_state({
        "logs": [],
        "current": {
            "yourIndex": 0,
            "turn": 3,
            "players": [
                {"active": [active or pokemon(293, 280)], "bench": bench or [], "hand": [], "discard": discard or [], "prize": [None] * 6, "deckCount": 40},
                {"active": [pokemon(235, 30)], "bench": [], "hand": [], "discard": [], "prize": [None] * 6, "deckCount": 40},
            ],
        },
        "select": {"context": CTX_MAIN, "minCount": 1, "maxCount": 1, "option": []},
    })


class EnergyDisciplineTests(unittest.TestCase):
    def test_first_darkness_to_zoroark_is_high_priority(self):
        s = state(active=pokemon(293, 280, []))
        self.assertGreater(score_energy_attachment_zoroark(s, 7, s.current["players"][0]["active"][0]).score, 5000)

    def test_second_darkness_to_zoroark_is_highest_priority(self):
        s = state(active=pokemon(293, 280, [7]))
        self.assertGreater(score_energy_attachment_zoroark(s, 7, s.current["players"][0]["active"][0]).score, 6500)

    def test_third_darkness_to_zoroark_is_blocked(self):
        s = state(active=pokemon(293, 280, [7, 7]))
        self.assertLess(score_energy_attachment_zoroark(s, 7, s.current["players"][0]["active"][0]).score, 0)

    def test_darkness_to_zekrom_is_blocked_normally(self):
        s = state(active=pokemon(293, 280, [7, 7]), bench=[pokemon(906, 130)])
        self.assertLess(score_energy_attachment_zoroark(s, 7, s.current["players"][0]["bench"][0]).score, 0)

    def test_darkness_to_copy_sources_and_supports_is_hard_blocked(self):
        for cid in (906, 303, 257, 258, 689, 112, 141, 140):
            with self.subTest(cid=cid):
                s = state(active=pokemon(293, 280, [7, 7]), bench=[pokemon(cid, 130)])
                self.assertLess(score_energy_attachment_zoroark(s, 7, s.current["players"][0]["bench"][0]).score, -1000)

    def test_support_only_energy_is_blocked(self):
        for cid in (122, 235, 1071, 140):
            s = state(active=pokemon(cid, 70))
            self.assertLess(score_energy_attachment_zoroark(s, 7, s.current["players"][0]["active"][0]).score, -1000)

    def test_pp_up_requires_darkness_in_discard(self):
        s = state(active=pokemon(293, 280, [7]), bench=[pokemon(292, 70)], discard=[])
        self.assertLess(score_ns_pp_up_option(s, {"type": OPT_PLAY, "cardId": 1113}), 0)
        s2 = state(active=pokemon(293, 280, [7]), bench=[pokemon(292, 70)], discard=[{"id": 7}])
        self.assertGreater(score_ns_pp_up_option(s2, {"type": OPT_PLAY, "cardId": 1113}), 0)


if __name__ == "__main__":
    unittest.main()
