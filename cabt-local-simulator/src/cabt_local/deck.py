from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from .card_catalog import CardCatalog


class DeckError(ValueError):
    pass


@dataclass(frozen=True)
class DeckReport:
    path: str
    card_count: int
    valid_size: bool
    unsupported_ids: list[int]
    rows: list[dict]


def load_deck(path: str | Path) -> list[int]:
    path = Path(path)
    if not path.exists():
        raise DeckError(f"Deck file does not exist: {path}")
    ids: list[int] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        text = raw.strip()
        if not text or text.startswith("#"):
            continue
        if "," in text:
            text = text.split(",", 1)[0].strip()
        try:
            ids.append(int(text))
        except ValueError as exc:
            raise DeckError(f"{path}:{line_no}: expected numeric cabt card ID, got {raw!r}") from exc
    return ids


def validate_deck(ids: Iterable[int], catalog: Optional[CardCatalog] = None, require_60: bool = True) -> list[str]:
    deck = [int(cid) for cid in ids]
    errors: list[str] = []
    if require_60 and len(deck) != 60:
        errors.append(f"Deck must contain exactly 60 IDs; found {len(deck)}.")
    if any(cid <= 0 for cid in deck):
        errors.append("Deck contains non-positive card IDs.")
    if catalog is not None:
        unsupported = catalog.unsupported_ids(deck)
        if unsupported:
            errors.append("Unsupported card IDs: " + ", ".join(str(cid) for cid in unsupported))
    return errors


def deck_report(path: str | Path, catalog: Optional[CardCatalog] = None) -> DeckReport:
    ids = load_deck(path)
    unsupported = catalog.unsupported_ids(ids) if catalog else []
    rows = catalog.report_counts(ids) if catalog else [{"card_id": cid, "name": "", "count": count} for cid, count in sorted(counts(ids).items())]
    return DeckReport(str(path), len(ids), len(ids) == 60, unsupported, rows)


def counts(ids: Iterable[int]) -> dict[int, int]:
    result: dict[int, int] = {}
    for cid in ids:
        result[int(cid)] = result.get(int(cid), 0) + 1
    return result


def write_deck(ids: Iterable[int], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(str(int(cid)) for cid in ids) + "\n", encoding="utf-8")
    return path


@dataclass(frozen=True)
class ConversionIssue:
    line: str
    reason: str


@dataclass(frozen=True)
class ConversionReport:
    output_path: str
    converted_count: int
    issues: list[ConversionIssue]


DECK_LINE_RE = re.compile(r"^\s*(?P<count>\d+)\s+(?P<name>.+?)\s+(?P<set>[A-Z0-9-]+)\s+(?P<number>[A-Za-z0-9-]+)\s*$")


def convert_ptcglive_text(input_path: str | Path, output_path: str | Path, catalog: CardCatalog) -> ConversionReport:
    ids: list[int] = []
    issues: list[ConversionIssue] = []
    for raw in Path(input_path).read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.endswith(":") or line.lower().startswith("total cards"):
            continue
        match = DECK_LINE_RE.match(line)
        if not match:
            issues.append(ConversionIssue(line, "not a recognized PTCG Live deck line"))
            continue
        count = int(match.group("count"))
        name = normalize_name(match.group("name"))
        set_name = match.group("set").upper()
        number = match.group("number").upper()
        matches = [
            card
            for card in catalog.cards
            if normalize_name(card.name) == name
            and (not card.set_name or card.set_name.upper() == set_name)
            and (not card.collector_number or str(card.collector_number).upper() == number)
        ]
        if len(matches) != 1:
            reason = "unsupported" if not matches else f"ambiguous ({len(matches)} matches)"
            issues.append(ConversionIssue(line, reason))
            continue
        ids.extend([matches[0].card_id] * count)
    if not issues and len(ids) == 60:
        write_deck(ids, output_path)
    return ConversionReport(str(output_path), len(ids), issues)


def normalize_name(value: str) -> str:
    return value.replace("{W}", "Water").replace("{L}", "Lightning").replace("’", "'").strip().lower()

