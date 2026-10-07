from __future__ import annotations

import unittest

from agent import agent
from card_db import get_db
from state_eval import CTX_MAIN, OPT_ATTACK, OPT_END
from tests.test_round_plan import card, current, player, pokemon


class CallForFamilyPlannerTests(unittest.TestCase):
    def test_active_toxel_early_uses_call_for_family_with_weak_bench(self):
        attacks = get_db().get_card(833).attacks
        p0 = player(pokemon(833), hand=[])
        obs = obs_main(p0, [{"type": OPT_ATTACK, "attackId": attacks[0].attack_id}, {"type": OPT_END}], turn=2)
        self.assertEqual(agent(obs), [0])

    def test_call_for_family_before_expected_ko(self):
        attacks = get_db().get_card(833).attacks
        p0 = player(pokemon(833), bench=[pokemon(227)], hand=[])
        obs = obs_main(p0, [{"type": OPT_ATTACK, "attackId": attacks[0].attack_id}, {"type": OPT_END}], turn=2)
        self.assertEqual(agent(obs), [0])

    def test_main_attacker_ko_beats_call_for_family(self):
        attacks = get_db().get_card(229).attacks
        p0 = player(pokemon(229, energies=[card(7), card(8), card(5), card(7)]), hand=[])
        p1 = player(pokemon(227, hp=70, max_hp=70, player=1), hand=None, player_index=1)
        obs = obs_main(p0, [{"type": OPT_ATTACK, "attackId": attacks[0].attack_id}, {"type": OPT_END}], p1=p1, turn=5)
        self.assertEqual(agent(obs), [0])


def obs_main(p0, options, p1=None, turn=3):
    return {"current": current(p0=p0, p1=p1, turn=turn), "logs": [], "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": options}}


if __name__ == "__main__":
    unittest.main()
