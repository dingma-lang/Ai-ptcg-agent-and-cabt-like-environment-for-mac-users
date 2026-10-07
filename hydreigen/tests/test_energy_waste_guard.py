from __future__ import annotations

import unittest

from agent import agent
from state_eval import AREA_ACTIVE, AREA_BENCH, AREA_HAND, CTX_MAIN, OPT_ATTACH, OPT_END
from tests.test_round_plan import card, current, player, pokemon


class EnergyWasteGuardTests(unittest.TestCase):
    def test_energy_to_toxel_is_blocked(self):
        self.assert_bad_target(833)

    def test_energy_to_toxtricity_is_blocked(self):
        self.assert_bad_target(834)

    def test_energy_to_pecharunt_is_blocked(self):
        self.assert_bad_target(141)

    def test_energy_to_hydreigon_line_allowed(self):
        p0 = player(pokemon(227), hand=[card(8)])
        obs = attach_obs(p0, [{"type": OPT_ATTACH, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [0])

    def test_energy_to_mega_gengar_line_allowed(self):
        p0 = player(pokemon(772), hand=[card(7)])
        obs = attach_obs(p0, [{"type": OPT_ATTACH, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [0])

    def test_disposable_active_prefers_bench_line(self):
        p0 = player(pokemon(833), bench=[pokemon(227)], hand=[card(5)])
        obs = attach_obs(
            p0,
            [
                {"type": OPT_ATTACH, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
                {"type": OPT_ATTACH, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_BENCH, "inPlayIndex": 0},
            ],
        )
        self.assertEqual(agent(obs), [1])

    def assert_bad_target(self, pid):
        p0 = player(pokemon(pid), hand=[card(7)])
        obs = attach_obs(p0, [{"type": OPT_ATTACH, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [1])


def attach_obs(p0, options):
    return {"current": current(p0=p0), "logs": [], "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": options}}


if __name__ == "__main__":
    unittest.main()
