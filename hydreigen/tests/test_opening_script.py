from __future__ import annotations

import unittest

from core.opening_script import opening_script_action
from state_eval import CTX_MAIN, OPT_END, OPT_PLAY, normalize_state
from tests.test_round_plan import card, current, player, pokemon


class OpeningScriptTests(unittest.TestCase):
    def test_opening_script_selects_poffin(self):
        p0 = player(pokemon(59), hand=[card(1086), card(1227)])
        state = normalize_state({"current": current(p0=p0, turn=1), "logs": [], "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": [{"type": OPT_PLAY, "index": 0}, {"type": OPT_PLAY, "index": 1}, {"type": OPT_END}]}})
        intent = opening_script_action(state, state.options)
        self.assertIsNotNone(intent)
        self.assertEqual(intent.selected_option_indices, [0])

    def test_opening_script_selects_pokepad_when_no_poffin(self):
        p0 = player(pokemon(59), hand=[card(1152), card(1227)])
        state = normalize_state({"current": current(p0=p0, turn=1), "logs": [], "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": [{"type": OPT_PLAY, "index": 0}, {"type": OPT_PLAY, "index": 1}, {"type": OPT_END}]}})
        intent = opening_script_action(state, state.options)
        self.assertIsNotNone(intent)
        self.assertEqual(intent.selected_option_indices, [0])


if __name__ == "__main__":
    unittest.main()
