from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


DECK_SOURCE = [
    (1, "Zweilous", "SSP", "118"),
    (3, "Deino", "SSP", "117"),
    (3, "Hydreigon ex", "SSP", "240"),
    (1, "Fezandipiti ex", "ASC", "288"),
    (1, "Mega Gengar ex", "ASC", "284"),
    (2, "Toxel", "PFL", "67"),
    (1, "Haunter", "PFL", "55"),
    (2, "Toxtricity", "PFL", "103"),
    (2, "Gastly", "TEF", "177"),
    (1, "Pecharunt ex", "SFA", "93"),
    (1, "Mega Gengar ex", "ASC", "269"),
    (1, "Secret Box", "TWM", "163"),
    (2, "Dawn", "PFL", "87"),
    (2, "Battle Cage", "PFL", "85"),
    (1, "Energy Recycler", "DRI", "164"),
    (2, "Ultra Ball", "ASC", "213"),
    (1, "Special Red Card", "CRI", "82"),
    (3, "Poké Pad", "ASC", "198"),
    (4, "Lillie's Determination", "ASC", "192"),
    (1, "Sacred Ash", "DRI", "168"),
    (1, "Night Stretcher", "MEG", "173"),
    (2, "Crispin", "PRE", "171"),
    (3, "Team Rocket's Petrel", "ASC", "207"),
    (3, "Buddy-Buddy Poffin", "ASC", "184"),
    (2, "Air Balloon", "SSH", "213"),
    (1, "Boss's Orders", "MEG", "114"),
    (3, "Rare Candy", "SVI", "191"),
    (6, "Basic Darkness Energy", "SVE", "15"),
    (2, "Basic Metal Energy", "MEE", "8"),
    (2, "Basic Psychic Energy", "MEE", "5"),
]


# This is intentionally disabled unless --allow-local-placeholder is passed.
# The local CSV/PDF does not contain CRI/Special Red Card yet. Meddling Memo is
# a legal numeric card ID with similar hand-bottoming behavior, but it is not
# identical gameplay text, so the report marks it as a temporary local blocker.
LOCAL_PLACEHOLDERS = {
    ("Special Red Card", "CRI", "82"): 1103,
}

ENERGY_NAME_ALIASES = {
    "basicdarknessenergy": "basicdenergy",
    "basicmetalenergy": "basicmenergy",
    "basicpsychicenergy": "basicpenergy",
    "basicwaterenergy": "basicwenergy",
    "basicfireenergy": "basicrenergy",
    "basicgrassenergy": "basicgenergy",
    "basiclightningenergy": "basiclenergy",
    "basicfightingenergy": "basicfenergy",
}


@dataclass
class MetadataCard:
    card_id: int
    name: str
    expansion: str = ""
    collection_no: str = ""
    stage_type: str = ""
    rule: str = ""
    category: str = ""
    text: str = ""

    @property
    def collection_base(self) -> str:
        first = str(self.collection_no or "").split("/")[0]
        first = first.strip()
        return str(int(first)) if first.isdigit() else first.upper()

    @property
    def normalized_name(self) -> str:
        return canonical_name(self.name)

    def metadata_summary(self) -> str:
        bits = [
            f"name={self.name}",
            f"expansion={self.expansion or '?'}",
            f"number={self.collection_no or '?'}",
            f"type={self.stage_type or '?'}",
        ]
        if self.rule:
            bits.append(f"rule={self.rule}")
        return "; ".join(bits)


@dataclass
class MappingResult:
    quantity: int
    input_name: str
    input_set: str
    input_number: str
    card: Optional[MetadataCard]
    status: str
    note: str


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--deck-out", default="deck.csv")
    parser.add_argument("--report-out", default="deck_mapping_report.md")
    parser.add_argument("--allow-local-placeholder", action="store_true")
    args = parser.parse_args()

    metadata, sources = load_metadata()
    results, errors = resolve_deck(metadata, allow_local_placeholder=args.allow_local_placeholder)
    write_report(args.report_out, results, errors, sources)
    print_mapping_table(results)

    if errors:
        print("\nUNRESOLVED DECK MAPPING ERRORS:")
        for error in errors:
            print(" -", error)
        print(f"\nReport written to {args.report_out}")
        return 1

    deck_ids: List[int] = []
    for result in results:
        if result.card is None:
            continue
        deck_ids.extend([result.card.card_id] * result.quantity)

    if len(deck_ids) != 60:
        print(f"ERROR: resolved deck has {len(deck_ids)} cards, expected 60.")
        return 1

    with open(args.deck_out, "w", encoding="utf-8") as handle:
        for card_id in deck_ids:
            handle.write(f"{card_id}\n")
    print(f"\nWrote {args.deck_out} with {len(deck_ids)} numeric card IDs.")
    print(f"Report written to {args.report_out}")
    return 0


