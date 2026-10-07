from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from agent import agent
from core.agent_memory import AgentMemory
from core.palafin_attack_state import track_giga_impact_lock
from state_eval import AREA_BENCH, CTX_SWITCH, OPT_ABILITY, OPT_ATTACK, OPT_CARD, OPT_END, OPT_PLAY, OPT_RETREAT, normalize_state
from tests.test_palafin_strategy import obs_for, pokemon


def recorded(index):
    data = json.loads((Path(__file__).parent / "fixtures" / "battle15_stall.json").read_text())
    return data["decisions"][str(index)]


class AttackLockRegressionTests(unittest.TestCase):
    def test_numeric_attack_event_identifies_turn_nine_lock_on_turn_eleven(self):
        state = normalize_state(recorded(76))
        self.assertTrue(track_giga_impact_lock(state).restriction_applies_now)

    def test_lock_survives_a_later_decision_window_with_no_attack_log(self):
        memory = AgentMemory()
        first = normalize_state(recorded(76))
        memory.update_from_state(first)
        later = normalize_state(recorded(78))
        memory.update_from_state(later)
        self.assertTrue(track_giga_impact_lock(later).restriction_applies_now)

    def test_lock_clears_when_same_pokemon_visits_bench_and_returns(self):
        memory = AgentMemory()
        memory.update_from_state(normalize_state(recorded(76)))
        obs = recorded(78)
        obs["logs"] = [
            {"type": 8, "playerIndex": 0, "serialActive": 5, "serialBench": 7},
            {"type": 8, "playerIndex": 0, "serialActive": 7, "serialBench": 5},
        ]
        state = normalize_state(obs)
        memory.update_from_state(state)
        self.assertFalse(track_giga_impact_lock(state).restriction_applies_now)

    def test_expiry_is_absolute_turn_not_number_of_agent_calls(self):
        memory = AgentMemory()
        memory.update_from_state(normalize_state(recorded(76)))
        obs = recorded(78)
        obs["logs"] = []
        for _ in range(5):
            state = normalize_state(obs)
            memory.update_from_state(state)
            self.assertTrue(track_giga_impact_lock(state).restriction_applies_now)
        obs["current"]["turn"] = 13
        state = normalize_state(obs)
        memory.update_from_state(state)
        self.assertFalse(track_giga_impact_lock(state).restriction_applies_now)

    def test_same_turn_opponent_prompt_does_not_share_our_lock(self):
        memory = AgentMemory()
        memory.update_from_state(normalize_state(recorded(76)))
        obs = recorded(78)
        obs["logs"] = []
        obs["current"]["yourIndex"] = 1
        state = normalize_state(obs)
        memory.update_from_state(state)
        self.assertFalse(track_giga_impact_lock(state).restriction_applies_now)
        self.assertEqual(memory.attack_lock_observers[0]["locks"], {"5": 11})

    def test_new_game_clears_lock_even_when_serial_reused(self):
        memory = AgentMemory()
        memory.update_from_state(normalize_state(recorded(76)))
        obs = recorded(78)
        obs["logs"] = []
        obs["gameId"] = "new-game"
        state = normalize_state(obs)
        memory.update_from_state(state)
        self.assertFalse(track_giga_impact_lock(state).restriction_applies_now)

    def test_new_game_turn_counter_reset_clears_history(self):
        memory = AgentMemory()
        memory.update_from_state(normalize_state(recorded(76)))
        obs = recorded(78)
        obs["logs"] = []
        obs["current"]["turn"] = 3
        state = normalize_state(obs)
        memory.update_from_state(state)
        self.assertFalse(state.giga_impact_locks)

    def test_legal_giga_overrides_stale_explicit_flag(self):
        obs = obs_for(pokemon(107, [3]), options=[{"type": OPT_ATTACK, "attackId": 134}, {"type": OPT_END}])
        obs["current"]["gigaImpactLockInstanceId"] = "107"
        self.assertFalse(track_giga_impact_lock(normalize_state(obs)).restriction_applies_now)


