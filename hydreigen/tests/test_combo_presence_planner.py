from __future__ import annotations

import unittest

from agent import agent
from state_eval import AREA_DECK, CTX_DISCARD, CTX_MAIN, CTX_TO_HAND, OPT_CARD, OPT_END, OPT_PLAY
from tests.test_hydreigon_policy import card, current, player, pokemon


class ComboPresencePlannerTests(unittest.TestCase):
    def test_pokepad_before_lillie_for_deino_hydreigon_bridge(self):
        p0 = player(pokemon(227), hand=[card(1152), card(229), card(1227)])
        obs = obs_main(p0, [{"type": OPT_PLAY, "index": 0}, {"type": OPT_PLAY, "index": 2}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [0])

    def test_pokepad_search_gets_zweilous_for_hydreigon_bridge(self):
        p0 = player(pokemon(227), hand=[card(229)])
        obs = obs_search(
            p0,
            effect=card(1152),
            deck=[card(227), card(228), card(771)],
        )
        self.assertEqual(agent(obs), [1])

    def test_petrel_before_lillie_when_evolution_bridge_needed(self):
        p0 = player(pokemon(227), bench=[pokemon(59), pokemon(833), pokemon(140)], hand=[card(1219), card(229), card(1227)])
        obs = obs_main(p0, [{"type": OPT_PLAY, "index": 0}, {"type": OPT_PLAY, "index": 2}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [0])

    def test_petrel_search_gets_rare_candy_for_hydreigon_bridge(self):
        p0 = player(pokemon(227), hand=[card(229)])
        obs = obs_search(
            p0,
            effect=card(1219),
            deck=[card(1086), card(1079), card(1121), card(1092)],
        )
        self.assertEqual(agent(obs), [1])

    def test_secret_box_used_for_bridge_when_energy_recycler_covers_discards(self):
        p0 = player(pokemon(227), hand=[card(1092), card(229), card(1139), card(7), card(8), card(5)])
        obs = obs_main(p0, [{"type": OPT_PLAY, "index": 0}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [0])

    def test_secret_box_discard_prompt_chooses_energy_package_with_recycler(self):
        p0 = player(pokemon(227), hand=[card(1139), card(7), card(8), card(5), card(1086), card(1227)])
        obs = {
            "current": current(p0=p0, turn=5),
            "logs": [],
            "select": {
                "context": CTX_DISCARD,
                "type": 1,
                "minCount": 3,
                "maxCount": 3,
                "effect": card(1092),
                "option": [{"type": OPT_CARD, "area": 2, "index": idx, "playerIndex": 0} for idx in range(6)],
            },
        }
        self.assertEqual(set(agent(obs)), {1, 2, 3})

    def test_pokepad_before_lillie_for_gastly_gengar_bridge(self):
        p0 = player(pokemon(59), hand=[card(1152), card(772), card(1227)])
        obs = obs_main(p0, [{"type": OPT_PLAY, "index": 0}, {"type": OPT_PLAY, "index": 2}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [0])

    def test_pokepad_search_gets_haunter_for_gengar_bridge(self):
        p0 = player(pokemon(59), hand=[card(772)])
        obs = obs_search(
            p0,
            effect=card(1152),
            deck=[card(227), card(59), card(771)],
        )
        self.assertEqual(agent(obs), [2])


def obs_main(p0, options):
    return {
        "current": current(p0=p0, turn=5),
        "logs": [],
        "select": {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": options},
    }


def obs_search(p0, effect, deck):
    return {
        "current": current(p0=p0, turn=5),
        "logs": [],
        "select": {
            "context": CTX_TO_HAND,
            "type": 1,
            "minCount": 1,
            "maxCount": 1,
            "effect": effect,
            "deck": deck,
            "option": [{"type": OPT_CARD, "area": AREA_DECK, "index": idx, "playerIndex": 0} for idx in range(len(deck))],
        },
    }


if __name__ == "__main__":
    unittest.main()