def load_metadata() -> Tuple[List[MetadataCard], List[str]]:
    cards_by_id: Dict[int, MetadataCard] = {}
    sources: List[str] = []

    for card in load_cabt_raw_metadata():
        cards_by_id[card.card_id] = card
    if cards_by_id:
        sources.append("cabt raw AllCard metadata")

    api_cards = load_cabt_api_metadata()
    if api_cards:
        sources.append("cabt all_card_data() metadata")
    for card in api_cards:
        existing = cards_by_id.get(card.card_id)
        cards_by_id[card.card_id] = merge_metadata(existing, card) if existing else card

    csv_cards = load_csv_metadata()
    if csv_cards:
        sources.append("card list and resource/EN_Card_Data.csv")
    for card in csv_cards:
        existing = cards_by_id.get(card.card_id)
        if existing is None:
            cards_by_id[card.card_id] = card
        else:
            cards_by_id[card.card_id] = merge_metadata(existing, card)

    if not cards_by_id:
        raise RuntimeError("No card metadata could be loaded from cabt or CSV.")

    return sorted(cards_by_id.values(), key=lambda card: card.card_id), sources


def load_cabt_raw_metadata() -> List[MetadataCard]:
    root = Path(__file__).resolve().parent
    sample = root / "sample_submission"
    if sample.exists() and str(sample) not in sys.path:
        sys.path.insert(0, str(sample))
    try:
        from cg.sim import lib  # type: ignore

        raw = json.loads(lib.AllCard().decode())
    except Exception:
        return []

    cards = []
    for row in raw:
        try:
            card_id = int(row.get("cardId") or row.get("id"))
        except Exception:
            continue
        cards.append(
            MetadataCard(
                card_id=card_id,
                name=str(row.get("name") or row.get("cardName") or ""),
                expansion=str(row.get("expansion") or row.get("set") or row.get("setCode") or ""),
                collection_no=str(row.get("collectionNo") or row.get("collectorNumber") or row.get("number") or ""),
                stage_type=str(row.get("stage") or row.get("cardType") or ""),
                rule=str(row.get("rule") or ""),
                category=str(row.get("category") or ""),
                text=extract_cabt_text(row),
            )
        )
    return cards


def load_cabt_api_metadata() -> List[MetadataCard]:
    root = Path(__file__).resolve().parent
    sample = root / "sample_submission"
    if sample.exists() and str(sample) not in sys.path:
        sys.path.insert(0, str(sample))
    try:
        from cg.api import all_card_data  # type: ignore
    except Exception:
        return []

    cards = []
    try:
        api_cards = all_card_data()
    except Exception:
        return []
    for card in api_cards:
        try:
            card_id = int(getattr(card, "cardId"))
        except Exception:
            continue
        rule = ""
        if getattr(card, "megaEx", False):
            rule = "Mega Pokemon ex"
        elif getattr(card, "ex", False):
            rule = "Pokemon ex"
        elif getattr(card, "aceSpec", False):
            rule = "ACE SPEC"
        cards.append(
            MetadataCard(
                card_id=card_id,
                name=str(getattr(card, "name", "") or ""),
                stage_type=str(getattr(card, "cardType", "") or ""),
                rule=rule,
                text="\n".join(str(getattr(skill, "text", "") or "") for skill in (getattr(card, "skills", []) or [])),
            )
        )
    return cards


def extract_cabt_text(row: Dict[str, Any]) -> str:
    pieces: List[str] = []
    for key in ("text", "effect", "effectText"):
        if row.get(key):
            pieces.append(str(row[key]))
    for skill in row.get("skills") or []:
        if isinstance(skill, dict) and skill.get("text"):
            pieces.append(str(skill["text"]))
    return "\n".join(pieces)


