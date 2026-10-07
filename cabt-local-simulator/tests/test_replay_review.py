from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from cabt_local.official_visualizer import (
    build_review_choice, load_replay_observations, refresh_replay_html, render_official_replay,
)
from cabt_local.replay_review import selection_contract
from cabt_local.webapp import load_episode_payload


def search_observation(maximum: int = 2) -> dict:
    return {
        "current": {"turn": 3, "yourIndex": 0, "supporterPlayed": True, "players": [
            {"hand": [], "benchMax": 5, "bench": [{"id": 902}], "prize": [None, None]}, {}]},
        "select": {"context": 5, "minCount": 0, "maxCount": maximum,
            "effect": {"id": 1086, "serial": 40},
            "deck": [{"id": 105, "serial": 1}, {"id": 902, "serial": 2},
                     {"id": 105, "serial": 3}, {"id": 122, "serial": 4}, {"id": 106, "serial": 5}],
            "option": [{"type": 3, "area": 1, "index": i, "playerIndex": 0} for i in [0, 2, 3]]}}


NAMES = {105: "Finizen", 106: "Palafin", 902: "Dratini", 122: "Tatsugiri", 1086: "Buddy-Buddy Poffin"}
METADATA = {"105": {"hp": 50, "stage": "Basic"}, "902": {"hp": 80, "stage": "Basic"}}


