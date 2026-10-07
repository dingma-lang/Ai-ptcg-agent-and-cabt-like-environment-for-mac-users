from __future__ import annotations

import unittest

from agent import agent
from card_db import get_db
from core.air_balloon_planner import score_air_balloon_target
from core.expert_battle_planner import (
    attack_energy_ready, bench_balloon_pivot, finishing_action,
    gust_target_score, redundant_attacker_discard,
)
from core.giga_impact_planner import score_giga_impact_attack
from core.palafin_planner import score_discard_selection, score_secret_box_target
from core.turn_plan import MovementResources, movement_resources
from policy import estimate_attack_damage
from state_eval import (
    AREA_ACTIVE, AREA_BENCH, CTX_SWITCH, CTX_TO_HAND, OPT_ABILITY,
    OPT_ATTACH, OPT_ATTACK, OPT_CARD, OPT_END, OPT_PLAY, OPT_RETREAT, normalize_state,
)
from tests.test_palafin_strategy import card, obs_for, pokemon


def attach(cid, area=AREA_ACTIVE, index=0):
    return {"type": OPT_ATTACH, "cardId": cid, "inPlayArea": area, "inPlayIndex": index}


def target(index, owner=0):
    return {"type": OPT_CARD, "area": AREA_BENCH, "index": index, "playerIndex": owner}


def finisher_obs(energy=(4, 4, 3), opponent_id=107, hp=300):
    obs = obs_for(pokemon(107, [3]), bench=[pokemon(904, list(energy))], options=[
        {"type": OPT_ATTACK, "attackId": 134}, {"type": OPT_ABILITY, "cardId": 904},
        {"type": OPT_END}])
    obs["current"]["players"][0]["prize"] = [None] * 2
    defender = pokemon(opponent_id, player=1)
    defender["hp"] = hp
    obs["current"]["players"][1]["active"] = [defender]
    return obs