def load_csv_metadata() -> List[MetadataCard]:
    path = find_csv()
    if path is None:
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))

    by_id: Dict[int, List[Dict[str, str]]] = {}
    for row in rows:
        try:
            by_id.setdefault(int(row.get("Card ID", "")), []).append(row)
        except ValueError:
            continue

    cards = []
    for card_id, card_rows in by_id.items():
        first = card_rows[0]
        text = "\n".join(clean_na(row.get("Effect Explanation", "")) for row in card_rows if clean_na(row.get("Effect Explanation", "")))
        cards.append(
            MetadataCard(
                card_id=card_id,
                name=first.get("Card Name", "") or "",
                expansion=first.get("Expansion", "") or "",
                collection_no=first.get("Collection No.", "") or "",
                stage_type=first.get("Stage (Pokemon)/Type (Energy and Trainer)", "")
                or first.get("Stage (Pokémon)/Type (Energy and Trainer)", ""),
                rule=clean_na(first.get("Rule", "")),
                category=clean_na(first.get("Category", "")),
                text=text,
            )
        )
    return cards


def find_csv() -> Optional[Path]:
    root = Path(__file__).resolve().parent
    candidates = [
        root / "card list and resource" / "EN_Card_Data.csv",
        root / "EN_Card_Data.csv",
        Path(os.getcwd()) / "card list and resource" / "EN_Card_Data.csv",
        Path("/kaggle_simulations/agent/card list and resource/EN_Card_Data.csv"),
        Path("/kaggle_simulations/agent/EN_Card_Data.csv"),
    ]
    return next((path for path in candidates if path.exists()), None)


def merge_metadata(primary: MetadataCard, supplement: MetadataCard) -> MetadataCard:
    return MetadataCard(
        card_id=primary.card_id,
        name=primary.name or supplement.name,
        expansion=primary.expansion or supplement.expansion,
        collection_no=primary.collection_no or supplement.collection_no,
        stage_type=primary.stage_type or supplement.stage_type,
        rule=primary.rule or supplement.rule,
        category=primary.category or supplement.category,
        text=primary.text or supplement.text,
    )


def resolve_deck(metadata: List[MetadataCard], allow_local_placeholder: bool) -> Tuple[List[MappingResult], List[str]]:
    results: List[MappingResult] = []
    errors: List[str] = []
    by_id = {card.card_id: card for card in metadata}

    for quantity, name, set_code, number in DECK_SOURCE:
        result, error = resolve_one(metadata, quantity, name, set_code, number)
        if error and allow_local_placeholder:
            placeholder_id = LOCAL_PLACEHOLDERS.get((name, set_code, number))
            if placeholder_id and placeholder_id in by_id:
                result = MappingResult(
                    quantity=quantity,
                    input_name=name,
                    input_set=set_code,
                    input_number=number,
                    card=by_id[placeholder_id],
                    status="LOCAL PLACEHOLDER",
                    note=(
                        "Exact card is absent from local metadata. This is not an identical gameplay-text "
                        "substitution; replace when cabt metadata includes Special Red Card CRI 82."
                    ),
                )
                error = ""
        results.append(result)
        if error:
            errors.append(error)
    return results, errors


def resolve_one(metadata: List[MetadataCard], quantity: int, name: str, set_code: str, number: str) -> Tuple[MappingResult, str]:
    input_norm = canonical_name(name)
    input_number = normalize_number(number)
    exact = [
        card
        for card in metadata
        if card.normalized_name == input_norm
        and card.expansion.upper() == set_code.upper()
        and normalize_number(card.collection_base) == input_number
    ]
    if len(exact) == 1:
        return MappingResult(quantity, name, set_code, number, exact[0], "EXACT", ""), ""
    if len(exact) > 1:
        return empty_result(quantity, name, set_code, number), f"{name} {set_code} {number} matched multiple exact cards: {card_ids(exact)}"

    same_name = [card for card in metadata if card.normalized_name == input_norm]
    if len(same_name) == 1:
        note = f"Exact set/number {set_code} {number} absent; unique same-name competition card used."
        return MappingResult(quantity, name, set_code, number, same_name[0], "SAME-NAME FALLBACK", note), ""
    if len(same_name) > 1:
        same_set = [card for card in same_name if card.expansion.upper() == set_code.upper()]
        if len(same_set) == 1:
            note = f"Exact collector {number} absent; unique same-name same-set competition card used."
            return MappingResult(quantity, name, set_code, number, same_set[0], "SAME-SET FALLBACK", note), ""
        gameplay_groups = group_by_gameplay(same_name)
        if len(gameplay_groups) == 1:
            chosen = sorted(same_name, key=lambda card: card.card_id)[0]
            note = f"Exact printing absent; all same-name candidates have identical local gameplay text. Candidates: {card_ids(same_name)}."
            return MappingResult(quantity, name, set_code, number, chosen, "GAMEPLAY FALLBACK", note), ""
        return empty_result(quantity, name, set_code, number), f"{name} {set_code} {number} matched multiple non-identical same-name cards: {card_ids(same_name)}"

    alias_norm = ENERGY_NAME_ALIASES.get(input_norm)
    if alias_norm:
        alias_matches = [card for card in metadata if card.normalized_name == alias_norm]
        if len(alias_matches) == 1:
            note = f"Energy export name normalized to competition energy name {alias_matches[0].name}."
            return MappingResult(quantity, name, set_code, number, alias_matches[0], "ENERGY ALIAS", note), ""

    return empty_result(quantity, name, set_code, number), f"{name} {set_code} {number} could not be resolved in available metadata."


