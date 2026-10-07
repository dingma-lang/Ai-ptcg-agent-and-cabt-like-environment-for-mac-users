from __future__ import annotations

import unittest

from agent import agent
from card_db import get_db
from core.mega_gengar_planner import score_mega_gengar_plan
from state_eval import AREA_ACTIVE, AREA_BENCH, AREA_DECK, AREA_HAND, CTX_ATTACH_TO, CTX_MAIN, CTX_TO_HAND, CTX_TO_HAND_ENERGY, OPT_ABILITY, OPT_ATTACH, OPT_ATTACK, OPT_CARD, OPT_END, OPT_EVOLVE, OPT_PLAY, normalize_state
from tests.test_round_plan import card, current, player, pokemon


class MegaGengarPlannerTests(unittest.TestCase):
    def test_haunter_evolves_into_mega_gengar(self):
        p0 = player(pokemon(771), hand=[card(772)])
        obs = obs_main(p0, [{"type": OPT_EVOLVE, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [0])

    def test_ultra_ball_searches_mega_gengar_when_haunter_ready(self):
        p0 = player(pokemon(771), hand=[])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_TO_HAND,
                "type": 1,
                "minCount": 1,
                "maxCount": 1,
                "effect": card(1121),
                "deck": [card(229), card(772)],
                "option": [{"type": OPT_CARD, "area": AREA_DECK, "index": 0, "playerIndex": 0}, {"type": OPT_CARD, "area": AREA_DECK, "index": 1, "playerIndex": 0}],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_darkness_attach_to_mega_gengar(self):
        p0 = player(pokemon(772, energies=[card(7)]), hand=[card(7)])
        obs = obs_main(p0, [{"type": OPT_ATTACH, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [0])

    def test_darkness_attach_prefers_gengar_line_over_toxtricity(self):
        p0 = player(pokemon(771), bench=[pokemon(834)], hand=[card(7)])
        obs = obs_main(
            p0,
            [
                {"type": OPT_ATTACH, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_BENCH, "inPlayIndex": 0},
                {"type": OPT_ATTACH, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
            ],
        )
        self.assertEqual(agent(obs), [1])

    def test_darkness_does_not_exceed_mega_gengar_attack_cost(self):
        p0 = player(pokemon(772, energies=[card(7), card(7)]), hand=[card(7)])
        obs = obs_main(p0, [{"type": OPT_ATTACH, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [1])

    def test_toxtricity_ability_for_mega_gengar(self):
        p0 = player(pokemon(834), bench=[pokemon(772)], hand=[])
        obs = obs_main(p0, [{"type": OPT_ABILITY, "area": AREA_ACTIVE, "index": 0, "playerIndex": 0}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [0])

    def test_crispin_powers_mega_gengar_attack_line(self):
        p0 = player(pokemon(772, energies=[card(7)]), hand=[card(1198), card(1227)])
        obs = obs_main(p0, [{"type": OPT_PLAY, "index": 0}, {"type": OPT_PLAY, "index": 1}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [0])

    def test_crispin_energy_prompt_prefers_darkness_for_mega_gengar(self):
        p0 = player(pokemon(772, energies=[card(7)]), hand=[])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_TO_HAND_ENERGY,
                "type": 1,
                "minCount": 1,
                "maxCount": 1,
                "effect": card(1198),
                "deck": [card(5), card(8), card(7)],
                "option": [{"type": OPT_CARD, "area": AREA_DECK, "index": idx, "playerIndex": 0} for idx in range(3)],
            },
        }
        self.assertEqual(agent(obs), [2])

    def test_void_gale_moves_energy_to_zweilous_before_hydreigon_is_out(self):
        p0 = player(pokemon(772, energies=[card(7), card(7)]), bench=[pokemon(227), pokemon(228)], hand=[])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_ATTACH_TO,
                "type": 1,
                "minCount": 1,
                "maxCount": 1,
                "effect": card(772),
                "option": [
                    {"type": OPT_CARD, "area": AREA_BENCH, "index": 0, "playerIndex": 0},
                    {"type": OPT_CARD, "area": AREA_BENCH, "index": 1, "playerIndex": 0},
                ],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_opponent_ex_heavy_increases_mega_gengar_value(self):
        p0 = player(pokemon(771), hand=[card(772)])
        ex_state = normalize_state(obs_main(p0, [], p1=player(pokemon(229, player=1), bench=[pokemon(140, player=1)], hand=None, player_index=1)))
        one_state = normalize_state(obs_main(p0, [], p1=player(pokemon(227, player=1), bench=[pokemon(59, player=1)], hand=None, player_index=1)))
        self.assertGreater(score_mega_gengar_plan(ex_state).score, score_mega_gengar_plan(one_state).score)

    def test_ultra_ball_prefers_mega_gengar_stage_two_against_ex_attacker(self):
        p0 = player(pokemon(771), bench=[pokemon(227)], hand=[card(1079)])
        p1 = player(pokemon(229, player=1), hand=None, player_index=1)
        obs = {
            "current": current(p0=p0, p1=p1),
            "logs": [],
            "select": {
                "context": CTX_TO_HAND,
                "type": 1,
                "minCount": 1,
                "maxCount": 1,
                "effect": card(1121),
                "deck": [card(229), card(772)],
                "option": [{"type": OPT_CARD, "area": AREA_DECK, "index": 0, "playerIndex": 0}, {"type": OPT_CARD, "area": AREA_DECK, "index": 1, "playerIndex": 0}],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_ultra_ball_chooses_live_mega_gengar_over_hydreigon_combo(self):
        p0 = player(pokemon(771), bench=[pokemon(227)], hand=[card(1079)])
        p1 = player(pokemon(229, player=1), hand=None, player_index=1)
        obs = {
            "current": current(p0=p0, p1=p1),
            "logs": [],
            "select": {
                "context": CTX_TO_HAND,
                "type": 1,
                "minCount": 1,
                "maxCount": 1,
                "effect": card(1121),
                "deck": [card(229), card(772)],
                "option": [{"type": OPT_CARD, "area": AREA_DECK, "index": 0, "playerIndex": 0}, {"type": OPT_CARD, "area": AREA_DECK, "index": 1, "playerIndex": 0}],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_dawn_chooses_live_mega_gengar_over_hydreigon_combo(self):
        p0 = player(pokemon(771), bench=[pokemon(227)], hand=[card(1079)])
        obs = {
            "current": current(p0=p0),
            "logs": [],
            "select": {
                "context": CTX_TO_HAND,
                "type": 1,
                "minCount": 1,
                "maxCount": 1,
                "effect": card(1231),
                "deck": [card(229), card(772)],
                "option": [{"type": OPT_CARD, "area": AREA_DECK, "index": 0, "playerIndex": 0}, {"type": OPT_CARD, "area": AREA_DECK, "index": 1, "playerIndex": 0}],
            },
        }
        self.assertEqual(agent(obs), [1])

    def test_hydreigon_incomplete_does_not_ignore_fast_mega_gengar(self):
        p0 = player(pokemon(771, energies=[card(7)]), hand=[card(7)])
        obs = obs_main(p0, [{"type": OPT_ATTACH, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [0])

    def test_crispin_supports_live_mega_gengar_line_with_deino_present(self):
        p0 = player(pokemon(771), bench=[pokemon(227)], hand=[card(1198)])
        obs = obs_main(p0, [{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [0])

    def test_mega_gengar_attacks_as_damage_dealer_before_pass(self):
        attacks = get_db().get_card(772).attacks
        void_gale = next(attack for attack in attacks if attack.name == "Void Gale")
        p0 = player(pokemon(772, energies=[card(7), card(7)]), hand=[])
        p1 = player(pokemon(229, hp=330, max_hp=330, player=1), hand=None, player_index=1)
        obs = obs_main(p0, [{"type": OPT_ATTACK, "attackId": void_gale.attack_id}, {"type": OPT_END}], p1=p1)
        self.assertEqual(agent(obs), [0])


def obs_main(p0, options, p1=None):
    return {"current": current(p0=p0, p1=p1), "logs": [], "select": {"context": CTX_MAIN, "type": 0, "minCount": 1 if options else 0, "maxCount": 1 if options else 0, "option": options}}


if __name__ == "__main__":
    unittest.main()