class ReplayReviewTests(unittest.TestCase):
    def test_search_uses_only_engine_candidates_not_entire_deck(self):
        obs = search_observation()
        result = build_review_choice(obs, obs, [0, 2], NAMES, METADATA)
        self.assertTrue(result["editable"])
        self.assertEqual(result["min_count"], 0)
        self.assertEqual(result["max_count"], 2)
        self.assertEqual([o["card"]["id"] for o in result["options"]], [105, 105, 122])
        self.assertNotEqual(result["options"][0]["detail"], result["options"][1]["detail"])
        self.assertIn("50 HP", result["options"][0]["detail"])
        self.assertEqual(result["effect"]["name"], "Buddy-Buddy Poffin")
        self.assertEqual(result["facts"]["bench_spaces"], 4)

    def test_restricted_bench_window_retains_engine_maximum(self):
        obs = search_observation(1)
        obs["current"]["players"][0]["bench"] *= 4
        c = build_review_choice(obs, obs, [0], NAMES, METADATA)
        self.assertEqual(c["max_count"], 1)
        self.assertEqual(c["facts"]["bench_spaces"], 1)

    def test_hand_play_targets_and_engine_options_are_not_synthesized(self):
        obs = search_observation()
        obs["current"]["players"][0]["hand"] = [{"id": 1086}, {"id": 105}, {"id": 902}]
        obs["current"]["players"][0]["bench"] = [{"id": 105, "serial": 8}, {"id": 105, "serial": 9}]
        obs["select"] = {"context": 0, "minCount": 1, "maxCount": 1, "option": [
            {"type": 7, "index": 0}, {"type": 9, "area": 2, "index": 1, "inPlayArea": 5, "inPlayIndex": 1}, {"type": 14}]}
        c = build_review_choice(obs, obs, [0], NAMES, METADATA)
        self.assertEqual(len(c["options"]), 3)
        self.assertEqual(c["options"][0]["label"], "Play Buddy-Buddy Poffin")
        self.assertIn("target Bench 2", c["options"][1]["detail"])
        self.assertNotIn("Dratini", json.dumps(c["options"]))

    def test_hidden_prizes_never_resolve_from_omniscient_replay(self):
        obs = search_observation()
        obs["select"] = {"context": 7, "minCount": 1, "maxCount": 1,
                         "option": [{"type": 3, "area": 6, "index": 0, "playerIndex": 0}]}
        full = deepcopy(obs)
        full["current"]["players"][0]["prize"] = [{"id": 902}, {"id": 106}]
        for visible in [obs, None]:
            c = build_review_choice(full, visible, [0], NAMES, METADATA)
            self.assertIsNone(c["options"][0]["card"])
            self.assertEqual(c["options"][0]["label"], "Hidden prize card")

    def test_known_prize_may_be_identified_in_observation(self):
        obs = search_observation()
        obs["current"]["players"][0]["prize"][0] = {"id": 105}
        obs["select"] = {"context": 7, "minCount": 1, "maxCount": 1,
                         "option": [{"type": 3, "area": 6, "index": 0, "playerIndex": 0}]}
        c = build_review_choice(obs, obs, [0], NAMES, METADATA)
        self.assertIn("Finizen", c["options"][0]["label"])

    def test_missing_or_invalid_bounds_are_comment_only(self):
        for select in [{}, {"option": []}, {"option": [], "minCount": 1, "maxCount": 1},
                       {"option": [1], "minCount": True, "maxCount": 1},
                       {"option": [1], "minCount": 0, "maxCount": -1}]:
            self.assertFalse(selection_contract(select)["editable"])
        self.assertTrue(selection_contract({"option": [], "minCount": 0, "maxCount": 0})["editable"])

    def test_empty_optional_and_unknown_option_are_preserved(self):
        obs = {"current": {}, "select": {"context": 999, "option": [{"type": 999, "futureField": 2}], "minCount": 0, "maxCount": 1}}
        c = build_review_choice(obs, obs, [], {}, {})
        self.assertTrue(c["editable"])
        self.assertEqual(c["original"], [])
        self.assertEqual(c["options"][0]["option"], {"type": 999, "futureField": 2})
        self.assertIn("futureField", c["options"][0]["label"])
        malformed = {"select": {"option": "not a list"}}
        self.assertFalse(build_review_choice(malformed, malformed, [], {}, {})["editable"])

    def test_episode_view_links_to_review_without_changing_episode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            episode = root / "data" / "episodes" / "battle.jsonl"
            episode.parent.mkdir(parents=True)
            original = json.dumps({"observation": search_observation(), "selected_indexes": [0]}) + "\n"
            episode.write_text(original)
            replay = root / "data" / "replays" / "battle.html"
            replay.parent.mkdir(parents=True)
            replay.write_text("<html></html>")
            result = load_episode_payload(root, "data/episodes/battle.jsonl")
            self.assertEqual(result["review_url"], "/files/data/replays/battle.html")
            self.assertEqual(episode.read_text(), original)

    def test_observation_alignment_fail_closed_and_numeric_enum_equivalence(self):
        obs = search_observation()
        replay = deepcopy(obs)
        replay["select"]["context"] = "ToBench"
        for o in replay["select"]["option"]:
            o["type"] = "Card"
        self.assertTrue(build_review_choice(replay, obs, [], NAMES, METADATA)["editable"])
        replay["select"]["option"].reverse()
        self.assertFalse(build_review_choice(replay, obs, [], NAMES, METADATA)["editable"])

    def test_attached_energy_and_tool_labels(self):
        obs = search_observation()
        obs["current"]["players"][0]["bench"][0]["energyCards"] = [{"id": 3, "serial": 90}]
        obs["select"] = {"context": 26, "minCount": 1, "maxCount": 1,
                         "option": [{"type": 5, "area": 5, "index": 0, "playerIndex": 0, "energyIndex": 0}]}
        c = build_review_choice(obs, obs, [0], {3: "Water Energy"}, {})
        self.assertEqual(c["options"][0]["card"]["serial"], 90)

    def test_refresh_preserves_files_and_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data" / "replays" / "battle.html"
            path.parent.mkdir(parents=True)
            original = '<html><script id="replay-data" type="application/json">[]</script></html>'
            path.write_text(original)
            refreshed = refresh_replay_html(path, original)
            self.assertIn('id="exportReview"', refreshed)
            self.assertIn('sessionStorage', refreshed)
            self.assertNotIn('__REVIEW_', refreshed)
            self.assertEqual(path.read_text(), original)
            self.assertEqual(refresh_replay_html(path, refreshed), refreshed)
            self.assertEqual(refresh_replay_html(path, '<p>Plain log</p>'), '<p>Plain log</p>')

    def test_no_trace_required_and_script_embedding_escaped(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'data' / 'replays' / 'battle.html'
            episode = path.parent.parent / 'episodes' / 'battle.jsonl'
            episode.parent.mkdir(parents=True)
            obs = search_observation()
            episode.write_text(json.dumps({"decision_index": 0, "observation": obs}) + '\ninvalid\n')
            self.assertEqual(load_replay_observations(path)[0], obs)
            obs['select']['deck'][0]['name'] = '</script><script>alert(1)</script>'
            frames = [obs, {"current": obs['current'], "logs": [], "selected": [0]}]
            page = render_official_replay(path, frames)
            self.assertNotIn('</script><script>alert(1)', page)
            self.assertIn('<\\/script>', page)


if __name__ == '__main__':
    unittest.main()