class ExpertBattleTests(unittest.TestCase):
    def test_opening_balloon_then_free_tatsugiri_retreat(self):
        obs = obs_for(pokemon(105), bench=[pokemon(122)], hand=[card(1174), card(904)],
                      options=[attach(1174), {"type": OPT_END}])
        obs["current"]["turn"] = 1
        self.assertEqual(agent(obs), [0])
        obs["current"]["players"][0]["active"][0]["tools"] = [card(1174)]
        obs["select"]["option"] = [{"type": OPT_RETREAT}, {"type": OPT_END}]
        self.assertEqual(agent(obs), [0])
        obs["select"].update(context=CTX_SWITCH, option=[target(0)])
        self.assertEqual(agent(obs), [0])

    def test_opening_route_does_not_spend_energy_to_retreat(self):
        obs = obs_for(pokemon(105, [3]), bench=[pokemon(122)],
                      options=[{"type": OPT_RETREAT}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [1])

    def test_supporter_in_hand_does_not_need_speculative_opening_pivot(self):
        obs = obs_for(pokemon(105), bench=[pokemon(122)], hand=[card(1174), card(1227)],
                      options=[attach(1174), {"type": OPT_PLAY, "cardId": 1227}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [1])

    def test_balloon_scores_do_not_leak_into_energy_options(self):
        state = normalize_state(obs_for(pokemon(122), hand=[card(3)], options=[attach(3)]))
        self.assertEqual(score_air_balloon_target(state, state.options[0]).score, 0)

    def test_balloon_on_benched_palafin_before_double_transform_route(self):
        pivot = pokemon(106, [3])
        pivot["serial"] = 2002
        obs = obs_for(pokemon(106, [3]), bench=[pivot], hand=[card(1174)], options=[
            {"type": OPT_ABILITY, "cardId": 1262}, attach(1174, AREA_BENCH), {"type": OPT_END}])
        obs["current"]["stadium"] = [card(1262)]
        self.assertTrue(bench_balloon_pivot(normalize_state(obs), pivot))
        self.assertEqual(agent(obs), [1])

    def test_choose_second_normal_palafin_as_free_return_pivot(self):
        pivot = pokemon(106, [3])
        pivot.update(serial=2002, tools=[card(1174)])
        obs = obs_for(pokemon(106, [3]), bench=[pokemon(105), pivot], options=[target(0), target(1)],
                      select_extra={"context": CTX_SWITCH, "sourceCardId": 1262})
        self.assertEqual(agent(obs), [1])

    def test_spent_retreat_and_non_ability_palafin_are_not_double_transform_pivots(self):
        pivot = pokemon(51, [3])
        obs = obs_for(pokemon(106, [3]), bench=[pivot], options=[{"type": OPT_ABILITY, "cardId": 1262}])
        self.assertFalse(bench_balloon_pivot(normalize_state(obs), pivot))
        pivot["cardId"] = pivot["id"] = 106
        pivot["serial"] = 2002
        obs["current"]["retreated"] = True
        self.assertFalse(bench_balloon_pivot(normalize_state(obs), pivot))

    def test_balloon_is_not_a_second_manual_retreat(self):
        self.assertEqual(MovementResources(free_retreat=True, air_balloon_attach_to_active=True).conservative_count, 1)
        active = pokemon(106, [3])
        active["tools"] = [card(1174)]
        obs = obs_for(active)
        obs["current"]["retreated"] = True
        self.assertEqual(movement_resources(normalize_state(obs)).conservative_count, 0)

    def test_guidance_finds_usable_backup_palafin_after_dragonair_evolved(self):
        dragonair = pokemon(903, [4])
        dragonair["appearThisTurn"] = True
        obs = obs_for(pokemon(107, [3]), bench=[pokemon(105), dragonair], options=[
            {"type": OPT_CARD, "cardId": 904}, {"type": OPT_CARD, "cardId": 106},
            {"type": OPT_CARD, "cardId": 107}], select_extra={"context": CTX_TO_HAND, "sourceCardId": 903})
        self.assertEqual(agent(obs), [1])

    def test_guidance_still_finds_mega_when_evolution_legal_now(self):
        obs = obs_for(pokemon(105), bench=[pokemon(903, [4])], options=[
            {"type": OPT_CARD, "cardId": 904}, {"type": OPT_CARD, "cardId": 106}],
            select_extra={"context": CTX_TO_HAND, "sourceCardId": 903})
        self.assertEqual(agent(obs), [0])

    def test_giga_does_not_claim_ko_through_cornerstone(self):
        obs = finisher_obs(opponent_id=117, hp=210)
        obs["select"]["option"] = [{"type": OPT_ATTACK, "attackId": 134}, {"type": OPT_END}]
        state = normalize_state(obs)
        self.assertEqual(estimate_attack_damage(state, get_db().get_attack(134),
                         state.current["players"][0]["active"][0], state.current["players"][1]["active"][0]), 0)
        self.assertLess(score_giga_impact_attack(state, state.options[0]).score, 0)
        self.assertEqual(agent(obs), [1])

    def test_no_ability_attacker_is_not_blocked_by_cornerstone(self):
        obs = finisher_obs(opponent_id=117, hp=130)
        obs["current"]["players"][0]["active"] = [pokemon(51, [3])]
        obs["select"]["option"] = [{"type": OPT_END}, {"type": OPT_ATTACK, "attackId": 51}]
        self.assertEqual(agent(obs), [1])

    def test_giga_counts_three_prize_mega_ko(self):
        obs = finisher_obs(opponent_id=904, hp=240)
        obs["current"]["players"][0]["prize"] = [None] * 3
        state = normalize_state(obs)
        self.assertEqual(score_giga_impact_attack(state, state.options[0]).reason, "Giga Impact takes final prizes.")

    def test_sky_transport_to_dragonite_finisher_before_nonko_giga(self):
        self.assertEqual(agent(finisher_obs()), [1])

    def test_do_not_plan_gust_for_active_without_legal_attack(self):
        obs = finisher_obs(energy=())
        obs["current"]["players"][1]["bench"] = [pokemon(107, player=1)]
        obs["current"]["players"][1]["bench"][0]["hp"] = 200
        obs["select"]["option"] = [{"type": OPT_PLAY, "cardId": 1182}, {"type": OPT_END}]
        self.assertIsNone(finishing_action(normalize_state(obs))[0])

    def test_select_dragonite_during_finishing_switch_resolution(self):
        obs = finisher_obs()
        obs["current"]["players"][0]["bench"].append(pokemon(122))
        obs["select"].update(context=CTX_SWITCH, sourceCardId=904, option=[target(0), target(1)])
        self.assertEqual(agent(obs), [0])

    def test_finisher_reason_is_recorded(self):
        from decision_reason import build_decision_record
        from policy import choose_main_turn_action, classify_all_options, score_options

        state = normalize_state(finisher_obs())
        choice = choose_main_turn_action(state, state.select, classify_all_options(state, state.select))
        trace = build_decision_record(state, score_options(state), choice)
        self.assertIn("finisher", trace["reason"])

    def test_finishing_energy_is_exact_typed_cost_not_three_any(self):
        attack = get_db().get_attack(1302)
        self.assertTrue(attack_energy_ready(pokemon(904, [4, 4, 3]), attack))
        self.assertFalse(attack_energy_ready(pokemon(904, [3, 3, 4]), attack))
        self.assertIsNone(finishing_action(normalize_state(finisher_obs(energy=(3, 3, 4))))[0])

    def test_attach_last_water_before_finishing_switch(self):
        obs = finisher_obs(energy=(4, 4))
        obs["current"]["players"][0]["hand"] = [card(3)]
        obs["select"]["option"].insert(0, attach(3, AREA_BENCH))
        self.assertEqual(agent(obs), [0])

    def test_gust_opponent_target_is_not_scored_as_own_pivot(self):
        obs = finisher_obs(opponent_id=117, hp=210)
        obs["current"]["players"][1]["bench"] = [pokemon(117, player=1), pokemon(107, player=1)]
        obs["current"]["players"][1]["bench"][1]["hp"] = 200
        obs["select"].update(context=CTX_SWITCH, sourceCardId=1182, option=[target(0, 1), target(1, 1)])
        self.assertEqual(agent(obs), [1])

    def test_secret_box_finishing_boss_over_refresh(self):
        obs = finisher_obs(opponent_id=117, hp=210)
        target_ex = pokemon(107, player=1)
        target_ex["hp"] = 200
        obs["current"]["players"][1]["bench"] = [target_ex]
        obs["select"].update(context=CTX_TO_HAND, sourceCardId=1092,
                             option=[{"type": OPT_CARD, "cardId": 1227}, {"type": OPT_CARD, "cardId": 1182}])
        self.assertEqual(agent(obs), [1])

    def test_extra_ex_discard_requires_two_built_attackers(self):
        backup = pokemon(107, [3])
        backup["serial"] = 2002
        state = normalize_state(obs_for(pokemon(107, [3]), bench=[backup], hand=[card(107)]))
        self.assertGreater(score_discard_selection(state, 107), 0)
        state = normalize_state(obs_for(pokemon(106, [3]), hand=[card(107)]))
        self.assertFalse(redundant_attacker_discard(state, 107))
        self.assertLess(score_discard_selection(state, 107), 0)

    def test_mega_never_pays_two_energy_to_retreat(self):
        obs = obs_for(pokemon(904, [3, 4, 4]), bench=[pokemon(107, [3])],
                      options=[{"type": OPT_RETREAT}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [1])
