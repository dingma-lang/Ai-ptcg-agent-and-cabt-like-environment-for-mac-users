from __future__ import annotations

import unittest

from agent import agent
from core.supporter_router import choose_best_supporter
from state_eval import AREA_ACTIVE, AREA_BENCH, AREA_DECK, AREA_HAND, CTX_ATTACH_TO, CTX_DISCARD, CTX_SETUP_ACTIVE, CTX_SWITCH, CTX_TO_ACTIVE, CTX_TO_HAND, OPT_ABILITY, OPT_ATTACH, OPT_ATTACK, OPT_CARD, OPT_END, OPT_PLAY, OPT_RETREAT, normalize_state
from tests.test_palafin_strategy import (
    AIR_BALLOON,
    DRAGONAIR,
    DRATINI,
    FINIZEN,
    HILDA,
    LIGHTNING,
    LILLIE,
    MEGA_DRAGONITE_EX,
    PALAFIN,
    PALAFIN_EX,
    PETREL,
    POFFIN,
    POKE_PAD,
    SECRET_BOX,
    TATSUGIRI,
    WATER,
    card,
    obs_for,
    pokemon,
)

BOSS = 1182
KIERAN = 1191
SWITCH = 1123


class PalakingLatestRulesTests(unittest.TestCase):
    def test_opening_setup_prefers_finizen_active_over_dratini(self):
        obs = obs_for(
            None,
            hand=[card(DRATINI), card(FINIZEN)],
            options=[
                {"type": OPT_CARD, "area": AREA_HAND, "index": 0, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_HAND, "index": 1, "playerIndex": 0},
            ],
            select_extra={"context": CTX_SETUP_ACTIVE},
        )
        self.assertEqual(agent(obs), [1])

    def test_unlocked_palafin_ex_does_not_switch_just_because_backup_exists(self):
        obs = obs_for(
            pokemon(PALAFIN_EX, energies=[WATER]),
            bench=[pokemon(PALAFIN_EX, energies=[WATER])],
            hand=[card(SWITCH)],
            options=[
                {"type": OPT_PLAY, "cardId": SWITCH},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [1])

    def test_locked_palafin_ex_can_switch_into_normal_palafin_recharge_line(self):
        active = pokemon(PALAFIN_EX, energies=[WATER])
        active["serial"] = "locked-palafin"
        obs = obs_for(
            active,
            bench=[pokemon(PALAFIN, energies=[WATER])],
            hand=[card(SWITCH)],
            options=[
                {"type": OPT_PLAY, "cardId": SWITCH},
                {"type": OPT_END},
            ],
        )
        obs["current"]["gigaImpactLockInstanceId"] = "locked-palafin"
        self.assertEqual(agent(obs), [0])

    def test_locked_palafin_ex_switch_target_prefers_air_balloon_tatsugiri_pivot(self):
        active = pokemon(PALAFIN_EX, energies=[WATER])
        active["serial"] = "locked-palafin"
        tatsugiri = pokemon(TATSUGIRI)
        tatsugiri["tools"] = [card(AIR_BALLOON)]
        obs = obs_for(
            active,
            bench=[pokemon(PALAFIN, energies=[WATER]), tatsugiri],
            hand=[],
            options=[
                {"type": OPT_CARD, "area": AREA_BENCH, "index": 0, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_BENCH, "index": 1, "playerIndex": 0},
            ],
            select_extra={"context": CTX_SWITCH, "sourceCardId": SWITCH},
        )
        obs["current"]["gigaImpactLockInstanceId"] = "locked-palafin"
        self.assertEqual(agent(obs), [1])

    def test_mega_dragonite_ex_never_pays_retreat_cost(self):
        obs = obs_for(
            pokemon(MEGA_DRAGONITE_EX, energies=[WATER, LIGHTNING]),
            bench=[pokemon(PALAFIN_EX, energies=[WATER])],
            hand=[],
            options=[
                {"type": OPT_RETREAT},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [1])

    def test_post_ko_promotes_finizen_when_no_attacker_is_ready(self):
        obs = obs_for(
            None,
            bench=[pokemon(DRATINI), pokemon(FINIZEN), pokemon(TATSUGIRI)],
            hand=[],
            options=[
                {"type": OPT_CARD, "area": AREA_BENCH, "index": 0, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_BENCH, "index": 1, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_BENCH, "index": 2, "playerIndex": 0},
            ],
            select_extra={"context": CTX_TO_ACTIVE},
        )
        self.assertEqual(agent(obs), [1])

    def test_active_tatsugiri_air_balloon_is_high_priority(self):
        obs = obs_for(
            pokemon(TATSUGIRI),
            bench=[pokemon(PALAFIN_EX, energies=[WATER])],
            hand=[card(AIR_BALLOON)],
            options=[
                {"type": OPT_ATTACH, "cardId": AIR_BALLOON, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [0])

    def test_dragonite_ability_waits_when_palafin_ex_can_giga_impact(self):
        obs = obs_for(
            pokemon(PALAFIN_EX, energies=[WATER]),
            bench=[pokemon(MEGA_DRAGONITE_EX)],
            hand=[],
            options=[
                {"type": OPT_ABILITY, "cardId": MEGA_DRAGONITE_EX, "inPlayArea": AREA_BENCH, "inPlayIndex": 0},
                {"type": OPT_ATTACK, "attackId": 10702},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [1])

    def test_dragonite_ability_high_when_locked_palafin_ex_has_tatsugiri_balloon(self):
        active = pokemon(PALAFIN_EX, energies=[WATER])
        active["serial"] = "locked-palafin"
        tatsugiri = pokemon(TATSUGIRI)
        tatsugiri["tools"] = [card(AIR_BALLOON)]
        obs = obs_for(
            active,
            bench=[tatsugiri, pokemon(MEGA_DRAGONITE_EX)],
            hand=[],
            options=[
                {"type": OPT_ABILITY, "cardId": MEGA_DRAGONITE_EX, "inPlayArea": AREA_BENCH, "inPlayIndex": 1},
                {"type": OPT_END},
            ],
        )
        obs["current"]["gigaImpactLockInstanceId"] = "locked-palafin"
        self.assertEqual(agent(obs), [0])

    def test_hilda_never_takes_palafin_ex_when_normal_palafin_is_available(self):
        obs = obs_for(
            pokemon(FINIZEN),
            hand=[],
            options=[
                {"type": OPT_CARD, "area": AREA_DECK, "index": 0, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_DECK, "index": 1, "playerIndex": 0},
            ],
            select_extra={
                "context": CTX_TO_HAND,
                "sourceCardId": HILDA,
                "deck": [card(PALAFIN_EX), card(PALAFIN)],
            },
        )
        self.assertEqual(agent(obs), [1])

    def test_hilda_gets_dragonair_not_palafin_ex_for_dragonite_chain(self):
        obs = obs_for(
            pokemon(DRATINI),
            hand=[],
            options=[
                {"type": OPT_CARD, "area": AREA_DECK, "index": 0, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_DECK, "index": 1, "playerIndex": 0},
            ],
            select_extra={
                "context": CTX_TO_HAND,
                "sourceCardId": HILDA,
                "deck": [card(PALAFIN_EX), card(DRAGONAIR)],
            },
        )
        self.assertEqual(agent(obs), [1])

    def test_hilda_gets_water_for_active_palafin_ex_without_energy(self):
        obs = obs_for(
            pokemon(PALAFIN_EX),
            bench=[pokemon(DRATINI)],
            hand=[],
            options=[
                {"type": OPT_CARD, "area": AREA_DECK, "index": 0, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_DECK, "index": 1, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_DECK, "index": 2, "playerIndex": 0},
            ],
            select_extra={
                "context": CTX_TO_HAND,
                "sourceCardId": HILDA,
                "deck": [card(PALAFIN_EX), card(WATER), card(LIGHTNING)],
            },
        )
        self.assertEqual(agent(obs), [1])

    def test_lightning_attach_target_prompt_never_chooses_palafin_ex(self):
        obs = obs_for(
            pokemon(PALAFIN_EX),
            bench=[pokemon(DRAGONAIR)],
            hand=[],
            options=[
                {"type": OPT_CARD, "area": 4, "index": 0, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_BENCH, "index": 0, "playerIndex": 0},
            ],
            select_extra={
                "context": CTX_ATTACH_TO,
                "sourceCardId": HILDA,
                "energyCardId": LIGHTNING,
            },
        )
        self.assertEqual(agent(obs), [1])

    def test_secret_box_discard_does_not_throw_away_poffin_when_bench_is_low(self):
        obs = obs_for(
            pokemon(FINIZEN),
            bench=[],
            hand=[card(SECRET_BOX), card(POFFIN), card(WATER), card(LILLIE)],
            options=[
                {"type": OPT_CARD, "area": AREA_HAND, "index": 1, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_HAND, "index": 2, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_HAND, "index": 3, "playerIndex": 0},
            ],
            select_extra={"context": CTX_DISCARD, "sourceCardId": SECRET_BOX, "minCount": 1, "maxCount": 1},
        )
        self.assertNotEqual(agent(obs), [0])

    def test_petrel_gets_poffin_when_bench_low_and_both_engines_started(self):
        obs = obs_for(
            pokemon(FINIZEN),
            bench=[pokemon(DRATINI)],
            hand=[],
            options=[
                {"type": OPT_CARD, "area": AREA_DECK, "index": 0, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_DECK, "index": 1, "playerIndex": 0},
            ],
            select_extra={
                "context": CTX_TO_HAND,
                "sourceCardId": PETREL,
                "deck": [card(POFFIN), card(POKE_PAD)],
            },
        )
        self.assertEqual(agent(obs), [0])

    def test_secret_box_low_hand_search_can_take_lillie(self):
        obs = obs_for(
            pokemon(FINIZEN),
            bench=[],
            hand=[card(SECRET_BOX), card(WATER), card(LIGHTNING)],
            options=[
                {"type": OPT_CARD, "area": AREA_DECK, "index": 0, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_DECK, "index": 1, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_DECK, "index": 2, "playerIndex": 0},
            ],
            select_extra={
                "context": CTX_TO_HAND,
                "sourceCardId": SECRET_BOX,
                "deck": [card(LILLIE), card(HILDA), card(POFFIN)],
            },
        )
        self.assertEqual(agent(obs), [0])

    def test_supporter_router_resolves_hand_index_options_not_raw_indices(self):
        obs = obs_for(
            pokemon(FINIZEN),
            hand=[card(LILLIE), card(HILDA), card(PALAFIN)],
            options=[
                {"type": OPT_PLAY, "area": AREA_HAND, "index": 0, "playerIndex": 0},
                {"type": OPT_PLAY, "area": AREA_HAND, "index": 1, "playerIndex": 0},
                {"type": OPT_END},
            ],
        )
        decision = choose_best_supporter(normalize_state(obs), obs["select"]["option"])
        self.assertEqual(decision.supporter_name, "Hilda")
        self.assertEqual(decision.option_index, 1)

    def test_boss_and_kieran_are_not_casual_supporters(self):
        obs = obs_for(
            pokemon(FINIZEN),
            bench=[pokemon(DRATINI)],
            hand=[card(BOSS), card(KIERAN)],
            options=[
                {"type": OPT_PLAY, "cardId": BOSS},
                {"type": OPT_PLAY, "cardId": KIERAN},
                {"type": OPT_END},
            ],
        )
        decision = choose_best_supporter(normalize_state(obs), obs["select"]["option"])
        self.assertFalse(decision.should_use)

    def test_mega_dragonite_reset_prefers_fresh_palafin_ex_over_tatsugiri_pivot(self):
        tatsugiri = pokemon(TATSUGIRI)
        tatsugiri["tools"] = [card(AIR_BALLOON)]
        active = pokemon(PALAFIN_EX, energies=[WATER])
        active["serial"] = "locked-palafin"
        obs = obs_for(
            active,
            bench=[tatsugiri, pokemon(PALAFIN_EX, energies=[WATER])],
            hand=[],
            options=[
                {"type": OPT_CARD, "area": AREA_BENCH, "index": 0, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_BENCH, "index": 1, "playerIndex": 0},
            ],
            select_extra={"context": CTX_SWITCH, "sourceCardId": MEGA_DRAGONITE_EX},
        )
        obs["current"]["gigaImpactLockInstanceId"] = "locked-palafin"
        self.assertEqual(agent(obs), [1])

    def test_pokepad_gets_dratini_not_dragonair_when_no_dratini_in_play(self):
        obs = obs_for(
            pokemon(PALAFIN_EX, energies=[WATER]),
            bench=[pokemon(TATSUGIRI)],
            hand=[],
            options=[
                {"type": OPT_CARD, "area": AREA_DECK, "index": 0, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_DECK, "index": 1, "playerIndex": 0},
            ],
            select_extra={
                "context": CTX_TO_HAND,
                "sourceCardId": POKE_PAD,
                "deck": [card(DRAGONAIR), card(DRATINI)],
            },
        )
        self.assertEqual(agent(obs), [1])

    def test_petrel_does_not_get_pokepad_for_dragonair_before_dratini_is_in_play(self):
        obs = obs_for(
            pokemon(PALAFIN_EX, energies=[WATER]),
            bench=[pokemon(TATSUGIRI)],
            hand=[card(DRATINI)],
            options=[
                {"type": OPT_CARD, "area": AREA_DECK, "index": 0, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_DECK, "index": 1, "playerIndex": 0},
            ],
            select_extra={
                "context": CTX_TO_HAND,
                "sourceCardId": PETREL,
                "deck": [card(POKE_PAD), card(POFFIN)],
            },
        )
        self.assertEqual(agent(obs), [1])

    def test_spare_water_goes_to_dragonite_line_after_palafin_ex_is_exactly_powered(self):
        obs = obs_for(
            pokemon(PALAFIN_EX, energies=[WATER]),
            bench=[pokemon(DRAGONAIR)],
            hand=[card(WATER)],
            options=[
                {"type": OPT_ATTACH, "cardId": WATER, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
                {"type": OPT_ATTACH, "cardId": WATER, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_BENCH, "inPlayIndex": 0},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [1])

    def test_dragonair_ability_is_used_before_lillie_when_energized(self):
        obs = obs_for(
            pokemon(FINIZEN),
            bench=[pokemon(DRAGONAIR, energies=[WATER])],
            hand=[card(LILLIE), card(PALAFIN_EX), card(PALAFIN_EX)],
            options=[
                {"type": OPT_ABILITY, "cardId": DRAGONAIR, "inPlayArea": AREA_BENCH, "inPlayIndex": 0},
                {"type": OPT_PLAY, "cardId": LILLIE, "area": AREA_HAND, "index": 0, "playerIndex": 0},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [0])

    def test_lillie_shuffles_duplicate_palafin_ex_back_before_zero_to_hero(self):
        obs = obs_for(
            pokemon(PALAFIN),
            bench=[pokemon(FINIZEN)],
            hand=[card(LILLIE), card(PALAFIN_EX), card(PALAFIN_EX)],
            options=[
                {"type": OPT_ABILITY, "cardId": PALAFIN},
                {"type": OPT_PLAY, "cardId": LILLIE, "area": AREA_HAND, "index": 0, "playerIndex": 0},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [1])

    def test_lillie_still_waits_for_useful_attachment_before_shuffling_palafin_ex(self):
        obs = obs_for(
            pokemon(PALAFIN),
            bench=[pokemon(DRAGONAIR)],
            hand=[card(LILLIE), card(PALAFIN_EX), card(PALAFIN_EX), card(WATER)],
            options=[
                {"type": OPT_ATTACH, "cardId": WATER, "area": AREA_HAND, "index": 3, "playerIndex": 0, "inPlayArea": AREA_BENCH, "inPlayIndex": 0},
                {"type": OPT_PLAY, "cardId": LILLIE, "area": AREA_HAND, "index": 0, "playerIndex": 0},
                {"type": OPT_ABILITY, "cardId": PALAFIN},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [0])

    def test_poffin_is_held_when_bench_is_developed_and_no_concrete_basic_needed(self):
        obs = obs_for(
            pokemon(PALAFIN_EX, energies=[WATER]),
            bench=[pokemon(FINIZEN), pokemon(PALAFIN_EX, energies=[WATER]), pokemon(TATSUGIRI), pokemon(DRATINI)],
            hand=[card(POFFIN)],
            options=[
                {"type": OPT_PLAY, "cardId": POFFIN},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [1])

    def test_sky_transport_preferred_over_switch_for_active_palafin_route(self):
        obs = obs_for(
            pokemon(PALAFIN),
            bench=[pokemon(FINIZEN), pokemon(MEGA_DRAGONITE_EX)],
            hand=[card(SWITCH)],
            options=[
                {"type": OPT_PLAY, "cardId": SWITCH},
                {"type": OPT_ABILITY, "cardId": MEGA_DRAGONITE_EX, "inPlayArea": AREA_BENCH, "inPlayIndex": 1},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [1])

    def test_zero_to_hero_waits_when_all_palafin_ex_are_visible_out_of_deck(self):
        obs = obs_for(
            pokemon(PALAFIN),
            bench=[pokemon(FINIZEN)],
            hand=[card(PALAFIN_EX), card(PALAFIN_EX), card(PALAFIN_EX), card(PALAFIN_EX)],
            options=[
                {"type": OPT_ABILITY, "cardId": PALAFIN},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [1])

    def test_giga_water_attach_shortcut_targets_active_palafin_ex_not_first_water_option(self):
        obs = obs_for(
            pokemon(PALAFIN_EX),
            bench=[pokemon(DRAGONAIR)],
            hand=[card(WATER)],
            options=[
                {"type": OPT_ATTACH, "cardId": WATER, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_BENCH, "inPlayIndex": 0},
                {"type": OPT_ATTACH, "cardId": WATER, "area": AREA_HAND, "index": 0, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [1])


if __name__ == "__main__":
    unittest.main()
