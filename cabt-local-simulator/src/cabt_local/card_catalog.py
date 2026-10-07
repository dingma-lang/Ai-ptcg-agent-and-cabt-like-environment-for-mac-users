from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

from .engine import CabtUnavailable, get_card_api
from .remote_engine import RemoteCabtMetadata


@dataclass(frozen=True)
class CardRecord:
    card_id: int
    name: str
    card_type: str = ""
    hp: Optional[int] = None
    set_name: str = ""
    collector_number: str = ""
    raw: dict[str, Any] | None = None


class CardCatalog:
    def __init__(self, cards: Iterable[CardRecord], source: str = "unknown") -> None:
        self.cards = sorted(list(cards), key=lambda card: card.card_id)
        self.source = source
        self.by_id = {card.card_id: card for card in self.cards}

    @classmethod
    def from_cabt(cls, cg_path: str | Path | None = None) -> "CardCatalog":
        try:
            api = get_card_api(cg_path)
        except CabtUnavailable:
            api = RemoteCabtMetadata()
        try:
            raw_cards = api.all_card_data()
        except Exception as exc:
            raise CabtUnavailable(f"all_card_data() failed: {exc}") from exc
        return cls([record_from_any(card) for card in raw_cards], source="cabt.all_card_data")

    @classmethod
    def from_csv(cls, path: str | Path) -> "CardCatalog":
        path = Path(path)
        with path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            cards = [record_from_row(row) for row in reader]
        return cls(cards, source=str(path))

    def unsupported_ids(self, ids: Iterable[int]) -> list[int]:
        return sorted({int(cid) for cid in ids if int(cid) not in self.by_id})

    def report_counts(self, ids: Iterable[int]) -> list[dict[str, Any]]:
        counts: dict[int, int] = {}
        for cid in ids:
            counts[int(cid)] = counts.get(int(cid), 0) + 1
        rows = []
        for cid in sorted(counts):
            card = self.by_id.get(cid)
            rows.append(
                {
                    "card_id": cid,
                    "name": card.name if card else "UNSUPPORTED",
                    "count": counts[cid],
                    "card_type": card.card_type if card else "",
                }
            )
        return rows

    def export_json(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"source": self.source, "cards": [asdict(card) for card in self.cards]}
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def export_csv(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["card_id", "name", "card_type", "hp", "set_name", "collector_number"])
            writer.writeheader()
            for card in self.cards:
                writer.writerow(
                    {
                        "card_id": card.card_id,
                        "name": card.name,
                        "card_type": card.card_type,
                        "hp": "" if card.hp is None else card.hp,
                        "set_name": card.set_name,
                        "collector_number": card.collector_number,
                    }
                )
        return path


def record_from_any(card: Any) -> CardRecord:
    data = to_plain_dict(card)
    return CardRecord(
        card_id=int(first_value(data, "cardId", "card_id", "id", default=0)),
        name=str(first_value(data, "name", "cardName", default="")),
        card_type=str(first_value(data, "cardType", "card_type", "type", default="")),
        hp=parse_optional_int(first_value(data, "hp", "HP", default=None)),
        set_name=str(first_value(data, "set", "setName", "expansion", default="")),
        collector_number=str(first_value(data, "collectorNumber", "number", "cardNo", default="")),
        raw=data,
    )


def record_from_row(row: dict[str, Any]) -> CardRecord:
    normalized = {str(k).strip(): v for k, v in row.items()}
    return CardRecord(
        card_id=int(first_value(normalized, "card_id", "cardId", "ID", "id", "Card ID", default=0)),
        name=str(first_value(normalized, "name", "Name", "card_name", "Card Name", default="")),
        card_type=str(first_value(normalized, "card_type", "cardType", "Type", "Card Type", "Stage (Pokémon)/Type (Energy and Trainer)", default="")),
        hp=parse_optional_int(first_value(normalized, "hp", "HP", default=None)),
        set_name=str(first_value(normalized, "set", "Set", "set_name", "Expansion", default="")),
        collector_number=str(first_value(normalized, "collector_number", "Collector Number", "Collection No.", "number", "No", "cardNo", default="")),
        raw=normalized,
    )


def to_plain_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "__dict__"):
        return dict(value.__dict__)
    result: dict[str, Any] = {}
    for name in dir(value):
        if name.startswith("_"):
            continue
        try:
            attr = getattr(value, name)
        except Exception:
            continue
        if not callable(attr):
            result[name] = attr
    return result


def first_value(mapping: dict[str, Any], *keys: str, default: Any = None) -> Any:
    lowered = {str(k).lower(): v for k, v in mapping.items()}
    for key in keys:
        if key in mapping and mapping[key] not in (None, ""):
            return mapping[key]
        value = lowered.get(key.lower())
        if value not in (None, ""):
            return value
    return default


def parse_optional_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except Exception:
        return None


def discover_csv_catalog(start: Path) -> Optional[Path]:
    candidates = list(start.rglob("EN_Card_Data.csv"))
    if not candidates and start.parent.exists():
        candidates = list(start.parent.rglob("EN_Card_Data.csv"))
    return candidates[0] if candidates else None
