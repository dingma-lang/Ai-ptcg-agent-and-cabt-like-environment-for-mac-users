from __future__ import annotations

import unittest

from agent import agent
from state_eval import AREA_ACTIVE, AREA_BENCH, AREA_HAND, CTX_ATTACH_TO, CTX_MAIN, OPT_ABILITY, OPT_ATTACK, OPT_CARD, OPT_END, OPT_EVOLVE
from tests.test_round_plan import card, current, player, pokemon


class ToxtricityEngineTests(unittest.TestCase):
    def test_evolve_toxel_to_toxtricity_when_mega_gengar_needs_darkness(self):
        p0 = player(pokemon(833), bench=[pokemon(772)], hand=[card(834)])
        obs = obs_main(p0, [{"type": OPT_EVOLVE, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [0])

    def test_toxtricity_ability_with_mega_gengar_target(self):
        p0 = player(pokemon(834), bench=[pokemon(772)], hand=[])
        obs = obs_main(p0, [{"type": OPT_ABILITY, "area": AREA_ACTIVE, "index": 0, "playerIndex": 0}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [0])

    def test_toxtricity_ability_uses_active_hydreigon_missing_darkness(self):
        p0 = player(pokemon(229, energies=[card(5), card(8)]), bench=[pokemon(834)], hand=[])
        obs = obs_main(p0, [{"type": OPT_ABILITY, "area": AREA_BENCH, "index": 0, "playerIndex": 0}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [0])

    def test_toxtricity_attack_without_ko_is_not_main_plan(self):
        attacks = __import__("card_db").get_db().get_card(834).attacks
        p0 = player(pokemon(834, energies=[card(7), card(7), card(7)]), hand=[])
        p1 = player(pokemon(229, hp=330, max_hp=330, player=1), hand=None, player_index=1)
        obs = obs_main(p0, [{"type": OPT_ATTACK, "attackId": attacks[1].attack_id}, {"type": OPT_END}], p1=p1)
        self.assertEqual(agent(obs), [1])

    def test_toxtricity_ability_avoids_target_that_is_too_damaged(self):
        p0 = player(pokemon(834), bench=[pokemon(772, hp=10, max_hp=350)], hand=[])
        obs = obs_main(p0, [{"type": OPT_ABILITY, "area": AREA_ACTIVE, "index": 0, "playerIndex": 0}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [1])

    def test_toxtricity_sinister_surge_target_avoids_itself(self):
        p0 = player(pokemon(834), bench=[pokemon(772)], hand=[])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_ATTACH_TO,
                "type": 1,
                "minCount": 1,
                "maxCount": 1,
                "effect": card(834),
                "option": [
                    {"type": OPT_CARD, "area": AREA_ACTIVE, "index": 0, "playerIndex": 0},
                    {"type": OPT_CARD, "area": AREA_BENCH, "index": 0, "playerIndex": 0},
                ],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_toxtricity_target_prefers_hydreigon_missing_attack_energy_over_gengar(self):
        p0 = player(pokemon(229, energies=[card(5), card(8)]), bench=[pokemon(834), pokemon(772, energies=[card(7)])], hand=[])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_ATTACH_TO,
                "type": 1,
                "minCount": 1,
                "maxCount": 1,
                "effect": card(834),
                "option": [
                    {"type": OPT_CARD, "area": AREA_ACTIVE, "index": 0, "playerIndex": 0},
                    {"type": OPT_CARD, "area": AREA_BENCH, "index": 1, "playerIndex": 0},
                ],
            },
        }
        self.assertEqual(agent(obs), [0])


def obs_main(p0, options, p1=None):
    return {"current": current(p0=p0, p1=p1), "logs": [], "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": options}}


if __name__ == "__main__":
    unittest.main()
