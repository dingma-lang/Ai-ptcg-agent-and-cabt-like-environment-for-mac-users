import json
import unittest
from pathlib import Path

from agent import agent
from core.agent_memory import AgentMemory
from core.reviewed_turn_planner import (
    box_discard_plan, confirmed_deck_counts, second_palafin_pivot,
)
from state_eval import (
    CTX_DISCARD, OPT_ATTACK, OPT_CARD, OPT_END, OPT_PLAY, card_id,
    card_id_from_option, normalize_state,
)
from tests.test_palafin_strategy import card, obs_for, pokemon


def cases():
    return json.loads((Path(__file__).parent / "fixtures/battle24_review.json").read_text())["decisions"]


class BattleReviewTests(unittest.TestCase):
    def test_all_fourteen_original_review_windows(self):
        for index, case in cases().items():
            with self.subTest(decision=index):
                agent({"current": None, "select": None})
                self.assertEqual(agent(case["observation"]), [case["expected"]])

    def test_preparation_rechecks_after_energy_not_attack_shortcut(self):
        obs = cases()["136"]["observation"]
        player = obs["current"]["players"][0]
        water = next(c for c in player["hand"] if c["id"] == 3)
        player["hand"].remove(water)
        player["bench"][0]["energies"].append(3)
        player["bench"][0]["energyCards"].append(water)
        obs["current"]["energyAttached"] = True
        # Rebuild this main window's legal choices after the attachment resolves.
        obs["select"]["option"] = [
            {"type": OPT_PLAY, "cardId": 1219},
            {"type": OPT_ATTACK, "attackId": 134}, {"type": OPT_END},
        ]
        self.assertEqual(agent(obs), [0])
        obs["current"]["supporterPlayed"] = True
        obs["select"]["option"].pop(0)
        self.assertEqual(agent(obs), [0])

    def test_confirmed_final_prize_win_still_beats_refresh(self):
        obs = obs_for(pokemon(107, [3]), hand=[card(1227)], options=[
            {"type": OPT_PLAY, "cardId": 1227}, {"type": OPT_ATTACK, "attackId": 134},
            {"type": OPT_END}])
        obs["current"]["players"][0]["prize"] = [None]
        obs["current"]["players"][1]["active"] = [pokemon(105, player=1)]
        self.assertEqual(agent(obs), [1])

    def test_box_cost_and_search_do_not_assume_prized_recovery(self):
        obs = cases()["28"]["observation"]
        state = normalize_state(obs)
        plan = box_discard_plan(state)
        self.assertEqual({card_id(state.current["players"][1]["hand"][i]) for i in plan}, {904, 3, 4})
        obs["select"]["deck"] = [c for c in obs["select"]["deck"] if c["id"] not in (1118, 1097)]
        self.assertFalse(box_discard_plan(normalize_state(obs)))

    def test_box_does_not_discard_only_mega_without_confirmed_replacement(self):
        obs = cases()["28"]["observation"]
        obs["select"]["deck"] = [c for c in obs["select"]["deck"] if c["id"] != 904]
        state = normalize_state(obs)
        plan = box_discard_plan(state)
        self.assertNotIn(904, [card_id(state.current["players"][1]["hand"][i]) for i in plan])

    def test_search_memory_reaches_box_discard_prompt_and_is_private(self):
        memory = AgentMemory()
        obs = cases()["28"]["observation"]
        state = normalize_state(obs)
        memory.update_from_state(state)
        obs["select"].update(context=CTX_DISCARD, effect=card(1092), deck=None,
                             minCount=3, maxCount=3, option=[
            {"type": OPT_CARD, "area": 2, "index": i, "playerIndex": 1} for i in range(4)])
        obs["logs"] = [{"type": 6, "fromArea": 1, "toArea": 2, "playerIndex": 1,
                        "serial": 107, "cardId": 1092}]
        state = normalize_state(obs)
        memory.update_from_state(state)
        self.assertEqual(confirmed_deck_counts(state)[1092], 0)
        self.assertTrue(box_discard_plan(state))
        from policy import score_options, choose_by_scores

        selected = choose_by_scores(state, score_options(state))
        self.assertEqual({card_id_from_option(state, state.options[i]) for i in selected}, {904, 3, 4})
        obs["current"]["yourIndex"] = 0
        state = normalize_state(obs)
        memory.update_from_state(state)
        self.assertFalse(confirmed_deck_counts(state))

    def test_omniscient_deck_cannot_enable_safe_discard(self):
        obs = cases()["28"]["observation"]
        obs["current"]["players"][1]["deck"] = obs["select"]["deck"]
        obs["select"]["deck"] = None
        self.assertFalse(box_discard_plan(normalize_state(obs)))

    def test_poffin_kept_when_bench_empty(self):
        obs = cases()["28"]["observation"]
        obs["current"]["players"][1]["bench"] = []
        obs["current"]["players"][1]["hand"].append(card(1086))
        state = normalize_state(obs)
        self.assertNotIn(4, box_discard_plan(state))

    def test_box_cannot_fetch_two_recovery_items_in_one_item_slot(self):
        obs = obs_for(pokemon(105), hand=[card(3), card(4), card(3), card(1092)])
        obs["select"]["deck"] = [card(1097), card(1097)]
        self.assertFalse(box_discard_plan(normalize_state(obs)))

    def test_box_replaces_low_impact_trainers_once_per_category(self):
        obs = obs_for(pokemon(105), hand=[card(1262), card(1225), card(1118), card(1092)])
        obs["current"]["supporterPlayed"] = True
        obs["current"]["stadium"] = [card(1262)]
        obs["select"]["deck"] = [card(1262), card(1227), card(1086), card(1174)]
        self.assertEqual(set(box_discard_plan(normalize_state(obs))), {0, 1, 2})

    def test_search_knowledge_expires_on_next_turn(self):
        memory = AgentMemory()
        obs = cases()["28"]["observation"]
        memory.update_from_state(normalize_state(obs))
        obs["current"]["turn"] += 2
        obs["select"]["deck"] = None
        obs["logs"] = []
        state = normalize_state(obs)
        memory.update_from_state(state)
        self.assertFalse(confirmed_deck_counts(state))

    def test_second_transform_needs_independent_return_move(self):
        obs = cases()["133"]["observation"]
        target = obs["current"]["players"][0]["bench"][2]
        self.assertTrue(second_palafin_pivot(normalize_state(obs), target))
        obs["current"]["players"][0]["hand"] = []
        obs["current"]["retreated"] = True
        self.assertFalse(second_palafin_pivot(normalize_state(obs), target))

    def test_dead_hilda_does_not_win_by_hand_index(self):
        obs = cases()["65"]["observation"]
        obs["select"]["option"] = [
            {"type": OPT_PLAY, "cardId": 1225}, {"type": OPT_PLAY, "cardId": 1219},
            {"type": OPT_END}]
        self.assertEqual(agent(obs), [1])
        obs["select"]["option"][:2] = reversed(obs["select"]["option"][:2])
        self.assertEqual(agent(obs), [0])
