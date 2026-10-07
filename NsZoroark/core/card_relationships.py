from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, List

from card_db import get_db
from deck_profile import load_deck_ids, load_profile
from core.priority_tables import canonical_name_from_id, card_id_for_name


@dataclass(frozen=True)
class CardRelationship:
    source_card: str
    target_card: str
    relationship_type: str
    condition: str = ""
    priority: int = 0
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_card_relationships(deck_metadata: Any = None) -> List[CardRelationship]:
    del deck_metadata
    relationships: List[CardRelationship] = []

    def rel(source: str, target: str, rel_type: str, priority: int, reason: str, condition: str = "") -> None:
        relationships.append(CardRelationship(source, target, rel_type, condition, priority, reason))

    rel("N's Zorua", "N's Zoroark ex", "evolves_into", 100, "Zoroark ex is the main attacker and copy engine.")
    rel("N's Darumaka", "N's Darmanitan", "evolves_into", 55, "Darmanitan is a secondary N's attack to keep available.")
    rel("N's Zoroark ex", "N's Zekrom", "copies_attack", 95, "Night Joker copies a Benched N's Pokemon's attacks.")
    rel("N's Zoroark ex", "N's Darmanitan", "copies_attack", 60, "Darmanitan can become a situational copied attack.")

    for target in ("N's Zorua", "Tatsugiri", "Budew", "Munkidori"):
        rel("Buddy-Buddy Poffin", target, "searches", 90, f"Poffin can establish {target} if HP is 70 or less.", "Bench has room.")
    rel("Buddy-Buddy Poffin", "N's Zekrom", "should_not_target", -80, "Zekrom is above the Poffin HP limit in local metadata.")

    for target in ("N's Zorua", "N's Darumaka", "N's Darmanitan", "Tatsugiri", "Budew", "Yveltal", "Munkidori"):
        rel("Poke Pad", target, "searches", 70, f"Poké Pad can find non-Rule Box Pokemon such as {target}.")
    rel("Poke Pad", "N's Zoroark ex", "should_not_target", -100, "Zoroark ex has a Rule Box.")

    rel("Ultra Ball", "N's Zoroark ex", "searches", 92, "Ultra Ball finds the main attacker when discard cost is acceptable.")
    rel("Ultra Ball", "N's Zekrom", "searches", 86, "Ultra Ball finds the key copied-attack Bench Pokemon.")
    rel("Cyrano", "N's Zoroark ex", "searches", 78, "Cyrano can find Pokemon ex when the Zoroark line is missing.")
    rel("Cyrano", "N's Zekrom", "searches", 72, "Cyrano can stabilize the N's attack bench.")

    rel("N's PP Up", "Basic Darkness Energy", "recovers_energy", 95, "PP Up attaches Darkness Energy from discard to a Benched N's Pokemon.")
    rel("Basic Darkness Energy", "N's Zoroark ex", "enables_attack", 100, "Night Joker costs Darkness Energy.")
    rel("Basic Darkness Energy", "N's Zekrom", "enables_attack", 80, "Zekrom is the secondary N's attacker.")
    rel("N's Castle", "N's Zoroark ex", "reduces_retreat", 85, "Castle removes retreat cost from N's Pokemon.")
    rel("N's Castle", "N's Zekrom", "reduces_retreat", 78, "Castle lets N's attackers pivot without discarding Energy.")

    for target in ("N's Zoroark ex", "N's Zekrom", "N's PP Up", "N's Castle", "Binding Mochi"):
        rel("Secret Box", target, "finds_piece", 76, "Secret Box can assemble Item, Tool, Supporter, and Stadium packages.", "Discard 3 safe cards.")
    rel("Transformation Tome", "N's Zorua", "transforms_basic", 80, "Tome swaps a Basic in discard with a Basic in play once the cabt ID is available.")

    rel("Boss's Orders", "Opponent Bench", "gust", 88, "Use only when gust creates KO, tempo, or final prize.")
    rel("Black Belt's Training", "Pokemon ex KO", "improves_damage_math", 76, "Damage boost matters against opposing Pokemon ex.")
    rel("Binding Mochi", "N's Zoroark ex", "improves_damage_math", 72, "Mochi boosts poisoned Darkness attackers.")
    rel("Special Red Card", "Opponent Hand", "disruption", 65, "Use when opponent has 3 or fewer prizes and disruption matters.")
    rel("Lillie's Determination", "Hand", "fixes_hand", 70, "Refresh after exact setup actions are checked.")

    protected = ("N's Zorua", "N's Zoroark ex", "N's Zekrom", "N's PP Up", "N's Castle", "Transformation Tome", "Basic Darkness Energy")
    for target in protected:
        rel(target, target, "should_not_discard", -90, f"{target} is protected unless recovery or direct payoff is clear.")

    return relationships


def relationships_to_dicts(relationships: Iterable[CardRelationship]) -> list[dict[str, Any]]:
    return [relationship.to_dict() for relationship in relationships]


def card_hp(name: str) -> int:
    cid = card_id_for_name(name)
    card = get_db().get_card(cid)
    return int(getattr(card, "hp", 0) or 0) if card else 0


def deck_card_names() -> list[str]:
    names = []
    seen = set()
    for cid in load_deck_ids():
        name = canonical_name_from_id(cid)
        if name and name not in seen:
            names.append(name)
            seen.add(name)
    if names:
        return names
    for key in ("setup_priority_names", "main_attackers_names", "secondary_attackers_names", "key_supporters"):
        for name in load_profile().get(key, []) or []:
            if name and name not in seen:
                names.append(str(name))
                seen.add(str(name))
    return names


__all__ = ["CardRelationship", "build_card_relationships", "relationships_to_dicts", "deck_card_names"]
