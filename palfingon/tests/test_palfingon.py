from __future__ import annotations

import os
import unittest
from collections import Counter
from pathlib import Path

from agent import agent
from card_db import get_db
from core.card_analysis import build_all_card_analyses
from core.card_relationships import build_card_relationships, deck_card_names
from core.palafin_planner import score_energy_attachment
from core.palfingon_cards import score_battle_cage, score_stretcher, stretcher_target_score
from core.priority_tables import canonical_name_from_id
from core.strategy_scope import active_strategy_id, reset_strategy_scope_cache
from core.turn_plan import zero_to_hero_route
from deck_profile import load_deck_ids, load_profile, reset_profile_cache
from state_eval import AREA_ACTIVE, AREA_BENCH, AREA_DECK, AREA_HAND, CTX_TO_HAND, OPT_ATTACH, OPT_ATTACK, OPT_CARD, OPT_END, OPT_EVOLVE, OPT_PLAY, OPT_RETREAT, normalize_state
from tests.test_palafin_strategy import card, obs_for, pokemon


class PalfingonTests(unittest.TestCase):
    def test_exact_resolved_counts_and_four_normal_palafin_by_name(self):
        counts = Counter(load_deck_ids())
        self.assertEqual(sum(counts.values()), 60)
        self.assertEqual({i: counts[i] for i in (51, 106, 1097, 3, 4, 1219, 1213, 1264)},
                         {51: 1, 106: 3, 1097: 2, 3: 6, 4: 3, 1219: 3, 1213: 1, 1264: 1})
        self.assertFalse({1129, 1191} & counts.keys())

    def test_profile_and_relations_have_no_removed_deck_cards(self):
        ids = set(load_deck_ids())
        for key, value in load_profile().items():
            if isinstance(value, list) and value and all(type(x) is int for x in value):
                self.assertTrue(set(value) <= ids, key)
        names = set(deck_card_names())
        for relationship in build_card_relationships():
            self.assertIn(relationship.source_card, names)
            self.assertIn(relationship.target_card, names)

    def test_parent_working_directory_does_not_change_deck_or_profile(self):
        original = Path.cwd()
        try:
            os.chdir(Path(__file__).resolve().parents[2])
            reset_profile_cache()
            self.assertEqual(active_strategy_id(), "palfingon")
            self.assertEqual(load_profile()["deck_name"], "palfingon")
            self.assertEqual(Counter(load_deck_ids())[51], 1)
        finally:
            os.chdir(original)
            reset_profile_cache()

    def test_engine_attack_ids_available_without_native_cabt(self):
        self.assertEqual(get_db().get_attack(134).name, "Giga Impact")
        self.assertEqual(get_db().get_attack(51).name, "Vanguard Punch")
        self.assertEqual([a.attack_id for a in get_db().get_card(107).attacks], [134])

    def test_two_normal_palafin_have_separate_analysis(self):
        self.assertNotEqual(canonical_name_from_id(51), canonical_name_from_id(106))
        analyses = build_all_card_analyses()
        self.assertEqual(analyses["Palafin"].count_in_deck, 3)
        self.assertEqual(analyses["Palafin TEF 49"].count_in_deck, 1)
        self.assertIn("one_prize_attacker", analyses["Palafin TEF 49"].role)

    def test_vanguard_palafin_cannot_start_zero_to_hero(self):
        obs = obs_for(pokemon(51, [3]), bench=[pokemon(105)], hand=[card(1123)],
                      options=[{"type": OPT_PLAY, "cardId": 1123}, {"type": OPT_RETREAT}])
        route = zero_to_hero_route(normalize_state(obs))
        self.assertFalse(route.can_start)

    def test_vanguard_takes_legal_ko(self):
        obs = obs_for(pokemon(51, [3]), options=[{"type": OPT_END}, {"type": OPT_ATTACK, "attackId": 51}])
        self.assertEqual(agent(obs), [1])

    def test_vanguard_avoids_nonwinning_self_ko(self):
        active = pokemon(51, [3])
        active["hp"] = 70
        obs = obs_for(active, bench=[pokemon(105)], options=[{"type": OPT_ATTACK, "attackId": 51}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [1])

    def test_each_water_line_stops_at_one_and_rejects_lightning(self):
        for cid in (51, 105, 106, 107):
            for energy in (3, 4):
                with self.subTest(cid=cid, energy=energy):
                    target = pokemon(cid, [3])
                    state = normalize_state(obs_for(target))
                    self.assertLessEqual(score_energy_attachment(state, energy, target), -100000)
                    unpowered = pokemon(cid)
                    self.assertLessEqual(score_energy_attachment(state, 4, unpowered), -100000)

    def test_dragonite_does_not_take_second_water(self):
        for cid in (902, 903, 904):
            target = pokemon(cid, [3])
            state = normalize_state(obs_for(pokemon(107, [3]), bench=[target]))
            self.assertLessEqual(score_energy_attachment(state, 3, target), -100000)

    def test_real_choice_rejects_extra_water_to_vanguard(self):
        obs = obs_for(pokemon(51, [3]), hand=[card(3)], options=[
            {"type": OPT_ATTACH, "cardId": 3, "area": AREA_HAND, "index": 0,
             "playerIndex": 0, "inPlayArea": AREA_ACTIVE, "inPlayIndex": 0}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [1])

    def test_judge_plays_as_only_hand_card(self):
        obs = obs_for(pokemon(105), hand=[card(1213)], options=[{"type": OPT_END}, {"type": OPT_PLAY, "cardId": 1213}])
        self.assertEqual(agent(obs), [1])

    def test_use_poffin_before_judge_then_recheck_judge(self):
        obs = obs_for(pokemon(105), hand=[card(1213), card(1086)], options=[
            {"type": OPT_PLAY, "cardId": 1213}, {"type": OPT_PLAY, "cardId": 1086}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [1])
        obs = obs_for(pokemon(105), bench=[pokemon(105), pokemon(122)], hand=[card(1213)], options=[
            {"type": OPT_PLAY, "cardId": 1213}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [0])

    def test_judge_not_selected_by_hand_order(self):
        obs = obs_for(pokemon(105), hand=[card(1213), card(1227)], options=[
            {"type": OPT_PLAY, "area": AREA_HAND, "index": 0, "playerIndex": 0},
            {"type": OPT_PLAY, "area": AREA_HAND, "index": 1, "playerIndex": 0}, {"type": OPT_END}])
        self.assertEqual(agent(obs), [1])

    def test_battle_cage_does_not_replace_live_surfing_route(self):
        obs = obs_for(pokemon(106, [3]), bench=[pokemon(105)], hand=[card(1264)], options=[
            {"type": OPT_PLAY, "cardId": 1264}, {"type": OPT_END}])
        obs["current"]["stadium"] = [card(1262)]
        self.assertLess(score_battle_cage(normalize_state(obs)), 0)
        self.assertEqual(agent(obs), [1])

    def test_battle_cage_values_public_counter_threat(self):
        db = get_db()
        threat = next(c.card_id for c in db.cards.values() if c.name == "Munkidori")
        obs = obs_for(pokemon(105), bench=[pokemon(105)], hand=[card(1264)], options=[
            {"type": OPT_END}, {"type": OPT_PLAY, "cardId": 1264}])
        obs["current"]["players"][1]["bench"] = [pokemon(threat, player=1)]
        self.assertGreater(score_battle_cage(normalize_state(obs)), 0)
        self.assertEqual(agent(obs), [1])

    def test_stretcher_cannot_restore_ex_to_deck_by_itself(self):
        obs = obs_for(pokemon(106), hand=[card(1097)])
        obs["current"]["players"][0]["discard"] = [card(107)]
        state = normalize_state(obs)
        self.assertLess(stretcher_target_score(state, 107), 0)
        self.assertLess(score_stretcher(state), 0)

    def test_hilda_search_prefers_bridge_over_stranded_ex(self):
        obs = obs_for(pokemon(105, [3]), bench=[pokemon(902)], options=[
            {"type": OPT_CARD, "cardId": 107}, {"type": OPT_CARD, "cardId": 106}],
            select_extra={"context": CTX_TO_HAND, "sourceCardId": 1225})
        self.assertEqual(agent(obs), [1])

    def test_setup_handshake_uses_new_deck(self):
        self.assertEqual(agent({"current": None, "select": None}), load_deck_ids())
