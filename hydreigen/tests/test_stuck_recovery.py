from __future__ import annotations

import unittest

from agent import agent
from state_eval import CTX_MAIN, OPT_ABILITY, OPT_END, OPT_PLAY
from tests.test_round_plan import card, current, player, pokemon


class StuckRecoveryTests(unittest.TestCase):
    def test_pass_with_poffin_in_hand_forces_poffin(self):
        p0 = player(pokemon(59), hand=[card(1086)])
        obs = obs_main(p0, [{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}], turn=5)
        self.assertEqual(agent(obs), [0])

    def test_pass_when_petrel_can_get_rare_candy_forces_petrel(self):
        p0 = player(pokemon(227), hand=[card(1219), card(229)])
        obs = obs_main(p0, [{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}], turn=5)
        self.assertEqual(agent(obs), [0])

    def test_hydreigon_no_energy_forces_crispin(self):
        p0 = player(pokemon(229), hand=[card(1198)])
        obs = obs_main(p0, [{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}], turn=5)
        self.assertEqual(agent(obs), [0])

    def test_toxtricity_ability_forced_when_legal(self):
        p0 = player(pokemon(834), bench=[pokemon(229, energies=[card(7), card(8)])], hand=[])
        obs = obs_main(p0, [{"type": OPT_ABILITY, "area": 4, "index": 0, "playerIndex": 0}, {"type": OPT_END}], turn=5)
        self.assertEqual(agent(obs), [0])

    def test_recovery_too_early_is_blocked(self):
        p0 = player(pokemon(229), hand=[card(1139)])
        p0["discard"] = [card(7), card(8)]
        obs = obs_main(p0, [{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}], turn=5)
        self.assertEqual(agent(obs), [1])


def obs_main(p0, options, turn=5):
    return {"current": current(p0=p0, turn=turn), "logs": [], "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": options}}


if __name__ == "__main__":
    unittest.main()
