from __future__ import annotations

import unittest

from agent import agent
from core.palafin_attack_state import track_giga_impact_lock
from state_eval import OPT_ATTACK, OPT_ATTACH, OPT_END, OPT_PLAY, normalize_state
from tests.test_palafin_strategy import (
    FINIZEN,
    PALAFIN_EX,
    SURFING_BEACH,
    WATER,
    card,
    obs_for,
    player,
    pokemon,
)

BOSS = 1182
KIERAN = 1191
SWITCH = 1123
GIGA_IMPACT = 10702


def with_opponent(obs, active, bench=None, prizes=6):
    obs["current"]["players"][1] = player(active, bench=bench or [], player_index=1)
    obs["current"]["players"][0]["prize"] = [None] * prizes
    return obs


class GigaImpactLogicTests(unittest.TestCase):
    def test_palafin_ex_uses_giga_impact_for_ko(self):
        obs = obs_for(
            pokemon(PALAFIN_EX, energies=[WATER]),
            options=[
                {"type": OPT_ATTACK, "attackId": GIGA_IMPACT},
                {"type": OPT_END},
            ],
        )
        with_opponent(obs, pokemon(FINIZEN, player=1))
        self.assertEqual(agent(obs), [0])

    def test_water_attachment_enables_giga_impact(self):
        obs = obs_for(
            pokemon(PALAFIN_EX),
            hand=[card(WATER)],
            options=[
                {"type": OPT_ATTACH, "cardId": WATER, "inPlayArea": 4, "inPlayIndex": 0},
                {"type": OPT_END},
            ],
        )
        with_opponent(obs, pokemon(FINIZEN, player=1))
        self.assertEqual(agent(obs), [0])

    def test_kieran_before_giga_impact_when_plus_30_creates_ko(self):
        opponent = pokemon(PALAFIN_EX, player=1)
        opponent["hp"] = 270
        obs = obs_for(
            pokemon(PALAFIN_EX, energies=[WATER]),
            hand=[card(KIERAN)],
            options=[
                {"type": OPT_PLAY, "cardId": KIERAN},
                {"type": OPT_ATTACK, "attackId": GIGA_IMPACT},
                {"type": OPT_END},
            ],
        )
        with_opponent(obs, opponent)
        self.assertEqual(agent(obs), [0])

    def test_boss_before_giga_impact_for_prize_route(self):
        opponent = pokemon(PALAFIN_EX, player=1)
        target = pokemon(FINIZEN, player=1)
        obs = obs_for(
            pokemon(PALAFIN_EX, energies=[WATER]),
            hand=[card(BOSS)],
            options=[
                {"type": OPT_PLAY, "cardId": BOSS},
                {"type": OPT_ATTACK, "attackId": GIGA_IMPACT},
                {"type": OPT_END},
            ],
        )
        with_opponent(obs, opponent, bench=[target])
        self.assertEqual(agent(obs), [0])

    def test_giga_lock_applies_only_to_same_instance(self):
        locked = pokemon(PALAFIN_EX, energies=[WATER])
        locked["serial"] = "locked-palafin"
        obs = obs_for(locked, options=[])
        obs["current"]["gigaImpactLockInstanceId"] = "locked-palafin"
        status = track_giga_impact_lock(normalize_state(obs), None)
        self.assertTrue(status.restriction_applies_now)
        self.assertFalse(status.can_attack_now)

        fresh = pokemon(PALAFIN_EX, energies=[WATER])
        fresh["serial"] = "fresh-palafin"
        obs = obs_for(fresh, options=[])
        obs["current"]["gigaImpactLockInstanceId"] = "locked-palafin"
        status = track_giga_impact_lock(normalize_state(obs), None)
        self.assertFalse(status.restriction_applies_now)
        self.assertTrue(status.can_attack_now)

    def test_locked_palafin_ex_uses_surfing_beach_reset(self):
        active = pokemon(PALAFIN_EX, energies=[WATER])
        active["serial"] = "locked-palafin"
        obs = obs_for(
            active,
            bench=[pokemon(PALAFIN_EX, energies=[WATER])],
            hand=[card(SURFING_BEACH)],
            options=[
                {"type": OPT_PLAY, "cardId": SURFING_BEACH},
                {"type": OPT_END},
            ],
        )
        obs["current"]["gigaImpactLockInstanceId"] = "locked-palafin"
        self.assertEqual(agent(obs), [0])

    def test_locked_palafin_ex_uses_switch_into_fresh_attacker(self):
        active = pokemon(PALAFIN_EX, energies=[WATER])
        active["serial"] = "locked-palafin"
        obs = obs_for(
            active,
            bench=[pokemon(PALAFIN_EX, energies=[WATER])],
            hand=[card(SWITCH)],
            options=[
                {"type": OPT_PLAY, "cardId": SWITCH},
                {"type": OPT_END},
            ],
        )
        obs["current"]["gigaImpactLockInstanceId"] = "locked-palafin"
        self.assertEqual(agent(obs), [0])

    def test_giga_impact_still_used_without_future_reset_if_it_kos(self):
        obs = obs_for(
            pokemon(PALAFIN_EX, energies=[WATER]),
            options=[
                {"type": OPT_ATTACK, "attackId": GIGA_IMPACT},
                {"type": OPT_END},
            ],
        )
        target = pokemon(PALAFIN_EX, player=1)
        target["hp"] = 200
        with_opponent(obs, target)
        self.assertEqual(agent(obs), [0])

    def test_lillie_prepares_before_ordinary_ko_but_pass_does_not(self):
        ko_obs = obs_for(
            pokemon(PALAFIN_EX, energies=[WATER]),
            hand=[card(1227)],
            options=[
                {"type": OPT_PLAY, "cardId": 1227},
                {"type": OPT_ATTACK, "attackId": GIGA_IMPACT},
                {"type": OPT_END},
            ],
        )
        with_opponent(ko_obs, pokemon(FINIZEN, player=1))
        self.assertEqual(agent(ko_obs), [0])

        pressure_obs = obs_for(
            pokemon(PALAFIN_EX, energies=[WATER]),
            options=[
                {"type": OPT_ATTACK, "attackId": GIGA_IMPACT},
                {"type": OPT_END},
            ],
        )
        with_opponent(pressure_obs, pokemon(PALAFIN_EX, player=1))
        self.assertEqual(agent(pressure_obs), [0])


if __name__ == "__main__":
    unittest.main()