class MovementStallRegressionTests(unittest.TestCase):
    def test_committed_switch_chooses_safe_return_pivot_without_prior_memory(self):
        from policy import score_options, choose_by_scores

        state = normalize_state(recorded(78))
        self.assertEqual(choose_by_scores(state, score_options(state)), [2])

    def test_turn_eleven_reset_selects_balloon_tatsugiri_not_unpowered_dragonite(self):
        agent(recorded(76))
        agent(recorded(77))
        self.assertEqual(agent(recorded(78)), [2])

    def test_turn_thirteen_uses_sky_then_powered_palafin_then_ko(self):
        obs = recorded(83)
        self.assertEqual(agent(obs), [9])
        obs["select"].update(context=CTX_SWITCH, sourceCardId=904, option=[
            {"type": OPT_CARD, "area": AREA_BENCH, "index": i, "playerIndex": 0} for i in range(4)])
        self.assertEqual(agent(obs), [0])
        me = obs["current"]["players"][0]
        me["active"][0], me["bench"][0] = me["bench"][0], me["active"][0]
        obs["select"].update(context=0, option=[{"type": OPT_ATTACK, "attackId": 134}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [0])

    def test_turn_twelve_can_use_free_ability_to_escape_active_dragonite(self):
        self.assertEqual(agent(recorded(82)), [3])

    def test_switch_item_can_escape_when_sky_is_not_legal(self):
        obs = recorded(83)
        obs["select"]["option"] = [{"type": OPT_PLAY, "cardId": 1123}, {"type": OPT_END}]
        self.assertEqual(agent(obs), [0])

    def test_escape_does_not_authorize_paid_dragonite_retreat(self):
        obs = recorded(83)
        obs["select"]["option"] = [{"type": OPT_RETREAT}, {"type": OPT_END}]
        self.assertEqual(agent(obs), [1])


class RefreshStallRegressionTests(unittest.TestCase):
    def test_decision_cache_does_not_survive_changed_legal_options(self):
        obs = recorded(83)
        self.assertEqual(agent(obs), [9])
        obs["select"]["option"] = [{"type": OPT_PLAY, "cardId": 1227}, {"type": OPT_END}]
        self.assertEqual(agent(obs), [0])
    def test_refresh_when_frozen_position_has_no_remaining_movement(self):
        obs = recorded(83)
        obs["select"]["option"] = [{"type": OPT_PLAY, "cardId": 1227}, {"type": OPT_END}]
        self.assertEqual(agent(obs), [0])

    def test_large_dead_hand_uses_judge_without_lillie(self):
        obs = recorded(82)
        obs["select"]["option"] = [{"type": OPT_PLAY, "cardId": 1213}, {"type": OPT_END}]
        self.assertEqual(agent(obs), [0])

    def test_end_remains_correct_when_every_choice_wastes_energy(self):
        obs = recorded(83)
        obs["select"]["option"] = [o for o in obs["select"]["option"] if o["type"] in (8, OPT_END)]
        choice = agent(obs)
        self.assertEqual(obs["select"]["option"][choice[0]]["type"], OPT_END)

    def test_stadium_on_board_is_not_counted_as_legal_move_from_dragonite(self):
        from core.turn_plan import movement_resources

        self.assertFalse(movement_resources(normalize_state(recorded(83))).stadium_switch)

    def test_spent_stadium_is_not_counted_again(self):
        from core.turn_plan import movement_resources

        obs = obs_for(pokemon(106, [3]), bench=[pokemon(105)], options=[{"type": OPT_END}])
        obs["current"]["stadium"] = [{"id": 1262}]
        self.assertFalse(movement_resources(normalize_state(obs)).stadium_switch)

    def test_positive_useful_score_is_not_overridden_by_500_point_cutoff(self):
        from policy import choose_by_scores

        state = normalize_state(obs_for(pokemon(105), options=[{"type": OPT_PLAY, "cardId": 1152}, {"type": OPT_END}]))
        self.assertEqual(choose_by_scores(state, [400.0, -1000.0]), [0])

    def test_supporter_diagnostics_distinguish_rejection_from_absence(self):
        from core.supporter_router import choose_best_supporter

        state = normalize_state(recorded(83))
        reason = choose_best_supporter(state, state.options).reason
        self.assertIn("Legal Supporters rejected", reason)

    def test_preserve_a_legal_active_ko_instead_of_switching(self):
        obs = obs_for(pokemon(107, [3]), bench=[pokemon(904, [3, 4, 4])], options=[
            {"type": OPT_ABILITY, "cardId": 904}, {"type": OPT_ATTACK, "attackId": 134}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [1])
