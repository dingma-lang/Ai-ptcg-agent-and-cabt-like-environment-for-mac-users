from __future__ import annotations

import unittest

from agent import agent
from core.supporter_router import choose_best_supporter
from state_eval import CTX_MAIN, OPT_END, OPT_PLAY, normalize_state
from tests.test_round_plan import card, current, player, pokemon


class SupporterRouterTests(unittest.TestCase):
    def test_weak_early_hand_can_use_lillie(self):
        p0 = player(pokemon(59), hand=[card(1227)])
        obs = obs_main(p0, [{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}], turn=2)
        decision = choose_best_supporter(normalize_state(obs), normalize_state(obs).options)
        self.assertEqual(decision.supporter_name, "Lillie's Determination")
        self.assertEqual(agent(obs), [0])

    def test_need_rare_candy_prefers_petrel_over_lillie(self):
        p0 = player(pokemon(227), hand=[card(1219), card(1227), card(229)])
        obs = obs_main(p0, [{"type": OPT_PLAY, "index": 0}, {"type": OPT_PLAY, "index": 1}, {"type": OPT_END}], turn=5)
        self.assertEqual(agent(obs), [0])

    def test_poffin_in_hand_is_played_before_petrel_for_poffin(self):
        p0 = player(pokemon(59), hand=[card(1086), card(1219)])
        obs = obs_main(p0, [{"type": OPT_PLAY, "index": 0}, {"type": OPT_PLAY, "index": 1}, {"type": OPT_END}], turn=2)
        self.assertEqual(agent(obs), [0])

    def test_poffin_missing_bench_incomplete_petrel_is_legal(self):
        p0 = player(pokemon(59), hand=[card(1219)])
        obs = obs_main(p0, [{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}], turn=2)
        self.assertEqual(agent(obs), [0])

    def test_hydreigon_needs_energy_crispin_is_used(self):
        p0 = player(pokemon(229, energies=[card(7), card(8)]), hand=[card(1198)])
        obs = obs_main(p0, [{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}], turn=5)
        self.assertEqual(agent(obs), [0])

    def test_missing_pokemon_package_dawn_is_used(self):
        p0 = player(pokemon(59), hand=[card(1231)])
        obs = obs_main(p0, [{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}], turn=5)
        self.assertEqual(agent(obs), [0])


def obs_main(p0, options, turn=3):
    return {"current": current(p0=p0, turn=turn), "logs": [], "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": options}}


if __name__ == "__main__":
    unittest.main()
