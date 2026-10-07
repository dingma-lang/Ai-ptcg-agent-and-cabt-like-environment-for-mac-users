from __future__ import annotations

import unittest

from agent import agent
from core.stuck_detector import detect_stalled_setup
from state_eval import AREA_ACTIVE, AREA_BENCH, AREA_HAND, CTX_MAIN, OPT_ABILITY, OPT_ATTACK, OPT_END, OPT_EVOLVE, OPT_PLAY, normalize_state
from tests.test_round_plan import card, current, player, pokemon


class StuckDetectorTests(unittest.TestCase):
    def test_pass_with_poffin_legal_is_forced_to_poffin(self):
        p0 = player(pokemon(59), hand=[card(1086)])
        obs = obs_main(p0, [{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [0])

    def test_weak_attack_with_pokepad_no_deino_is_forced_to_pokepad(self):
        attacks = __import__("card_db").get_db().get_card(59).attacks
        p0 = player(pokemon(59), hand=[card(1152)])
        obs = obs_main(p0, [{"type": OPT_PLAY, "index": 0}, {"type": OPT_ATTACK, "attackId": attacks[0].attack_id}])
        self.assertEqual(agent(obs), [0])

    def test_no_bench_growth_after_turn_two_flags_stall(self):
        p0 = player(pokemon(59), hand=[card(1086)])
        obs = obs_main(p0, [{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}], turn=6)
        report = detect_stalled_setup(None, normalize_state(obs), normalize_state(obs).options)
        self.assertTrue(report.is_stuck)

    def test_legal_mega_gengar_evolution_forced(self):
        p0 = player(pokemon(771), hand=[card(772)])
        obs = obs_main(p0, [{"type": OPT_EVOLVE, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [0])

    def test_legal_toxtricity_ability_forced(self):
        p0 = player(pokemon(834), bench=[pokemon(772)], hand=[])
        obs = obs_main(p0, [{"type": OPT_ABILITY, "area": AREA_ACTIVE, "index": 0, "playerIndex": 0, "playerIndex": 0}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [0])


def obs_main(p0, options, turn=5):
    return {"current": current(p0=p0, turn=turn), "logs": [], "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": options}}


if __name__ == "__main__":
    unittest.main()
