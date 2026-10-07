from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import config
from core.action_intent import ActionIntent
from deck_profile import list_value
from state_eval import (
    active_pokemon,
    bench_pokemon,
    card_id,
    deck_count,
    discard_cards,
    getv,
    hand_cards,
    int_or,
    prize_cards,
)


MEMORY_PATH = Path("memory") / "agent_memory.jsonl"


@dataclass
class AgentMemory:
    current_game_id: str = ""
    turn_number: int = 0
    known_hand_cards: List[int] = field(default_factory=list)
    known_deck_or_prize_inference: Dict[str, Any] = field(default_factory=dict)
    discard_pile: List[int] = field(default_factory=list)
    opponent_public_cards: List[int] = field(default_factory=list)
    opponent_revealed_cards: Set[int] = field(default_factory=set)
    opponent_inferred_archetype: str = "unknown"
    previous_actions_taken: List[Dict[str, Any]] = field(default_factory=list)
    cards_already_used_this_turn: List[int] = field(default_factory=list)
    supporter_used: bool = False
    energy_attached: bool = False
    retreated: bool = False
    stadium_played: bool = False
    known_prize_information: Dict[int, int] = field(default_factory=dict)
    protected_cards_remaining: Dict[int, int] = field(default_factory=dict)
    discardable_cards_remaining: Dict[int, int] = field(default_factory=dict)
    matchup_notes_activated: List[str] = field(default_factory=list)
    last_chosen_intent: str = ""
    last_chosen_reason: str = ""
    detected_mistakes_from_previous_games: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)

    def update_from_state(self, state: Any, mode: str = "CABT_SUBMISSION_MODE") -> None:
        current = getv(state, "current", None)
        self.turn_number = int_or(getv(current, "turn", self.turn_number), self.turn_number)
        self.current_game_id = self.current_game_id or public_state_hash(state)[:12]
        self.known_hand_cards = compact_ids(hand_cards(state))
        self.discard_pile = compact_ids(discard_cards(state))
        self.opponent_public_cards = compact_ids([active_pokemon(state, state.opponent_index)] + bench_pokemon(state, state.opponent_index) + discard_cards(state, state.opponent_index))
        self.known_deck_or_prize_inference = {
            "our_deck_count": deck_count(state),
            "our_prize_count": len(prize_cards(state)),
            "opponent_deck_count": deck_count(state, state.opponent_index),
            "opponent_prize_count": len(prize_cards(state, state.opponent_index)),
        }
        self.supporter_used = bool(getv(current, "supporterPlayed", False))
        self.energy_attached = bool(getv(current, "energyAttached", False))
        self.retreated = bool(getv(current, "retreated", False))
        self.stadium_played = bool(getv(current, "stadiumPlayed", False))
        self.protected_cards_remaining = count_remaining(self.known_hand_cards, list_value("protected_cards"))
        self.discardable_cards_remaining = count_remaining(self.known_hand_cards, list_value("discard_freely"))
        self._record_revealed_from_logs(getv(state, "obs", {}))
        self._append_event(
            {
                "event_type": "STATE_OBSERVED",
                "mode": mode,
                "public_state_hash": public_state_hash(state),
            }
        )

    def record_intent(self, state: Any, intent: ActionIntent, mode: str = "CABT_SUBMISSION_MODE") -> None:
        self.last_chosen_intent = intent.intent_type
        self.last_chosen_reason = intent.reason
        event = {
            "game_id": self.current_game_id or public_state_hash(state)[:12],
            "turn": self.turn_number,
            "actor": "self",
            "event_type": "ACTION_CHOSEN",
            "intent_type": intent.intent_type,
            "source_card": intent.source_card_name or intent.source_card_id,
            "target_card": intent.target_card_name or intent.target_card_id,
            "reason": intent.reason,
            "public_state_hash": public_state_hash(state),
            "mode": mode,
        }
        self.previous_actions_taken.append(event)
        self._append_event(event)

    def load_detected_mistakes(self, mistakes: List[Dict[str, Any]]) -> None:
        self.detected_mistakes_from_previous_games = [dict(item) for item in mistakes if isinstance(item, dict)]

    def _record_revealed_from_logs(self, obs: Any) -> None:
        for log in getv(obs, "logs", []) or []:
            for key in ("cardId", "cardIdActive", "cardIdBench", "cardIdBefore", "cardIdAfter", "cardIdTarget"):
                cid = getv(log, key)
                if cid is not None:
                    try:
                        self.opponent_revealed_cards.add(int(cid))
                    except (TypeError, ValueError):
                        pass

    def _append_event(self, event: Dict[str, Any]) -> None:
        self.events.append(dict(event))
        if not config.ENABLE_MEMORY_FILE_WRITES:
            return
        try:
            MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
            with MEMORY_PATH.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, ensure_ascii=True, sort_keys=True) + "\n")
        except Exception:
            return


def compact_ids(cards: List[Any]) -> List[int]:
    out: List[int] = []
    for item in cards:
        cid = card_id(item)
        if cid is not None:
            out.append(cid)
    return out


def count_remaining(seen_ids: List[int], wanted_ids: List[int]) -> Dict[int, int]:
    wanted = set(wanted_ids)
    counts: Dict[int, int] = {}
    for cid in seen_ids:
        if cid in wanted:
            counts[cid] = counts.get(cid, 0) + 1
    return counts


def public_state_hash(state: Any) -> str:
    current = getv(state, "current", {})
    players = getv(current, "players", []) or []
    public: Dict[str, Any] = {
        "turn": getv(current, "turn", 0),
        "yourIndex": getv(current, "yourIndex", 0),
        "stadium": compact_ids(getv(current, "stadium", []) or []),
        "players": [],
    }
    if isinstance(players, list):
        for player in players[:2]:
            public["players"].append(
                {
                    "active": compact_ids(getv(player, "active", []) or []),
                    "bench": compact_ids(getv(player, "bench", []) or []),
                    "discard": compact_ids(getv(player, "discard", []) or []),
                    "deckCount": getv(player, "deckCount", 0),
                    "prizeCount": len(getv(player, "prize", []) or []),
                }
            )
    data = json.dumps(public, sort_keys=True, default=str)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


GLOBAL_AGENT_MEMORY = AgentMemory()
