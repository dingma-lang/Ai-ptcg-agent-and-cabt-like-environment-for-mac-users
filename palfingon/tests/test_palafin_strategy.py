from __future__ import annotations

import unittest

from agent import agent
from card_db import get_db
from core.palafin_planner import (
    attached_energy_count_any,
    score_ability_option,
    score_air_balloon_play_or_attach,
    score_attach_target,
    score_discard_selection,
    score_energy_attachment,
    score_poffin_target,
    score_pokepad_target,
    score_recovery_play,
    score_secret_box_target,
    secret_box_discard_safety,
)
from policy import MomentType, classify_all_options, current_turn_player_index, debug_scores, identify_moment_type, parse_select, parse_state
from state_eval import AREA_ACTIVE, AREA_BENCH, AREA_DECK, CTX_ATTACH_TO, CTX_IS_FIRST, CTX_MAIN, CTX_DISCARD, CTX_TO_BENCH, CTX_TO_HAND, OPT_ABILITY, OPT_ATTACH, OPT_ATTACK, OPT_CARD, OPT_END, OPT_EVOLVE, OPT_NO, OPT_PLAY, OPT_RETREAT, OPT_YES, normalize_state


FINIZEN = 105
PALAFIN = 106
PALAFIN_EX = 107
TATSUGIRI = 122
DRATINI = 902
DRAGONAIR = 903
MEGA_DRAGONITE_EX = 904
WATER = 3
LIGHTNING = 4
POFFIN = 1086
POKE_PAD = 1152
SECRET_BOX = 1092
SACRED_ASH = 1129
AIR_BALLOON = 1174
SURFING_BEACH = 1262
PETREL = 1219
HILDA = 1225
LILLIE = 1227


def card(cid, player=0):
    return {"id": cid, "cardId": cid, "playerIndex": player}


def pokemon(cid, energies=None, player=0):
    info = get_db().get_card(cid)
    max_hp = info.hp if info else 100
    return {
        "id": cid,
        "cardId": cid,
        "serial": cid,
        "playerIndex": player,
        "hp": max_hp,
        "maxHp": max_hp,
        "appearThisTurn": False,
        "energyCards": [card(eid, player=player) for eid in (energies or [])],
        "energies": [],
        "tools": [],
        "preEvolution": [],
    }


def player(active, bench=None, hand=None, discard=None, player_index=0):
    return {
        "active": [active] if active else [],
        "bench": bench or [],
        "benchMax": 5,
        "deckCount": 40,
        "handCount": len(hand or []),
        "hand": hand or [],
        "discard": discard or [],
        "prize": [None] * 6,
    }


def obs_for(active, bench=None, hand=None, options=None, select_extra=None):
    select = {"context": CTX_MAIN, "type": 0, "minCount": 1, "maxCount": 1, "option": options or []}
    if select_extra:
        select.update(select_extra)
    return {
        "logs": [],
        "current": {
            "turn": 3,
            "turnActionCount": 0,
            "yourIndex": 0,
            "firstPlayer": 0,
            "supporterPlayed": False,
            "stadiumPlayed": False,
            "energyAttached": False,
            "retreated": False,
            "stadium": [],
            "players": [
                player(active, bench=bench, hand=hand),
                player(pokemon(FINIZEN, player=1), player_index=1),
            ],
        },
        "select": select,
    }


