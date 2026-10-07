import unittest

from core.copy_target_planner import CopyChoice
from core.damage_math_planner import calculate_zoroark_damage, damage_with_modifiers
from state_eval import CTX_MAIN, normalize_state


def pokemon(card_id, hp=100, energy=None, tools=None, poisoned=False):
    return {"id": card_id, "hp": hp, "maxHp": hp, "energyCards": [{"id": cid} for cid in (energy or [])], "tools": [{"id": cid} for cid in (tools or [])], "poisoned": poisoned}


def state(target):
    return normalize_state({
        "logs": [],
        "current": {
            "yourIndex": 0,
            "turn": 3,
            "players": [
                {"active": [pokemon(293, 280, [7, 7])], "bench": [], "hand": [], "discard": [], "prize": [None] * 6, "deckCount": 40},
                {"active": [target], "bench": [], "hand": [], "discard": [], "prize": [None] * 6, "deckCount": 40},
            ],
        },
        "select": {"context": CTX_MAIN, "minCount": 1, "maxCount": 1, "option": []},
    })


class ZoroarkDamageMathTests(unittest.TestCase):
    def test_zoroark_copying_zekrom_is_250(self):
        self.assertEqual(damage_with_modifiers(250), 250)

    def test_binding_mochi_poison_reaches_290(self):
        self.assertEqual(damage_with_modifiers(250, binding_mochi=True), 290)

    def test_black_belt_against_ex_reaches_290(self):
        self.assertEqual(damage_with_modifiers(250, black_belt=True, target_ex=True), 290)

    def test_mochi_and_black_belt_reaches_330(self):
        self.assertEqual(damage_with_modifiers(250, binding_mochi=True, black_belt=True, target_ex=True), 330)

    def test_modifier_tracks_ko_math(self):
        s = state(pokemon(141, 290))
        math = calculate_zoroark_damage(s, CopyChoice(expected_damage=250), {"black_belt": True}, s.current["players"][1]["active"][0])
        self.assertTrue(math.is_ko)
        self.assertEqual(math.final_damage, 290)


if __name__ == "__main__":
    unittest.main()
