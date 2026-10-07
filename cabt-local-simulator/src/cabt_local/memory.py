from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .observation import getv, int_or, legal_options, normalized_features, redact_hidden_information


@dataclass
class MatchMemory:
    player: int
    turn: int = 0
    acting_player: int = 0
    decision_count: int = 0
    prize_counts: dict[str, int] = field(default_factory=dict)
    deck_counts: dict[str, int] = field(default_factory=dict)
    hand_counts: dict[str, int] = field(default_factory=dict)
    active: dict[str, Any] = field(default_factory=dict)
    bench: dict[str, list[Any]] = field(default_factory=dict)
    discard: dict[str, list[Any]] = field(default_factory=dict)
    stadium: Any = None
    once_per_turn: dict[str, Any] = field(default_factory=dict)
    revealed_cards: dict[str, Any] = field(default_factory=dict)
    previous_logs: list[Any] = field(default_factory=list)
    deck_facts: dict[str, Any] = field(default_factory=dict)

    def reset(self) -> None:
        self.turn = 0
        self.acting_player = self.player
        self.decision_count = 0
        self.prize_counts.clear()
        self.deck_counts.clear()
        self.hand_counts.clear()
        self.active.clear()
        self.bench.clear()
        self.discard.clear()
        self.stadium = None
        self.once_per_turn.clear()
        self.revealed_cards.clear()
        self.previous_logs.clear()
        self.deck_facts.clear()

    def update(self, obs: dict) -> None:
        current = getv(obs, "current", {}) or {}
        features = normalized_features(obs, self.player)
        self.turn = int(features["turn"])
        self.acting_player = int(features["acting_player"])
        self.decision_count += 1
        players = getv(current, "players", []) or []
        for idx in (0, 1):
            pstate = players[idx] if isinstance(players, list) and 0 <= idx < len(players) else {}
            key = str(idx)
            self.prize_counts[key] = len(getv(pstate, "prize", []) or [])
            self.deck_counts[key] = int_or(getv(pstate, "deckCount", 0), 0)
            self.hand_counts[key] = int_or(getv(pstate, "handCount", len(getv(pstate, "hand", []) or [])), 0)
            self.active[key] = summarize_pokemon_list(getv(pstate, "active", []) or [], visible=True)
            self.bench[key] = summarize_pokemon_list(getv(pstate, "bench", []) or [], visible=True)
            self.discard[key] = summarize_cards(getv(pstate, "discard", []) or [])
        self.stadium = summarize_cards(getv(current, "stadium", []) or [])
        self.once_per_turn = {
            "supporterPlayed": bool(getv(current, "supporterPlayed", False)),
            "stadiumPlayed": bool(getv(current, "stadiumPlayed", False)),
            "energyAttached": bool(getv(current, "energyAttached", False)),
            "retreated": bool(getv(current, "retreated", False)),
        }
        logs = getv(obs, "logs", []) or []
        if isinstance(logs, list):
            self.previous_logs.extend(logs[-20:])
            for log in logs:
                cid = getv(log, "cardId")
                if cid is not None:
                    self.revealed_cards[str(cid)] = {"last_log": log}
        self._update_palafin_facts(obs)

    def _update_palafin_facts(self, obs: dict) -> None:
        redacted = redact_hidden_information(obs, self.player)
        current = getv(redacted, "current", {}) or {}
        players = getv(current, "players", []) or []
        own = players[self.player] if isinstance(players, list) and 0 <= self.player < len(players) else {}
        visible = []
        visible.extend(getv(own, "hand", []) or [])
        visible.extend(getv(own, "discard", []) or [])
        for zone in ("active", "bench"):
            visible.extend(getv(own, zone, []) or [])
        palafin_ex_seen = sum(1 for item in visible if card_id(item) == 107)
        self.deck_facts["palafin_ex_seen_by_us"] = palafin_ex_seen
        self.deck_facts["zero_to_hero_completed_visible"] = any(card_id(item) == 107 for item in getv(own, "active", []) + getv(own, "bench", []))
        self.deck_facts["sky_transport_used_flag"] = "Sky Transport" in str(self.previous_logs[-10:])

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def summarize_pokemon_list(items: list[Any], visible: bool) -> list[dict[str, Any]]:
    if not visible:
        return [{} for _ in items]
    rows = []
    for pokemon in items:
        rows.append(
            {
                "card_id": card_id(pokemon),
                "hp": getv(pokemon, "hp"),
                "max_hp": getv(pokemon, "maxHp", getv(pokemon, "maxHP")),
                "energies": summarize_cards(getv(pokemon, "energyCards", []) or getv(pokemon, "energies", []) or []),
                "tools": summarize_cards(getv(pokemon, "tools", []) or []),
                "conditions": {
                    key: bool(getv(pokemon, key, False))
                    for key in ("poisoned", "burned", "asleep", "paralyzed", "confused")
                    if getv(pokemon, key, False)
                },
            }
        )
    return rows


def summarize_cards(items: list[Any]) -> list[Any]:
    return [card_id(item) if item is not None else None for item in items]


def card_id(item: Any) -> int | None:
    if isinstance(item, int):
        return item
    if isinstance(item, dict):
        value = item.get("cardId", item.get("id"))
    else:
        value = getattr(item, "cardId", getattr(item, "id", None))
    try:
        return int(value)
    except Exception:
        return None

