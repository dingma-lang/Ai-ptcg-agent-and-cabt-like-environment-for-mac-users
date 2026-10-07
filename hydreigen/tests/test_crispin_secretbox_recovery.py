from __future__ import annotations

import unittest

from agent import agent
from core.recovery_timing_planner import score_energy_recycler, score_sacred_ash
from state_eval import CTX_MAIN, OPT_END, OPT_PLAY, normalize_state
from tests.test_round_plan import card, current, player, pokemon


class CrispinSecretBoxRecoveryTests(unittest.TestCase):
    def test_hydreigon_no_energy_hand_crispin_legal(self):
        p0 = player(pokemon(229), hand=[card(1198)])
        obs = obs_main(p0, [{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [0])

    def test_hydreigon_enough_energy_does_not_force_crispin(self):
        p0 = player(pokemon(229, energies=[card(7), card(8), card(5), card(7)]), hand=[card(1198)])
        state = normalize_state(obs_main(p0, [{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}]))
        self.assertLessEqual(__import__("core.crispin_planner", fromlist=["score_crispin_option"]).score_crispin_option(state, state.options[0]), 0)

    def test_secret_box_early_weak_hand_is_used(self):
        p0 = player(pokemon(59), hand=[card(1092), card(7), card(7), card(1174)])
        obs = obs_main(p0, [{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}], turn=2)
        self.assertEqual(agent(obs), [0])

    def test_energy_recycler_threshold(self):
        low_player = player(pokemon(229), hand=[])
        low_player["discard"] = [card(7), card(8)]
        high_player = player(pokemon(229), hand=[])
        high_player["discard"] = [card(7), card(8), card(5), card(7)]
        low = normalize_state(obs_main(low_player, []))
        high = normalize_state(obs_main(high_player, []))
        self.assertLess(score_energy_recycler(low), 0)
        self.assertGreater(score_energy_recycler(high), 0)

    def test_sacred_ash_threshold(self):
        low_player = player(pokemon(229), hand=[])
        low_player["discard"] = [card(59), card(833)]
        high_player = player(pokemon(229), hand=[])
        high_player["discard"] = [card(59), card(833), card(227), card(771)]
        low = normalize_state(obs_main(low_player, []))
        high = normalize_state(obs_main(high_player, []))
        self.assertLess(score_sacred_ash(low), 0)
        self.assertGreater(score_sacred_ash(high), 0)


def obs_main(p0, options, turn=5):
    return {"current": current(p0=p0, turn=turn), "logs": [], "select": {"context": CTX_MAIN, "type": 0, "minCount": 1 if options else 0, "maxCount": 1 if options else 0, "option": options}}


if __name__ == "__main__":
    unittest.main()
