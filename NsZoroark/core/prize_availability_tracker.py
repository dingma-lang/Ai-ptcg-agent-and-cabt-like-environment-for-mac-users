from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from deck_profile import load_deck_ids
from state_eval import (
    active_pokemon,
    bench_pokemon,
    card_id,
    discard_cards,
    getv,
    hand_cards,
    prize_cards,
)
from core.priority_tables import CARD_IDS, canonical_name_from_id


@dataclass(frozen=True)
class CardAvailability:
    card_id: int
    name: str
    total: int
    in_hand: int
    in_play: int
    in_discard: int
    known_prize: int
    searchable: Optional[int]

    @property
    def seen(self) -> int:
        return self.in_hand + self.in_play + self.in_discard + self.known_prize

    @property
    def inferred_missing(self) -> int:
        known_searchable = self.searchable if self.searchable is not None else 0
        return max(0, self.total - self.seen - known_searchable)

    @property
    def unavailable_or_prized(self) -> bool:
        return self.total > 0 and self.searchable == 0 and self.seen < self.total


@dataclass(frozen=True)
class AvailabilityReport:
    cards: Dict[int, CardAvailability]

    def card(self, cid: int) -> CardAvailability:
        return self.cards.get(cid, CardAvailability(cid, canonical_name_from_id(cid), 0, 0, 0, 0, 0, None))

    @property
    def toxel_availability_low(self) -> bool:
        toxel = self.card(CARD_IDS["Toxel"])
        return toxel.unavailable_or_prized and toxel.in_play == 0 and toxel.in_hand == 0

    @property
    def all_deino_in_discard(self) -> bool:
        deino = self.card(CARD_IDS["Deino"])
        return deino.total > 0 and deino.in_discard >= deino.total

    @property
    def rare_candy_unavailable(self) -> bool:
        candy = self.card(CARD_IDS["Rare Candy"])
        return candy.unavailable_or_prized and candy.in_hand == 0

    @property
    def hydreigon_unavailable(self) -> bool:
        hydreigon = self.card(CARD_IDS["Hydreigon ex"])
        return hydreigon.unavailable_or_prized and hydreigon.in_hand == 0 and hydreigon.in_play == 0


def infer_card_availability(state: Any, deck_profile: Any = None) -> AvailabilityReport:
    del deck_profile
    wanted = set(load_deck_ids()) | set(CARD_IDS.values())
    totals: Dict[int, int] = {}
    for cid in load_deck_ids():
        totals[cid] = totals.get(cid, 0) + 1

    searchable_counts = searchable_deck_counts(state)
    cards: Dict[int, CardAvailability] = {}
    for cid in wanted:
        cards[cid] = CardAvailability(
            card_id=cid,
            name=canonical_name_from_id(cid),
            total=totals.get(cid, 0),
            in_hand=count_id(hand_cards(state), cid),
            in_play=count_in_play(state, cid),
            in_discard=count_id(discard_cards(state), cid),
            known_prize=count_id([card for card in prize_cards(state) if card is not None], cid),
            searchable=searchable_counts.get(cid) if searchable_counts is not None else None,
        )
    return AvailabilityReport(cards)


def searchable_deck_counts(state: Any) -> Optional[Dict[int, int]]:
    deck = getv(state.select, "deck")
    if deck is None:
        deck = getv(state.current, "looking")
    if not isinstance(deck, list):
        return None
    counts: Dict[int, int] = {}
    for card in deck:
        cid = card_id(card)
        if cid is not None:
            counts[cid] = counts.get(cid, 0) + 1
    return counts


def count_id(cards: Any, wanted: int) -> int:
    if not isinstance(cards, list):
        return 0
    return sum(1 for card in cards if card_id(card) == wanted)


def count_in_play(state: Any, wanted: int) -> int:
    count = 0
    for pokemon in [active_pokemon(state)] + bench_pokemon(state):
        if card_id(pokemon) == wanted:
            count += 1
    return count