class PalafinStrategyTests(unittest.TestCase):
    def test_opening_poffin_is_chosen_when_bench_has_room(self):
        obs = obs_for(
            pokemon(FINIZEN),
            bench=[],
            hand=[card(POFFIN)],
            options=[
                {"type": OPT_PLAY, "cardId": POFFIN},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [0])

    def test_poffin_still_used_with_bench_room_after_first_palafin_line(self):
        obs = obs_for(
            pokemon(PALAFIN_EX, energies=[WATER]),
            bench=[pokemon(FINIZEN), pokemon(TATSUGIRI)],
            hand=[card(POFFIN)],
            options=[
                {"type": OPT_PLAY, "cardId": POFFIN},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [0])

    def test_active_tatsugiri_uses_attract_customers_before_lillie_or_energy(self):
        obs = obs_for(
            pokemon(TATSUGIRI, energies=[WATER, LIGHTNING]),
            bench=[],
            hand=[card(PALAFIN_EX), card(PALAFIN_EX), card(DRAGONAIR), card(LILLIE), card(LIGHTNING), card(WATER)],
            options=[
                {"type": OPT_ATTACK, "attackId": 12201},
                {"type": OPT_ATTACK, "attackId": 12202},
                {"type": OPT_PLAY, "area": 2, "index": 3, "playerIndex": 0, "cardId": LILLIE},
                {"type": OPT_ATTACH, "area": 2, "index": 4, "playerIndex": 0, "cardId": LIGHTNING, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
                {"type": OPT_ATTACH, "area": 2, "index": 5, "playerIndex": 0, "cardId": WATER, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [0])

    def test_already_powered_tatsugiri_does_not_take_extra_manual_energy(self):
        obs = obs_for(
            pokemon(TATSUGIRI, energies=[WATER, LIGHTNING]),
            bench=[],
            hand=[card(LIGHTNING), card(WATER)],
            options=[
                {"type": OPT_ATTACH, "area": 2, "index": 0, "playerIndex": 0, "cardId": LIGHTNING, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
                {"type": OPT_ATTACH, "area": 2, "index": 1, "playerIndex": 0, "cardId": WATER, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [2])

    def test_empty_bench_uses_poffin_before_lillie(self):
        obs = obs_for(
            pokemon(TATSUGIRI),
            bench=[],
            hand=[card(POFFIN), card(LILLIE)],
            options=[
                {"type": OPT_PLAY, "area": 2, "index": 0, "playerIndex": 0, "cardId": POFFIN},
                {"type": OPT_PLAY, "area": 2, "index": 1, "playerIndex": 0, "cardId": LILLIE},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [0])

    def test_empty_bench_dead_hand_uses_lillie_when_poffin_unavailable(self):
        obs = obs_for(
            pokemon(TATSUGIRI, energies=[WATER, LIGHTNING]),
            bench=[],
            hand=[card(PALAFIN_EX), card(PALAFIN_EX), card(DRAGONAIR), card(LILLIE), card(LIGHTNING), card(WATER)],
            options=[
                {"type": OPT_PLAY, "area": 2, "index": 3, "playerIndex": 0, "cardId": LILLIE},
                {"type": OPT_ATTACH, "area": 2, "index": 4, "playerIndex": 0, "cardId": LIGHTNING, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
                {"type": OPT_ATTACH, "area": 2, "index": 5, "playerIndex": 0, "cardId": WATER, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [0])

    def test_nearly_empty_bench_dead_hand_uses_lillie_when_no_basic_or_poffin(self):
        obs = obs_for(
            pokemon(TATSUGIRI),
            bench=[pokemon(PALAFIN_EX, energies=[WATER])],
            hand=[card(PALAFIN_EX), card(DRAGONAIR), card(LILLIE)],
            options=[
                {"type": OPT_PLAY, "area": 2, "index": 2, "playerIndex": 0, "cardId": LILLIE},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [0])

    def test_basic_in_hand_is_benched_before_lillie_or_end(self):
        obs = obs_for(
            pokemon(TATSUGIRI),
            bench=[],
            hand=[card(FINIZEN), card(LILLIE)],
            options=[
                {"type": OPT_PLAY, "area": 2, "index": 0, "playerIndex": 0, "cardId": FINIZEN},
                {"type": OPT_PLAY, "area": 2, "index": 1, "playerIndex": 0, "cardId": LILLIE},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [0])

    def test_basic_in_hand_is_benched_before_tatsugiri_ability(self):
        obs = obs_for(
            pokemon(TATSUGIRI),
            bench=[],
            hand=[card(FINIZEN), card(LILLIE)],
            options=[
                {"type": OPT_ATTACK, "attackId": 12201},
                {"type": OPT_PLAY, "area": 2, "index": 0, "playerIndex": 0, "cardId": FINIZEN},
                {"type": OPT_PLAY, "area": 2, "index": 1, "playerIndex": 0, "cardId": LILLIE},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [1])

    def test_poffin_targets_finizen_not_dratini_because_dratini_has_80_hp(self):
        state = normalize_state(obs_for(pokemon(FINIZEN), bench=[], hand=[]))
        self.assertGreater(score_poffin_target(state, FINIZEN, "Finizen"), 6000)
        self.assertLess(score_poffin_target(state, DRATINI, "Dratini"), -9000)

    def test_poffin_prompt_takes_finizen_tatsugiri_not_dratini(self):
        obs = obs_for(
            pokemon(FINIZEN),
            bench=[],
            hand=[],
            options=[
                {"type": OPT_CARD, "area": AREA_DECK, "index": 0, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_DECK, "index": 1, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_DECK, "index": 2, "playerIndex": 0},
            ],
            select_extra={
                "context": CTX_TO_BENCH,
                "effect": card(POFFIN),
                "deck": [card(DRATINI), card(FINIZEN), card(TATSUGIRI)],
                "minCount": 0,
                "maxCount": 2,
            },
        )
        self.assertEqual(set(agent(obs)), {1, 2})

    def test_pokepad_gets_palafin_or_dratini_for_missing_dragonite_line(self):
        state = normalize_state(obs_for(pokemon(FINIZEN), bench=[], hand=[]))
        self.assertGreater(score_pokepad_target(state, PALAFIN, "Palafin"), 6000)
        self.assertGreater(score_pokepad_target(state, DRATINI, "Dratini"), 5000)
        self.assertLess(score_pokepad_target(state, PALAFIN_EX, "Palafin ex"), -5000)

    def test_pokepad_is_used_to_get_dratini_when_dragonite_basic_absent(self):
        play_obs = obs_for(
            pokemon(FINIZEN),
            bench=[pokemon(FINIZEN)],
            hand=[card(POKE_PAD)],
            options=[
                {"type": OPT_PLAY, "cardId": POKE_PAD},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(play_obs), [0])

        search_obs = obs_for(
            pokemon(FINIZEN),
            bench=[pokemon(FINIZEN)],
            hand=[],
            options=[
                {"type": OPT_CARD, "area": AREA_DECK, "index": 0, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_DECK, "index": 1, "playerIndex": 0},
            ],
            select_extra={
                "context": CTX_TO_HAND,
                "effect": card(POKE_PAD),
                "deck": [card(PALAFIN), card(DRATINI)],
                "minCount": 1,
                "maxCount": 1,
            },
        )
        self.assertEqual(agent(search_obs), [0])

    def test_use_lillie_for_empty_hand_before_ordinary_attack(self):
        obs = obs_for(
            pokemon(PALAFIN_EX, energies=[WATER]),
            bench=[pokemon(DRATINI)],
            hand=[card(LILLIE)],
            options=[
                {"type": OPT_ATTACK, "attackId": 10702},
                {"type": OPT_PLAY, "cardId": LILLIE},
                {"type": OPT_END},
            ],
        )
        obs["current"]["players"][1] = player(pokemon(PALAFIN_EX, player=1), player_index=1)
        self.assertEqual(agent(obs), [1])

    def test_evolution_is_checked_before_non_ko_attack_or_end(self):
        obs = obs_for(
            pokemon(FINIZEN),
            bench=[pokemon(DRATINI)],
            hand=[card(PALAFIN)],
            options=[
                {"type": OPT_ATTACK, "attackId": 10501},
                {"type": OPT_EVOLVE, "cardId": PALAFIN, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
                {"type": OPT_END},
            ],
        )
        obs["current"]["players"][1] = player(pokemon(PALAFIN_EX, player=1), player_index=1)
        self.assertEqual(agent(obs), [1])

    def test_use_productive_dragonair_energy_before_attack(self):
        obs = obs_for(
            pokemon(PALAFIN_EX, energies=[WATER]),
            bench=[pokemon(DRAGONAIR)],
            hand=[card(LIGHTNING)],
            options=[
                {"type": OPT_ATTACK, "attackId": 10702},
                {"type": OPT_ATTACH, "cardId": LIGHTNING, "inPlayArea": AREA_BENCH, "inPlayIndex": 0},
                {"type": OPT_END},
            ],
        )
        obs["current"]["players"][1] = player(pokemon(PALAFIN_EX, player=1), player_index=1)
        self.assertEqual(agent(obs), [1])

    def test_recheck_lillie_after_item_resolution_before_attack(self):
        obs = obs_for(
            pokemon(PALAFIN_EX, energies=[WATER]),
            bench=[pokemon(FINIZEN), pokemon(DRATINI)],
            hand=[card(LILLIE)],
            options=[
                {"type": OPT_ATTACK, "attackId": 10702},
                {"type": OPT_PLAY, "cardId": LILLIE},
                {"type": OPT_END},
            ],
        )
        obs["current"]["players"][1] = player(pokemon(PALAFIN_EX, player=1), player_index=1)
        self.assertEqual(agent(obs), [1])

    def test_ordinary_ko_does_not_skip_productive_supporter(self):
        obs = obs_for(
            pokemon(PALAFIN_EX, energies=[WATER]),
            bench=[pokemon(DRATINI)],
            hand=[card(LILLIE)],
            options=[
                {"type": OPT_ATTACK, "attackId": 10702},
                {"type": OPT_PLAY, "cardId": LILLIE},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [1])

    def test_poffin_setup_before_ordinary_attack(self):
        obs = obs_for(
            pokemon(PALAFIN_EX, energies=[WATER]),
            bench=[pokemon(FINIZEN), pokemon(DRATINI)],
            hand=[card(POFFIN)],
            options=[
                {"type": OPT_ATTACK, "attackId": 10702},
                {"type": OPT_PLAY, "cardId": POFFIN},
                {"type": OPT_END},
            ],
        )
        obs["current"]["players"][1] = player(pokemon(PALAFIN_EX, player=1), player_index=1)
        self.assertEqual(agent(obs), [1])

    def test_productive_pokepad_setup_before_ordinary_attack(self):
        obs = obs_for(
            pokemon(PALAFIN_EX, energies=[WATER]),
            bench=[pokemon(FINIZEN)],
            hand=[card(POKE_PAD)],
            options=[
                {"type": OPT_ATTACK, "attackId": 10702},
                {"type": OPT_PLAY, "cardId": POKE_PAD},
                {"type": OPT_END},
            ],
        )
        obs["current"]["players"][1] = player(pokemon(PALAFIN_EX, player=1), player_index=1)
        self.assertEqual(agent(obs), [1])

    def test_palafin_ex_energy_is_capped_at_one(self):
        state = normalize_state(obs_for(pokemon(PALAFIN_EX), bench=[], hand=[]))
        fresh = pokemon(PALAFIN_EX)
        powered = pokemon(PALAFIN_EX, energies=[WATER])
        self.assertGreater(score_energy_attachment(state, WATER, fresh), 6000)
        self.assertLess(score_energy_attachment(state, WATER, powered), -90000)
        self.assertLess(score_energy_attachment(state, LIGHTNING, fresh), -6000)

    def test_palafin_ex_energy_cap_counts_attached_cards_shape(self):
        target = pokemon(PALAFIN_EX)
        target.pop("energyCards", None)
        target["attachedCards"] = [card(WATER)]
        state = normalize_state(obs_for(pokemon(FINIZEN), bench=[target], hand=[]))
        self.assertEqual(attached_energy_count_any(target), 1)
        self.assertLess(score_energy_attachment(state, WATER, target), -90000)

    def test_manual_attach_avoids_second_energy_on_palafin_ex(self):
        obs = obs_for(
            pokemon(PALAFIN_EX, energies=[WATER]),
            bench=[],
            hand=[card(WATER)],
            options=[
                {"type": OPT_ATTACH, "cardId": WATER, "area": 2, "index": 0, "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [1])

    def test_active_tatsugiri_does_not_get_retreat_energy_when_palafin_ex_ready(self):
        obs = obs_for(
            pokemon(TATSUGIRI),
            bench=[pokemon(PALAFIN_EX, energies=[WATER])],
            hand=[card(WATER)],
            options=[
                {"type": OPT_ATTACH, "cardId": WATER, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0, "playerIndex": 0},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [1])

    def test_active_tatsugiri_prefers_air_balloon_over_retreat_energy(self):
        obs = obs_for(
            pokemon(TATSUGIRI),
            bench=[pokemon(PALAFIN_EX, energies=[WATER])],
            hand=[card(WATER), card(AIR_BALLOON)],
            options=[
                {"type": OPT_ATTACH, "cardId": WATER, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0, "playerIndex": 0},
                {"type": OPT_ATTACH, "cardId": AIR_BALLOON, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0, "playerIndex": 0},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [1])

    def test_crispin_attach_target_avoids_powered_palafin_ex(self):
        obs = obs_for(
            pokemon(PALAFIN_EX, energies=[WATER]),
            bench=[pokemon(DRAGONAIR)],
            options=[
                {"type": OPT_CARD, "area": AREA_ACTIVE, "index": 0, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_BENCH, "index": 0, "playerIndex": 0},
            ],
            select_extra={"context": CTX_ATTACH_TO, "sourceCardId": 1198},
        )
        state = normalize_state(obs)
        self.assertLess(score_attach_target(state, pokemon(PALAFIN_EX, energies=[WATER]), "Crispin"), -90000)
        self.assertEqual(agent(obs), [1])

    def test_lightning_is_reserved_for_dragonite_line(self):
        state = normalize_state(obs_for(pokemon(FINIZEN), bench=[pokemon(DRATINI)], hand=[]))
        self.assertGreater(score_energy_attachment(state, LIGHTNING, pokemon(DRATINI)), 5000)
        self.assertLess(score_energy_attachment(state, LIGHTNING, pokemon(PALAFIN_EX)), -6000)
        self.assertLess(score_energy_attachment(state, LIGHTNING, pokemon(TATSUGIRI)), -6000)

    def test_lightning_is_hard_blocked_on_palafin_evolution_chain(self):
        state = normalize_state(obs_for(pokemon(FINIZEN), bench=[pokemon(PALAFIN)], hand=[]))
        self.assertLess(score_energy_attachment(state, LIGHTNING, pokemon(FINIZEN)), -90000)
        self.assertLess(score_energy_attachment(state, LIGHTNING, pokemon(PALAFIN)), -90000)
        self.assertLess(score_energy_attachment(state, LIGHTNING, pokemon(PALAFIN_EX)), -90000)

    def test_agent_does_not_attach_lightning_to_finizen(self):
        obs = obs_for(
            pokemon(FINIZEN),
            bench=[pokemon(DRATINI)],
            hand=[card(LIGHTNING)],
            options=[
                {"type": OPT_ATTACH, "cardId": LIGHTNING, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0, "playerIndex": 0},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [1])

    def test_lillie_waits_for_useful_energy_attachment(self):
        obs = obs_for(
            pokemon(PALAFIN_EX, energies=[WATER]),
            bench=[pokemon(DRAGONAIR)],
            hand=[card(LILLIE), card(LIGHTNING)],
            options=[
                {"type": OPT_PLAY, "cardId": LILLIE},
                {"type": OPT_ATTACH, "cardId": LIGHTNING, "inPlayArea": AREA_BENCH, "inPlayIndex": 0, "playerIndex": 0},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [1])

    def test_retreat_with_energy_discard_is_held_when_not_urgent(self):
        obs = obs_for(
            pokemon(PALAFIN, energies=[WATER]),
            bench=[pokemon(FINIZEN)],
            hand=[],
            options=[
                {"type": OPT_RETREAT},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [1])

    def test_tatsugiri_does_not_retreat_with_energy_when_palafin_ex_is_ready(self):
        obs = obs_for(
            pokemon(TATSUGIRI, energies=[WATER]),
            bench=[pokemon(PALAFIN_EX, energies=[WATER])],
            hand=[],
            options=[
                {"type": OPT_RETREAT},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [1])

    def test_air_balloon_targets_palafin_or_tatsugiri(self):
        option_palafin = {"type": OPT_ATTACH, "cardId": AIR_BALLOON, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0}
        state = normalize_state(obs_for(pokemon(PALAFIN), bench=[pokemon(FINIZEN)], hand=[card(AIR_BALLOON)], options=[option_palafin]))
        self.assertGreater(score_air_balloon_play_or_attach(state, option_palafin), 6000)

        option_tatsu = {"type": OPT_ATTACH, "cardId": AIR_BALLOON, "inPlayArea": AREA_BENCH, "inPlayIndex": 0}
        state = normalize_state(obs_for(pokemon(FINIZEN), bench=[pokemon(TATSUGIRI)], hand=[card(AIR_BALLOON)], options=[option_tatsu]))
        self.assertGreater(score_air_balloon_play_or_attach(state, option_tatsu), 1000)

        option_dratini = {"type": OPT_ATTACH, "cardId": AIR_BALLOON, "inPlayArea": AREA_BENCH, "inPlayIndex": 0}
        state = normalize_state(obs_for(pokemon(FINIZEN), bench=[pokemon(DRATINI)], hand=[card(AIR_BALLOON)], options=[option_dratini]))
        self.assertLess(score_air_balloon_play_or_attach(state, option_dratini), 0)

    def test_secret_box_package_targets_combo_cards(self):
        state = normalize_state(obs_for(pokemon(FINIZEN), bench=[pokemon(FINIZEN)], hand=[card(SECRET_BOX)]))
        self.assertGreater(score_secret_box_target(state, "Poke Pad"), 7000)
        self.assertGreater(score_secret_box_target(state, "Air Balloon"), 4000)
        self.assertGreater(score_secret_box_target(state, "Surfing Beach"), 7000)

    def test_petrel_gets_secret_box_when_package_can_cover_multiple_pieces(self):
        obs = obs_for(
            pokemon(FINIZEN),
            bench=[],
            hand=[card(PETREL), card(LILLIE), card(PETREL), card(PETREL), card(AIR_BALLOON)],
            options=[
                {"type": OPT_CARD, "area": AREA_DECK, "index": 0, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_DECK, "index": 1, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_DECK, "index": 2, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_DECK, "index": 3, "playerIndex": 0},
            ],
            select_extra={
                "context": CTX_TO_HAND,
                "effect": card(PETREL),
                "deck": [card(POFFIN), card(POKE_PAD), card(SURFING_BEACH), card(SECRET_BOX)],
                "minCount": 1,
                "maxCount": 1,
            },
        )
        obs["current"]["supporterPlayed"] = True
        self.assertEqual(agent(obs), [3])

    def test_petrel_avoids_secret_box_when_discard_is_unsafe(self):
        obs = obs_for(
            pokemon(FINIZEN),
            bench=[],
            hand=[card(PALAFIN_EX), card(MEGA_DRAGONITE_EX), card(LIGHTNING)],
            options=[
                {"type": OPT_CARD, "area": AREA_DECK, "index": 0, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_DECK, "index": 1, "playerIndex": 0},
            ],
            select_extra={
                "context": CTX_TO_HAND,
                "effect": card(PETREL),
                "deck": [card(POKE_PAD), card(SECRET_BOX)],
                "minCount": 1,
                "maxCount": 1,
            },
        )
        obs["current"]["supporterPlayed"] = True
        self.assertEqual(agent(obs), [0])

    def test_petrel_gets_pokepad_when_it_leads_to_palafin_evolution(self):
        obs = obs_for(
            pokemon(FINIZEN),
            bench=[pokemon(TATSUGIRI)],
            hand=[card(PETREL), card(PALAFIN_EX), card(MEGA_DRAGONITE_EX), card(LIGHTNING)],
            options=[
                {"type": OPT_CARD, "area": AREA_DECK, "index": 0, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_DECK, "index": 1, "playerIndex": 0},
            ],
            select_extra={
                "context": CTX_TO_HAND,
                "effect": card(PETREL),
                "deck": [card(SURFING_BEACH), card(POKE_PAD)],
                "minCount": 1,
                "maxCount": 1,
            },
        )
        obs["current"]["supporterPlayed"] = True
        self.assertEqual(agent(obs), [1])

    def test_petrel_play_is_valued_when_secret_box_package_is_needed(self):
        obs = obs_for(
            pokemon(FINIZEN),
            bench=[],
            hand=[card(PETREL), card(AIR_BALLOON), card(AIR_BALLOON), card(AIR_BALLOON), card(LILLIE)],
            options=[
                {"type": OPT_PLAY, "cardId": PETREL},
                {"type": OPT_PLAY, "cardId": LILLIE},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [0])

    def test_secret_box_cannot_assume_removed_mass_recovery(self):
        obs = obs_for(
            pokemon(FINIZEN),
            bench=[pokemon(FINIZEN)],
            hand=[card(SECRET_BOX), card(PALAFIN_EX), card(PALAFIN_EX), card(MEGA_DRAGONITE_EX), card(1097)],
            select_extra={"context": CTX_DISCARD, "sourceCardId": SECRET_BOX},
        )
        state = normalize_state(obs)
        self.assertLess(secret_box_discard_safety(state), 0)

    def test_tatsugiri_ability_before_supporter(self):
        obs = obs_for(
            pokemon(TATSUGIRI),
            bench=[pokemon(FINIZEN)],
            hand=[card(LILLIE)],
            options=[
                {"type": OPT_ABILITY, "cardId": TATSUGIRI},
                {"type": OPT_PLAY, "cardId": LILLIE},
            ],
        )
        state = normalize_state(obs)
        self.assertGreater(score_ability_option(state, obs["select"]["option"][0], "Tatsugiri", TATSUGIRI), 7000)
        self.assertEqual(agent(obs), [0])

    def test_dragonair_ability_with_energy_before_supporter_or_end(self):
        obs = obs_for(
            pokemon(FINIZEN),
            bench=[pokemon(DRAGONAIR, energies=[LIGHTNING])],
            hand=[card(LILLIE)],
            options=[
                {"type": OPT_ABILITY, "cardId": DRAGONAIR},
                {"type": OPT_PLAY, "cardId": LILLIE},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [0])

    def test_dragonair_ability_without_energy_is_not_prioritized(self):
        obs = obs_for(
            pokemon(FINIZEN),
            bench=[pokemon(DRAGONAIR)],
            hand=[],
            options=[
                {"type": OPT_ABILITY, "cardId": DRAGONAIR},
                {"type": OPT_END},
            ],
        )
        self.assertEqual(agent(obs), [1])

    def test_dragonair_search_gets_palafin_not_palafin_ex(self):
        obs = obs_for(
            pokemon(FINIZEN),
            bench=[pokemon(DRAGONAIR, energies=[LIGHTNING])],
            hand=[card(MEGA_DRAGONITE_EX)],
            options=[
                {"type": OPT_CARD, "area": AREA_DECK, "index": 0, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_DECK, "index": 1, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_DECK, "index": 2, "playerIndex": 0},
            ],
            select_extra={
                "context": CTX_TO_HAND,
                "effect": card(DRAGONAIR),
                "deck": [card(PALAFIN_EX), card(PALAFIN), card(MEGA_DRAGONITE_EX)],
                "minCount": 1,
                "maxCount": 1,
            },
        )
        self.assertEqual(agent(obs), [1])

    def test_dragonair_search_gets_mega_dragonite_when_missing(self):
        obs = obs_for(
            pokemon(TATSUGIRI),
            bench=[pokemon(DRAGONAIR, energies=[LIGHTNING])],
            hand=[],
            options=[
                {"type": OPT_CARD, "area": AREA_DECK, "index": 0, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_DECK, "index": 1, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_DECK, "index": 2, "playerIndex": 0},
            ],
            select_extra={
                "context": CTX_TO_HAND,
                "effect": card(DRAGONAIR),
                "deck": [card(PALAFIN), card(PALAFIN_EX), card(MEGA_DRAGONITE_EX)],
                "minCount": 1,
                "maxCount": 1,
            },
        )
        self.assertEqual(agent(obs), [2])

    def test_tatsugiri_search_takes_useful_supporter(self):
        obs = obs_for(
            pokemon(TATSUGIRI),
            bench=[pokemon(FINIZEN)],
            hand=[],
            options=[
                {"type": OPT_CARD, "area": AREA_DECK, "index": 0, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_DECK, "index": 1, "playerIndex": 0},
                {"type": OPT_CARD, "area": AREA_DECK, "index": 2, "playerIndex": 0},
            ],
            select_extra={
                "context": CTX_TO_HAND,
                "effect": card(TATSUGIRI),
                "deck": [card(1182), card(LILLIE), card(PETREL)],
                "minCount": 1,
                "maxCount": 1,
            },
        )
        self.assertEqual(agent(obs), [1])

    def test_palaking_prefers_going_first_after_log_review(self):
        obs = obs_for(
            pokemon(FINIZEN),
            bench=[],
            options=[{"type": OPT_YES}, {"type": OPT_NO}],
            select_extra={"context": CTX_IS_FIRST},
        )
        self.assertEqual(agent(obs), [0])

    def test_end_turn_loses_to_useful_poffin_score(self):
        obs = obs_for(
            pokemon(FINIZEN),
            bench=[],
            hand=[card(POFFIN)],
            options=[
                {"type": OPT_END},
                {"type": OPT_PLAY, "cardId": POFFIN},
            ],
        )
        choice, rows = debug_scores(obs)
        self.assertEqual(choice, [1], rows)

    def test_main_action_window_overrides_turn_parity_confusion(self):
        obs = obs_for(
            pokemon(FINIZEN),
            bench=[],
            hand=[card(LILLIE)],
            options=[
                {"type": OPT_PLAY, "cardId": LILLIE},
                {"type": OPT_END},
            ],
        )
        obs["current"]["firstPlayer"] = 1
        obs["current"]["turn"] = 1
        state = parse_state(obs)
        select = parse_select(obs)
        options = classify_all_options(state, select)
        self.assertEqual(current_turn_player_index(state), 1)
        self.assertEqual(identify_moment_type(state, select, options), MomentType.OUR_MAIN_TURN)
        self.assertEqual(agent(obs), [0])

    def test_direct_current_player_field_overrides_turn_parity(self):
        obs = obs_for(
            pokemon(FINIZEN),
            bench=[],
            hand=[card(LILLIE)],
            options=[
                {"type": OPT_PLAY, "cardId": LILLIE},
                {"type": OPT_END},
            ],
        )
        obs["current"]["firstPlayer"] = 1
        obs["current"]["turn"] = 1
        obs["current"]["currentPlayer"] = 0
        state = parse_state(obs)
        self.assertEqual(current_turn_player_index(state), 0)


if __name__ == "__main__":
    unittest.main()
