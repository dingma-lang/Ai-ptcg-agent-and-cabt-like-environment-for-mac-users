from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from state_eval import card_id, getv
from core.priority_tables import CARD_IDS, canonical_name_from_id
from core.prize_availability_tracker import infer_card_availability


@dataclass(frozen=True)
class SearchMemorySnapshot:
    searchable_counts: Dict[int, int]
    prize_suspicions: Dict[str, bool]


WATCH_NAMES = (
    "Deino",
    "Gastly",
    "Toxel",
    "Toxtricity",
    "Hydreigon ex",
    "Mega Gengar ex",
    "Fezandipiti ex",
    "Pecharunt ex",
    "Rare Candy",
    "Basic Darkness Energy",
    "Basic Metal Energy",
    "Basic Psychic Energy",
    "Energy Recycler",
    "Sacred Ash",
    "Night Stretcher",
)


def snapshot_search_memory(state: Any) -> SearchMemorySnapshot:
    deck = getv(state.select, "deck")
    if deck is None:
        deck = getv(state.current, "looking")
    counts: Dict[int, int] = {}
    if isinstance(deck, list):
        for card in deck:
            cid = card_id(card)
            if cid is not None:
                counts[cid] = counts.get(cid, 0) + 1
    report = infer_card_availability(state, None)
    suspicions: Dict[str, bool] = {}
    for name in WATCH_NAMES:
        cid = CARD_IDS.get(name)
        if cid is None:
            continue
        suspicions[name] = report.card(cid).unavailable_or_prized
    return SearchMemorySnapshot(counts, suspicions)


def card_searchable(state: Any, name: str) -> Optional[bool]:
    cid = CARD_IDS.get(name)
    if cid is None:
        return None
    deck = getv(state.select, "deck")
    if deck is None:
        deck = getv(state.current, "looking")
    if not isinstance(deck, list):
        return None
    return any(card_id(card) == cid for card in deck)


def availability_reason(state: Any, name: str) -> str:
    searchable = card_searchable(state, name)
    if searchable is True:
        return f"{name} is visible in current search."
    if searchable is False:
        return f"{name} not visible in current search; lower priority and infer prize/deck unavailability."
    return f"{name} availability unknown."
