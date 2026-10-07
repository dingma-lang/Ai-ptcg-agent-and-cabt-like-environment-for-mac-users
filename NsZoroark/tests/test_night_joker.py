import unittest

from core.copy_target_planner import choose_best_benched_n_attack_to_copy
from core.night_joker_planner import score_night_joker_option, zoroark_attack_locked_by_logs
from policy import score_attack
from state_eval import CTX_ATTACK, OPT_ATTACK, normalize_state


def pokemon(card_id, hp=100, energy=None):
    return {"id": card_id, "hp": hp, "maxHp": hp, "energyCards": [{"id": cid} for cid in (energy or [])], "tools": []}


def state(active, bench, opponent_active, opponent_discard=None, logs=None):
    return normalize_state({
        "logs": logs or [],
        "current": {
            "yourIndex": 0,
            "turn": 3,
            "players": [
                {"active": [active], "bench": bench, "hand": [], "discard": [], "prize": [None] * 6, "deckCount": 40},
                {"active": [opponent_active], "bench": [], "hand": [], "discard": opponent_discard or [], "prize": [None] * 6, "deckCount": 40},
            ],
        },
        "select": {"context": CTX_ATTACK, "minCount": 1, "maxCount": 1, "option": [{"type": OPT_ATTACK, "attackName": "Night Joker"}]},
    })


class NightJokerTests(unittest.TestCase):
    def test_zoroark_copies_zekrom_for_ko(self):
        s = state(pokemon(293, 280, [7, 7]), [pokemon(906, 130)], pokemon(141, 190))
        self.assertGreater(score_night_joker_option(s, s.options[0], 0), 10000)

    def test_attack_lock_is_not_global(self):
        s = state(
            pokemon(293, 280, [7, 7]),
            [pokemon(293, 280, [7, 7]), pokemon(906, 130)],
            pokemon(141, 190),
            logs=["N's Zoroark ex used Rampaging Thunder. During your next turn, this Pokemon can't use attacks."],
        )
        self.assertTrue(zoroark_attack_locked_by_logs(s))
        self.assertTrue(any(p["id"] == 293 for p in s.current["players"][0]["bench"]))

    def test_back_draft_can_outscore_zekrom_when_discard_is_large(self):
        s = state(pokemon(293, 280, [7, 7]), [pokemon(906, 130), pokemon(258, 140)], pokemon(293, 280), opponent_discard=[{"id": 7}] * 10)
        choice = choose_best_benched_n_attack_to_copy(s)
        self.assertEqual(choice.copied_attack_name, "Back Draft")

    def test_flamebody_without_bench_value_is_bad(self):
        s = state(pokemon(293, 280, [7, 7]), [pokemon(258, 140)], pokemon(293, 280))
        choices = [c for c in __import__("core.copy_target_planner", fromlist=["choices_for_source"]).choices_for_source(s, s.current["players"][0]["bench"][0], "N's Darmanitan", 280)]
        flame = [c for c in choices if c.copied_attack_name == "Flamebody Cannon"][0]
        self.assertLess(flame.score, 0)

    def test_direct_zekrom_attack_is_blocked(self):
        s = state(pokemon(906, 130, [7, 7]), [pokemon(293, 280, [7, 7])], pokemon(141, 190))
        self.assertLess(score_attack(s, s.options[0], 0, s.options), -1000)


if __name__ == "__main__":
    unittest.main()
