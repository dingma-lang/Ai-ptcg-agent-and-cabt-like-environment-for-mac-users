from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, List, Optional

from card_db import get_db
from deck_profile import load_deck_ids
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

    dratini_hp = card_hp("Dratini")
    poffin_dratini_reason = "Dratini has more than 70 HP in local competition metadata." if dratini_hp > 70 else "Dratini is Poffin-eligible in this metadata."

    rel("Finizen", "Palafin", "evolves_into", 100, "Finizen must become Palafin before Zero to Hero.")
    rel("Palafin", "Palafin ex", "enables_zero_to_hero", 100, "Moving Palafin from Active to Bench puts Palafin ex into play.")
    rel("Dratini", "Dragonair", "evolves_into", 80, "Dratini is the Basic for Dragonair.")
    rel("Dragonair", "Mega Dragonite ex", "evolves_into", 90, "Dragonair becomes the switch engine and late closer.")

    rel("Buddy-Buddy Poffin", "Finizen", "searches", 100, "Finizen is the required Basic for the Palafin ex engine.", "Bench has room and Finizen count is low.")
    rel("Buddy-Buddy Poffin", "Tatsugiri", "searches", 75, "Tatsugiri provides Supporter access and pivot value.", "Bench has room and support access is needed.")
    if dratini_hp > 70:
        rel("Buddy-Buddy Poffin", "Dratini", "should_not_target", -100, poffin_dratini_reason)
    else:
        rel("Buddy-Buddy Poffin", "Dratini", "searches", 45, poffin_dratini_reason)

    for target in ("Finizen", "Palafin", "Dragonair", "Tatsugiri"):
        rel("Poke Pad", target, "searches", 78 if target == "Palafin" else 65, f"Poke Pad can find non-Rule Box Pokemon such as {target}.")
    rel("Poke Pad", "Dratini", "finds_evolution_piece", 72, "Poke Pad is the route to Dratini because Dratini is not Poffin-eligible when HP is 80.")
    rel("Poke Pad", "Palafin ex", "should_not_target", -100, "Palafin ex has a Rule Box and should stay in deck for Zero to Hero.")
    rel("Poke Pad", "Mega Dragonite ex", "should_not_target", -80, "Mega Dragonite ex has a Rule Box; use Hilda/Dragonair style evolution search instead.")

    rel("Hilda", "Palafin", "finds_evolution_piece", 88, "Hilda can find Palafin when Finizen is ready.")
    rel("Hilda", "Basic Water Energy", "provides_energy", 84, "Hilda can pair Palafin with Water Energy.")
    rel("Hilda", "Dragonair", "finds_evolution_piece", 82, "Hilda can find Dragonair when Dratini is in play.")
    rel("Hilda", "Mega Dragonite ex", "finds_evolution_piece", 88, "Hilda can find Mega Dragonite ex when Dragonair is ready.")
    rel("Hilda", "Basic Lightning Energy", "provides_energy", 86, "Hilda can pair Dragonite line evolution with Lightning Energy.")

    trainer_targets = [
        "Buddy-Buddy Poffin",
        "Poke Pad",
        "Surfing Beach",
        "Switch",
        "Secret Box",
        "Air Balloon",
        "Energy Retrieval",
        "Night Stretcher",
        "Sacred Ash",
        "Boss's Orders",
        "Kieran",
    ]
    for target in trainer_targets:
        rel("Team Rocket's Petrel", target, "finds_exact_trainer", 82, f"Petrel can get exact Trainer {target} when that card solves the turn.")
    rel("Team Rocket's Petrel", "Buddy-Buddy Poffin", "should_not_target", -40, "Do not Petrel for Poffin when Poffin is already in hand.")

    for target, rel_type in (
        ("Buddy-Buddy Poffin", "finds_exact_trainer"),
        ("Poke Pad", "finds_exact_trainer"),
        ("Switch", "finds_exact_trainer"),
        ("Air Balloon", "finds_tool"),
        ("Hilda", "finds_supporter"),
        ("Lillie's Determination", "finds_supporter"),
        ("Team Rocket's Petrel", "finds_supporter"),
        ("Crispin", "finds_supporter"),
        ("Surfing Beach", "finds_stadium"),
    ):
        rel("Secret Box", target, rel_type, 76, "Secret Box builds Item + Tool + Supporter + Stadium setup packages.", "Discard 3 safe cards.")

    for source in ("Surfing Beach", "Switch", "Kieran", "Air Balloon", "Mega Dragonite ex"):
        rel(source, "Palafin", "enables_zero_to_hero", 100 if source == "Surfing Beach" else 88, f"{source} moves Palafin from Active to Bench.")
        rel(source, "Palafin ex", "resets_attack_restriction", 92, f"{source} helps reset or rotate after Giga Impact.")
    rel("Kieran", "Palafin ex", "improves_damage_math", 70, "Kieran's +30 mode matters only when it changes KO math.")

    rel("Basic Water Energy", "Palafin ex", "enables_attack", 100, "Palafin ex attacks for one Water Energy.")
    rel("Basic Water Energy", "Mega Dragonite ex", "enables_attack", 55, "Mega Dragonite also needs Water for its attack.")
    rel("Basic Lightning Energy", "Mega Dragonite ex", "enables_attack", 100, "Mega Dragonite needs scarce Lightning Energy.")
    rel("Basic Lightning Energy", "Palafin ex", "should_not_target", -100, "Lightning Energy is protected for Mega Dragonite ex.")
    rel("Crispin", "Mega Dragonite ex", "provides_energy", 90, "Crispin fixes Water + Lightning for Mega Dragonite ex.")
    rel("Crispin", "Palafin ex", "provides_energy", 40, "Crispin can provide Water, but Palafin usually needs only one manual Water.")
    rel("Energy Retrieval", "Basic Water Energy", "recovers_energy", 70, "Energy Retrieval recovers Palafin attack fuel.")
    rel("Energy Retrieval", "Basic Lightning Energy", "recovers_energy", 78, "Energy Retrieval recovers scarce Dragonite Energy.")
    rel("Night Stretcher", "Palafin", "recovers_pokemon", 70, "Night Stretcher gets exact missing Pokemon or Basic Energy from discard.")
    rel("Night Stretcher", "Basic Lightning Energy", "recovers_energy", 75, "Night Stretcher can recover exact Lightning Energy.")
    for target in ("Finizen", "Palafin", "Palafin ex", "Dratini", "Dragonair", "Mega Dragonite ex"):
        rel("Sacred Ash", target, "recovers_pokemon", 68, "Sacred Ash restores lost Pokemon lines when several pieces are in discard.")

    rel("Boss's Orders", "Palafin ex", "improves_damage_math", 86, "Boss enables Palafin ex to take prize-route KOs.")
    rel("Boss's Orders", "Mega Dragonite ex", "improves_damage_math", 82, "Boss enables Mega Dragonite ex to close on high-HP targets.")
    rel("Lillie's Determination", "Hand", "fixes_hand", 65, "Lillie refreshes weak hands after exact setup actions are used.")

    protected = ("Palafin ex", "Mega Dragonite ex", "Finizen", "Palafin", "Dratini", "Dragonair", "Basic Lightning Energy", "Surfing Beach")
    for target in protected:
        rel(target, target, "should_not_discard", -90, f"{target} is protected unless recovery or payoff is clear.")

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
    return names


__all__ = ["CardRelationship", "build_card_relationships", "relationships_to_dicts", "deck_card_names"]
