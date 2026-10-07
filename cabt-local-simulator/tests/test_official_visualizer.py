from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cabt_local.official_visualizer import (
    build_turn_procedures,
    load_replay_card_metadata,
    load_replay_decision_traces,
    write_official_replay,
)


def card(card_id: int, name: str, serial: int) -> dict:
    return {"id": card_id, "name": name, "serial": serial}


def player(hand: list[dict], *, active: list[dict] | None = None, bench: list[dict] | None = None) -> dict:
    return {
        "hand": hand,
        "handCount": len(hand),
        "deck": [],
        "deckCount": 50,
        "discard": [],
        "active": active or [],
        "bench": bench or [],
        "prize": [],
    }


class OfficialVisualizerTests(unittest.TestCase):
    def test_selected_option_is_matched_to_following_result_frame(self) -> None:
        finizen = card(10, "Finizen", 1)
        opponent = card(20, "N's Zorua", 2)
        frames = [
            {
                "current": {
                    "turn": 1,
                    "yourIndex": 0,
                    "players": [player([finizen]), player([], active=[opponent])],
                },
                "select": {
                    "context": "Main",
                    "option": [{"type": "Play", "index": 0}],
                },
                "logs": [
                    {"type": "TurnStart", "playerIndex": 0},
                    {"type": "Draw", "playerIndex": 0, "cardId": 10},
                ],
                "selected": None,
            },
            {
                "current": {
                    "turn": 1,
                    "yourIndex": 0,
                    "players": [player([], bench=[finizen]), player([], active=[opponent])],
                },
                "select": {"context": "Main", "option": [{"type": "End"}]},
                "logs": [
                    {"type": "Play", "playerIndex": 0, "cardId": 10},
                    {"type": "MoveCard", "playerIndex": 0, "cardId": 10, "fromArea": 2, "toArea": 5},
                ],
                "selected": [0],
            },
            {
                "current": {
                    "turn": 2,
                    "yourIndex": 1,
                    "players": [player([], bench=[finizen]), player([], active=[opponent])],
                },
                "select": {"context": "Main", "option": [{"type": "End"}]},
                "logs": [
                    {"type": "TurnEnd", "playerIndex": 0},
                    {"type": "TurnStart", "playerIndex": 1},
                ],
                "selected": [0],
            },
        ]

        turns = build_turn_procedures(frames)

        self.assertEqual(len(turns), 1)
        self.assertEqual(turns[0]["label"], "Turn 1 - Player 1")
        self.assertEqual(turns[0]["start_hands"][0][0]["name"], "Finizen")
        self.assertEqual(turns[0]["actions"][0]["title"], "Play Finizen")
        self.assertEqual(turns[0]["actions"][0]["result_frame"], 1)
        self.assertEqual(turns[0]["actions"][1]["title"], "End turn")
        self.assertEqual(turns[0]["end_hands"][0], [])

    def test_setup_uses_opening_hands_after_coin_decision(self) -> None:
        finizen = card(10, "Finizen", 1)
        frames = [
            {
                "current": {"turn": 0, "yourIndex": 0, "players": [player([]), player([])]},
                "select": {"context": "IsFirst", "option": [{"type": "Yes"}, {"type": "No"}]},
                "logs": [],
                "selected": None,
            },
            {
                "current": {"turn": 0, "yourIndex": 0, "players": [player([finizen]), player([])]},
                "select": {
                    "context": "SetupActivePokemon",
                    "option": [{"type": "Card", "area": 2, "index": 0, "playerIndex": 0}],
                },
                "logs": [{"type": "Draw", "playerIndex": 0, "cardId": 10}],
                "selected": [0],
            },
        ]

        turns = build_turn_procedures(frames)

        self.assertEqual(turns[0]["label"], "Setup")
        self.assertEqual(turns[0]["start_hands"][0][0]["name"], "Finizen")
        self.assertEqual(turns[0]["start_frame"], 1)
        self.assertEqual(turns[0]["actions"][0]["title"], "Choose to go first")

    def test_local_catalog_rows_merge_into_one_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            replay = root / "data" / "replays" / "battle.html"
            catalog = root / "data" / "catalog" / "cards.json"
            catalog.parent.mkdir(parents=True)
            catalog.write_text(
                json.dumps(
                    {
                        "cards": [
                            {
                                "card_id": 10,
                                "name": "Finizen",
                                "card_type": "Pokemon",
                                "hp": 70,
                                "raw": {"Move Name": "Ability One", "Effect Explanation": "Search."},
                            },
                            {
                                "card_id": 10,
                                "name": "Finizen",
                                "card_type": "Pokemon",
                                "hp": 70,
                                "raw": {"Move Name": "Wave Splash", "Cost": "W", "Damage": "30"},
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            metadata = load_replay_card_metadata(replay)

            self.assertEqual(metadata["10"]["name"], "Finizen")
            self.assertEqual([move["name"] for move in metadata["10"]["moves"]], ["Ability One", "Wave Splash"])

    def test_episode_trace_is_joined_to_matching_replay_action(self) -> None:
        finizen = card(10, "Finizen", 1)
        frames = [
            {
                "current": {"turn": 1, "yourIndex": 0, "players": [player([finizen]), player([])]},
                "select": {"context": "Main", "option": [{"type": "Play", "index": 0}, {"type": "End"}]},
                "logs": [],
                "selected": None,
            },
            {
                "current": {"turn": 1, "yourIndex": 0, "players": [player([]), player([])]},
                "select": {"context": "Main", "option": [{"type": "End"}]},
                "logs": [{"type": "Play", "playerIndex": 0, "cardId": 10}],
                "selected": [0],
            },
        ]
        trace = {
            0: {
                "reason": "Bench Finizen for the main evolution line.",
                "legal_options": [
                    {"index": 0, "category": "PLAY_BASIC_TO_BENCH", "card_name": "Finizen", "score": 4200},
                    {"index": 1, "category": "END_TURN", "score": -4100, "reason": "Useful setup remains."},
                ],
            }
        }

        turns = build_turn_procedures(frames, traces=trace)
        thought = turns[0]["actions"][0]["thought"]

        self.assertEqual(thought["reason"], "Bench Finizen for the main evolution line.")
        self.assertEqual(thought["selected"], [0])
        self.assertEqual(thought["options"][0]["score"], 4200.0)

    def test_trace_loader_reads_sibling_episode_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            replay = root / "data" / "replays" / "battle.html"
            episode = root / "data" / "episodes" / "battle.jsonl"
            episode.parent.mkdir(parents=True)
            episode.write_text(
                json.dumps(
                    {
                        "decision_index": 3,
                        "player": 1,
                        "agent_id": "file:agent.py:agent",
                        "agent_trace": {"reason": "Use the attack", "legal_options": []},
                    }
                ) + "\n",
                encoding="utf-8",
            )

            traces = load_replay_decision_traces(replay)

            self.assertEqual(traces[3]["reason"], "Use the attack")
            self.assertEqual(traces[3]["player"], 1)

    def test_written_replay_embeds_turns_and_card_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data" / "replays" / "battle.html"
            write_official_replay(path, "[]")
            page = path.read_text(encoding="utf-8")
            self.assertNotIn("__TURN_DATA__", page)
            self.assertNotIn("__CARD_DATA__", page)
            self.assertIn('id="turn-data"', page)
            self.assertIn("Competition list", page)
            self.assertIn("Agent reasoning", page)
            self.assertIn('id="zonePlayers"', page)
            self.assertIn('id="zone-deck"', page)
            self.assertIn('id="zone-prize"', page)
            self.assertIn('id="zone-discard"', page)
            self.assertIn('name="snapshotMoment"', page)
            self.assertIn('id="revealZones"', page)


if __name__ == "__main__":
    unittest.main()