def empty_result(quantity: int, name: str, set_code: str, number: str) -> MappingResult:
    return MappingResult(quantity, name, set_code, number, None, "UNRESOLVED", "")


def group_by_gameplay(cards: Iterable[MetadataCard]) -> Dict[str, List[MetadataCard]]:
    groups: Dict[str, List[MetadataCard]] = {}
    for card in cards:
        groups.setdefault(canonical_text(card.text), []).append(card)
    return groups


def card_ids(cards: Iterable[MetadataCard]) -> str:
    return ", ".join(str(card.card_id) for card in cards)


def print_mapping_table(results: List[MappingResult]) -> None:
    print(
        "quantity | input_name | input_set | input_number | competition_id | "
        "resolved_name | resolved_metadata"
    )
    print("-" * 140)
    for result in results:
        card = result.card
        print(
            f"{result.quantity} | {result.input_name} | {result.input_set} | {result.input_number} | "
            f"{card.card_id if card else 'UNRESOLVED'} | {card.name if card else 'UNRESOLVED'} | "
            f"{card.metadata_summary() if card else result.status}"
        )


def write_report(path: str, results: List[MappingResult], errors: List[str], sources: List[str]) -> None:
    lines = [
        "# Deck Mapping Report",
        "",
        "## Metadata Sources",
        "",
    ]
    lines.extend(f"- {source}" for source in sources)
    lines.extend(["", "## Mapping", ""])
    lines.append("| Qty | Input | Requested Set/No. | Status | Competition ID | Resolved | Notes |")
    lines.append("| ---: | --- | --- | --- | ---: | --- | --- |")
    for result in results:
        card = result.card
        lines.append(
            f"| {result.quantity} | {result.input_name} | {result.input_set} {result.input_number} | "
            f"{result.status} | {card.card_id if card else ''} | {card.metadata_summary() if card else ''} | "
            f"{result.note} |"
        )
    lines.extend(["", "## Unresolved / Blockers", ""])
    if errors:
        lines.extend(f"- {error}" for error in errors)
    else:
        local_placeholders = [result for result in results if result.status == "LOCAL PLACEHOLDER"]
        if local_placeholders:
            lines.extend(f"- {result.input_name} uses a local placeholder: {result.note}" for result in local_placeholders)
        else:
            lines.append("- None.")
    lines.append("")
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def canonical_name(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = text.replace("’", "'").replace("`", "'")
    text = text.replace("{D}", "D").replace("{M}", "M").replace("{P}", "P")
    text = text.replace("{W}", "W").replace("{R}", "R").replace("{G}", "G")
    text = text.replace("{L}", "L").replace("{F}", "F")
    text = "".join(ch for ch in text.lower() if ch.isalnum())
    return ENERGY_NAME_ALIASES.get(text, text)


def canonical_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    return re.sub(r"\W+", "", text.lower())


def normalize_number(value: str) -> str:
    text = str(value or "").split("/")[0].strip()
    return str(int(text)) if text.isdigit() else text.upper()


def clean_na(value: Any) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in {"n/a", "nan", "none"} else text


if __name__ == "__main__":
    raise SystemExit(main())
