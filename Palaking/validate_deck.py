from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import List, Tuple

from card_db import get_db


def read_deck(path: str = "deck.csv") -> List[int]:
    with open(path, "r", encoding="utf-8") as handle:
        return [int(line.strip()) for line in handle if line.strip()]


def validate_deck(path: str = "deck.csv") -> Tuple[List[str], List[str]]:
    db = get_db()
    deck_path = Path(path)
    errors: List[str] = []
    warnings: List[str] = []

    if not deck_path.exists():
        return [f"Deck file not found: {path}"], warnings

    try:
        deck = read_deck(path)
    except Exception as exc:
        return [f"Could not read deck: {exc}"], warnings

    if len(deck) != 60:
        errors.append(f"Deck must contain exactly 60 cards; found {len(deck)}.")

    unknown = [cid for cid in deck if db.get_card(cid) is None]
    if unknown:
        errors.append("Unknown card IDs: " + ", ".join(str(cid) for cid in sorted(set(unknown))))

    ace_spec_count = sum(1 for cid in deck if (db.get_card(cid) and db.get_card(cid).ace_spec))
    if ace_spec_count > 1:
        errors.append(f"Deck has {ace_spec_count} ACE SPEC cards; maximum is 1.")

    name_counts = Counter()
    for cid in deck:
        card = db.get_card(cid)
        if card is None or card.card_type == "Basic Energy":
            continue
        name_counts[card.name] += 1
    too_many = [(name, count) for name, count in name_counts.items() if count > 4]
    for name, count in sorted(too_many):
        errors.append(f"Deck has {count} copies of {name}; maximum is 4 by name.")

    basics = [cid for cid in deck if (db.get_card(cid) and db.get_card(cid).basic)]
    if not basics:
        errors.append("Deck must contain at least one Basic Pokemon.")
    elif len(basics) < 6:
        warnings.append(f"Only {len(basics)} Basic Pokemon found; setup consistency may be poor.")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("deck", nargs="?", default="deck.csv")
    args = parser.parse_args()

    errors, warnings = validate_deck(args.deck)
    for warning in warnings:
        print("WARNING:", warning)
    for error in errors:
        print("ERROR:", error)
    if errors:
        return 1
    print(f"OK: {args.deck} is a 60-card legal-looking deck.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
