from __future__ import annotations

import csv
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class SkillInfo:
    name: str = ""
    text: str = ""


@dataclass(frozen=True)
class AttackInfo:
    attack_id: int
    name: str = ""
    text: str = ""
    damage: int = 0
    damage_text: str = ""
    cost: tuple = field(default_factory=tuple)


@dataclass(frozen=True)
class CardInfo:
    card_id: int
    name: str = ""
    card_type: str = ""
    stage: str = ""
    rule: str = ""
    category: str = ""
    text: str = ""
    hp: int = 0
    retreat_cost: int = 0
    weakness: str = ""
    resistance: str = ""
    energy_type: str = ""
    basic: bool = False
    stage1: bool = False
    stage2: bool = False
    ex: bool = False
    mega_ex: bool = False
    tera: bool = False
    ace_spec: bool = False
    evolves_from: Optional[str] = None
    skills: tuple = field(default_factory=tuple)
    attacks: tuple = field(default_factory=tuple)

    @property
    def prize_value(self) -> int:
        if self.mega_ex:
            return 3
        if self.ex:
            return 2
        return 1


class CardDB:
    def __init__(self) -> None:
        self.cards: Dict[int, CardInfo] = {}
        self.attacks: Dict[int, AttackInfo] = {}
        self.source = "empty"

    def get_card(self, card_id: Any) -> Optional[CardInfo]:
        try:
            return self.cards.get(int(card_id))
        except (TypeError, ValueError):
            return None

    def get_attack(self, attack_id: Any) -> Optional[AttackInfo]:
        try:
            return self.attacks.get(int(attack_id))
        except (TypeError, ValueError):
            return None

    def card_name(self, card_id: Any) -> str:
        card = self.get_card(card_id)
        return card.name if card else str(card_id)

    def is_energy(self, card_id: Any) -> bool:
        card = self.get_card(card_id)
        return bool(card and "Energy" in card.card_type)

    def is_basic_energy(self, card_id: Any) -> bool:
        card = self.get_card(card_id)
        return bool(card and card.card_type == "Basic Energy")

    def is_pokemon(self, card_id: Any) -> bool:
        card = self.get_card(card_id)
        return bool(card and card.card_type == "Pokemon")

    def load(self) -> "CardDB":
        if self.cards:
            return self
        if self._load_from_cg():
            return self
        self._load_from_csv()
        return self

    def _load_from_cg(self) -> bool:
        try:
            root = Path(__file__).resolve().parent
            sample = root / "sample_submission"
            if sample.exists() and str(sample) not in sys.path:
                sys.path.insert(0, str(sample))
            from cg.api import all_attack, all_card_data  # type: ignore

            attack_map: Dict[int, AttackInfo] = {}
            for attack in all_attack():
                info = AttackInfo(
                    attack_id=int(getattr(attack, "attackId")),
                    name=str(getattr(attack, "name", "") or ""),
                    text=str(getattr(attack, "text", "") or ""),
                    damage=int(getattr(attack, "damage", 0) or 0),
                    damage_text=str(getattr(attack, "damage", 0) or ""),
                    cost=tuple(_energy_label(e) for e in (getattr(attack, "energies", None) or [])),
                )
                attack_map[info.attack_id] = info

            cards: Dict[int, CardInfo] = {}
            for card in all_card_data():
                card_id = int(getattr(card, "cardId"))
                attack_ids = tuple(int(a) for a in (getattr(card, "attacks", None) or []))
                skills = tuple(
                    SkillInfo(str(getattr(s, "name", "") or ""), str(getattr(s, "text", "") or ""))
                    for s in (getattr(card, "skills", None) or [])
                )
                card_type = _cg_card_type_label(getattr(card, "cardType", None))
                stage = _stage_from_cg(card)
                rule = "Mega Pokemon ex" if getattr(card, "megaEx", False) else (
                    "Pokemon ex" if getattr(card, "ex", False) else ("ACE SPEC" if getattr(card, "aceSpec", False) else "")
                )
                info = CardInfo(
                    card_id=card_id,
                    name=str(getattr(card, "name", "") or ""),
                    card_type=card_type,
                    stage=stage,
                    rule=rule,
                    text=" ".join(s.text for s in skills if s.text),
                    hp=int(getattr(card, "hp", 0) or 0),
                    retreat_cost=int(getattr(card, "retreatCost", 0) or 0),
                    weakness=_energy_label(getattr(card, "weakness", None)),
                    resistance=_energy_label(getattr(card, "resistance", None)),
                    energy_type=_energy_label(getattr(card, "energyType", None)),
                    basic=bool(getattr(card, "basic", False)),
                    stage1=bool(getattr(card, "stage1", False)),
                    stage2=bool(getattr(card, "stage2", False)),
                    ex=bool(getattr(card, "ex", False)),
                    mega_ex=bool(getattr(card, "megaEx", False)),
                    tera=bool(getattr(card, "tera", False)),
                    ace_spec=bool(getattr(card, "aceSpec", False)),
                    evolves_from=getattr(card, "evolvesFrom", None),
                    skills=skills,
                    attacks=tuple(attack_map[a] for a in attack_ids if a in attack_map),
                )
                cards[card_id] = info

            if cards:
                self.cards = cards
                self.attacks = attack_map
                self.source = "cg.api"
                return True
        except Exception:
            return False
        return False

    def _load_from_csv(self) -> bool:
        path = _find_card_csv()
        if path is None:
            self.source = "missing"
            return False

        with path.open(newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
        if not rows:
            self.source = "empty-csv"
            return False

        stage_key = _first_key(rows[0], ("Stage", "Type (Energy"))
        by_id: Dict[int, List[Dict[str, str]]] = {}
        for row in rows:
            try:
                by_id.setdefault(int(row.get("Card ID", "") or 0), []).append(row)
            except ValueError:
                continue

        cards: Dict[int, CardInfo] = {}
        attacks: Dict[int, AttackInfo] = {}
        for card_id, card_rows in by_id.items():
            first = card_rows[0]
            stage = (first.get(stage_key, "") if stage_key else "") or ""
            rule = first.get("Rule", "") or ""
            hp = _to_int(first.get("HP"))
            retreat = _to_int(first.get("Retreat"))
            attack_infos: List[AttackInfo] = []
            for order, row in enumerate(card_rows, start=1):
                move_name = _clean_na(row.get("Move Name", ""))
                if not move_name:
                    continue
                attack_id = card_id * 100 + order
                attack = AttackInfo(
                    attack_id=attack_id,
                    name=move_name,
                    text=_clean_na(row.get("Effect Explanation", "")),
                    damage=_parse_damage(row.get("Damage", "")),
                    damage_text=_clean_na(row.get("Damage", "")),
                    cost=tuple(_parse_cost(row.get("Cost", ""))),
                )
                attack_infos.append(attack)
                attacks[attack_id] = attack

            card_type = _normalize_card_type(stage)
            ex = "ex" in rule.lower()
            mega_ex = "mega" in rule.lower() and "ex" in rule.lower()
            info = CardInfo(
                card_id=card_id,
                name=first.get("Card Name", "") or "",
                card_type=card_type,
                stage=stage,
                rule=rule,
                category=first.get("Category", "") or "",
                text=_clean_na(first.get("Effect Explanation", "")),
                hp=hp,
                retreat_cost=retreat,
                weakness=_clean_na(first.get("Weakness", "")),
                resistance=_clean_na(first.get("Resistance (Type)", "")),
                energy_type=_clean_na(first.get("Type", "")),
                basic=stage.startswith("Basic") and "Pok" in stage,
                stage1=stage.startswith("Stage 1"),
                stage2=stage.startswith("Stage 2"),
                ex=ex,
                mega_ex=mega_ex,
                tera="Tera" in (first.get("Category", "") or ""),
                ace_spec="ACE SPEC" in rule,
                evolves_from=_clean_na(first.get("Previous stage", "")) or None,
                attacks=tuple(attack_infos),
            )
            cards[card_id] = info

        self.cards = cards
        self.attacks = attacks
        self.source = str(path)
        return True


_DB: Optional[CardDB] = None


def get_db() -> CardDB:
    global _DB
    if _DB is None:
        _DB = CardDB().load()
    return _DB


def _find_card_csv() -> Optional[Path]:
    root = Path(__file__).resolve().parent
    candidates = [
        root / "EN_Card_Data.csv",
        root / "card list and resource" / "EN_Card_Data.csv",
        root / "sample_submission" / "EN_Card_Data.csv",
        Path(os.getcwd()) / "EN_Card_Data.csv",
        Path(os.getcwd()) / "card list and resource" / "EN_Card_Data.csv",
        Path("/kaggle_simulations/agent/EN_Card_Data.csv"),
        Path("/kaggle_simulations/agent/card list and resource/EN_Card_Data.csv"),
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def _first_key(row: Dict[str, str], needles: Iterable[str]) -> str:
    for key in row.keys():
        if all(needle in key for needle in needles):
            return key
    return ""


def _clean_na(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() in ("n/a", "nan", "none") else text


def _to_int(value: Any) -> int:
    text = _clean_na(value)
    if not text:
        return 0
    match = re.search(r"\d+", text)
    return int(match.group(0)) if match else 0


def _parse_damage(value: Any) -> int:
    text = _clean_na(value)
    if not text:
        return 0
    match = re.search(r"\d+", text)
    return int(match.group(0)) if match else 0


def _parse_cost(value: Any) -> List[str]:
    text = _clean_na(value)
    if not text:
        return []
    tokens = re.findall(r"\{([^}]+)\}", text)
    tokens.extend(["C"] * text.count("●"))
    return tokens


def _normalize_card_type(stage: str) -> str:
    if "Basic Energy" in stage:
        return "Basic Energy"
    if "Special Energy" in stage:
        return "Special Energy"
    if "Supporter" in stage:
        return "Supporter"
    if "Stadium" in stage:
        return "Stadium"
    if "Tool" in stage:
        return "Tool"
    if "Item" in stage:
        return "Item"
    if "Pok" in stage:
        return "Pokemon"
    return stage or "Unknown"


def _cg_card_type_label(value: Any) -> str:
    raw = _enum_int(value)
    return {
        0: "Pokemon",
        1: "Item",
        2: "Tool",
        3: "Supporter",
        4: "Stadium",
        5: "Basic Energy",
        6: "Special Energy",
    }.get(raw, str(getattr(value, "name", value) or "Unknown"))


def _stage_from_cg(card: Any) -> str:
    if getattr(card, "basic", False):
        return "Basic Pokemon"
    if getattr(card, "stage1", False):
        return "Stage 1 Pokemon"
    if getattr(card, "stage2", False):
        return "Stage 2 Pokemon"
    return _cg_card_type_label(getattr(card, "cardType", None))


def _enum_int(value: Any) -> int:
    if value is None:
        return -1
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(getattr(value, "value", -1))


def _energy_label(value: Any) -> str:
    raw = _enum_int(value)
    labels = {
        0: "C",
        1: "G",
        2: "R",
        3: "W",
        4: "L",
        5: "P",
        6: "F",
        7: "D",
        8: "M",
        9: "Dragon",
        10: "Rainbow",
        11: "Team Rocket",
    }
    return labels.get(raw, "" if value is None else str(value))
