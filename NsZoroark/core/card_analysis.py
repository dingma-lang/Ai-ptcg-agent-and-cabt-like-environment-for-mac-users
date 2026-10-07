from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from card_db import CardInfo, get_db
from deck_profile import load_deck_ids, load_profile
from core.card_relationships import build_card_relationships
from core.priority_tables import canonical_name_from_id


ROLE_OPTIONS = [
    "main_attacker",
    "secondary_attacker",
    "setup_basic",
    "evolution_target",
    "search_card",
    "broad_draw",
    "energy_acceleration",
    "energy_recovery",
    "pokemon_recovery",
    "stadium",
    "gust",
    "damage_modifier",
    "ace_spec",
    "support_pokemon",
    "resource_card",
]


@dataclass(frozen=True)
class CardAnalysis:
    card_name: str
    count_in_deck: int = 0
    card_type: str = ""
    stage: str = ""
    rule_box_status: str = ""
    hp: int = 0
    retreat_cost: int = 0
    attack_costs: List[str] = field(default_factory=list)
    attack_damage: List[str] = field(default_factory=list)
    ability_text: str = ""
    effect_text: str = ""
    role: List[str] = field(default_factory=list)
    primary_use: str = ""
    secondary_use: str = ""
    early_game_value: int = 0
    mid_game_value: int = 0
    late_game_value: int = 0
    search_targets: List[str] = field(default_factory=list)
    searched_by: List[str] = field(default_factory=list)
    enables_cards: List[str] = field(default_factory=list)
    enabled_by_cards: List[str] = field(default_factory=list)
    protects_cards: List[str] = field(default_factory=list)
    protected_by_cards: List[str] = field(default_factory=list)
    energy_requirements: str = ""
    switch_synergy: str = ""
    recovery_synergy: str = ""
    discard_priority: str = ""
    protected_priority: str = ""
    when_to_play: str = ""
    when_to_hold: str = ""
    when_not_to_play: str = ""
    common_mistakes: List[str] = field(default_factory=list)
    policy_rules: List[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


BASE_STRATEGY: Dict[str, dict[str, Any]] = {
    "N's Zorua": {
        "role": ["setup_basic"],
        "primary_use": "Required Basic for N's Zoroark ex.",
        "values": (100, 75, 35),
        "when_to_play": "Bench immediately while Bench has space.",
        "discard_priority": "Very protected until at least one Zoroark ex is established.",
        "policy_rules": ["Poffin for N's basics", "Evolve Zorua first"],
    },
    "N's Zoroark ex": {
        "role": ["main_attacker", "evolution_target"],
        "primary_use": "Main attacker and Night Joker copy engine.",
        "values": (70, 100, 95),
        "energy_requirements": "Usually Darkness Energy for Night Joker.",
        "when_to_play": "Evolve legal Zorua before discard-cost Items.",
        "discard_priority": "Do not discard the only copy unless Ultra Ball directly replaces it.",
        "policy_rules": ["Evolve Zorua first", "Keep Zekrom available"],
    },
    "N's Zekrom": {
        "role": ["main_attacker", "support_pokemon"],
        "primary_use": "Bench attacker for Zoroark ex to copy and backup direct attacker.",
        "values": (82, 96, 90),
        "energy_requirements": "Darkness Energy when attacking directly.",
        "when_to_play": "Bench when Zoroark ex is coming online or pressure is needed.",
        "discard_priority": "Protected; Night Joker wants access to its attacks.",
        "policy_rules": ["Keep Zekrom available"],
    },
    "Buddy-Buddy Poffin": {
        "role": ["search_card"],
        "primary_use": "Early Bench fill for Zorua and low-HP support Basics.",
        "values": (100, 45, 15),
        "when_to_play": "Use before Lillie when Bench has space.",
        "when_not_to_play": "Do not waste when Bench is full or targets are exhausted.",
        "policy_rules": ["Poffin for N's basics"],
    },
    "Ultra Ball": {
        "role": ["search_card"],
        "primary_use": "Find Zoroark ex or Zekrom when discard cost is acceptable.",
        "values": (82, 88, 70),
        "discard_priority": "Requires a discard check; protect sole Zoroark/Zorua/Zekrom resources.",
        "policy_rules": ["Evolve Zorua first", "Keep Zekrom available"],
    },
    "Transformation Tome": {
        "role": ["resource_card"],
        "primary_use": "Swap a Basic Pokemon from discard with a Basic in play once cabt ID is available.",
        "values": (50, 88, 86),
        "when_to_hold": "Hold until the discard and board have a real transformation target.",
        "discard_priority": "Protected until the local cabt card ID and prompt behavior are known.",
        "policy_rules": ["Protect Tome"],
    },
    "N's PP Up": {
        "role": ["energy_acceleration"],
        "primary_use": "Attach Darkness Energy from discard to a Benched N's Pokemon.",
        "values": (55, 92, 80),
        "energy_requirements": "Needs Darkness Energy in discard and a useful Benched N's target.",
        "when_to_play": "Use before end turn if it powers Zoroark/Zekrom development.",
        "policy_rules": ["Use N's PP Up"],
    },
    "N's Castle": {
        "role": ["stadium"],
        "primary_use": "Remove retreat costs from N's Pokemon.",
        "values": (65, 80, 72),
        "when_to_play": "Play when retreat flexibility matters or opponent Stadium should be replaced.",
        "discard_priority": "Protected when no Stadium is active.",
    },
    "Lillie's Determination": {
        "role": ["broad_draw"],
        "primary_use": "Refresh weak or clogged hands.",
        "values": (78, 78, 55),
        "when_to_play": "Use after playable Basics, evolutions, Items, and Energy are checked.",
        "policy_rules": ["Lillie for weak hands"],
    },
    "Boss's Orders": {
        "role": ["gust"],
        "primary_use": "Pull a KO target or disrupt a key response.",
        "values": (25, 70, 95),
        "when_not_to_play": "Do not spend without KO, tempo, or prize-route benefit.",
        "policy_rules": ["Boss only for prizes"],
    },
    "Secret Box": {
        "role": ["ace_spec", "search_card"],
        "primary_use": "Find an Item, Tool, Supporter, and Stadium package.",
        "values": (82, 85, 72),
        "discard_priority": "Requires strict discard check before use.",
    },
    "Basic Darkness Energy": {
        "role": ["resource_card"],
        "primary_use": "Attack fuel for Zoroark/Zekrom and PP Up resource.",
        "values": (72, 85, 75),
        "when_to_play": "Attach to the attacker most likely to attack next.",
        "discard_priority": "Can be discarded when N's PP Up converts it into acceleration.",
    },
}


def build_deck_context() -> dict[str, Any]:
    ids = load_deck_ids()
    counts_by_id = Counter(ids)
    counts_by_name: Counter[str] = Counter(canonical_name_from_id(cid) for cid in ids if canonical_name_from_id(cid))
    metadata_by_name: dict[str, CardInfo] = {}
    for cid in counts_by_id:
        card = get_db().get_card(cid)
        name = canonical_name_from_id(cid)
        if card and name:
            metadata_by_name[name] = card
    if not counts_by_name:
        profile = load_profile()
        for name in profile_names(profile):
            counts_by_name[name] += 0
    context: dict[str, Any] = {
        "deck_ids": ids,
        "counts_by_id": counts_by_id,
        "counts_by_name": counts_by_name,
        "metadata_by_name": metadata_by_name,
    }
    context["relationships"] = build_card_relationships(context)
    return context


def build_all_card_analyses(deck_context: Optional[dict[str, Any]] = None) -> dict[str, CardAnalysis]:
    deck_context = deck_context or build_deck_context()
    result = {}
    for name in deck_context["counts_by_name"]:
        if name:
            result[name] = analyze_card(name, deck_context["metadata_by_name"].get(name), deck_context)
    return result


def analyze_card(name: str, metadata: Optional[CardInfo], deck_context: dict[str, Any]) -> CardAnalysis:
    base = BASE_STRATEGY.get(name, {})
    relationships = deck_context.get("relationships", [])
    outgoing = [rel for rel in relationships if rel.source_card == name]
    incoming = [rel for rel in relationships if rel.target_card == name]
    values = base.get("values", (40, 40, 40))
    return CardAnalysis(
        card_name=name,
        count_in_deck=int(deck_context["counts_by_name"].get(name, 0)),
        card_type=str(getattr(metadata, "card_type", "") or ""),
        stage=str(getattr(metadata, "stage", "") or ""),
        rule_box_status=rule_box_status(metadata),
        hp=int(getattr(metadata, "hp", 0) or 0) if metadata else 0,
        retreat_cost=int(getattr(metadata, "retreat_cost", 0) or 0) if metadata else 0,
        attack_costs=attack_costs(metadata),
        attack_damage=attack_damage(metadata),
        ability_text=ability_text(metadata),
        effect_text=effect_text(metadata),
        role=list(base.get("role", ["resource_card"])),
        primary_use=str(base.get("primary_use", "Context-dependent resource.")),
        secondary_use=str(base.get("secondary_use", "")),
        early_game_value=int(values[0]),
        mid_game_value=int(values[1]),
        late_game_value=int(values[2]),
        search_targets=[rel.target_card for rel in outgoing if rel.relationship_type.startswith("search") or rel.relationship_type.startswith("finds")],
        searched_by=[rel.source_card for rel in incoming if rel.relationship_type.startswith("search") or rel.relationship_type.startswith("finds")],
        enables_cards=[rel.target_card for rel in outgoing if rel.priority > 0],
        enabled_by_cards=[rel.source_card for rel in incoming if rel.priority > 0],
        energy_requirements=str(base.get("energy_requirements", "")),
        switch_synergy=str(base.get("switch_synergy", "")),
        recovery_synergy=str(base.get("recovery_synergy", "")),
        discard_priority=str(base.get("discard_priority", "Context dependent.")),
        protected_priority=str(base.get("protected_priority", "")),
        when_to_play=str(base.get("when_to_play", "Use when the legal prompt advances setup, prizes, or resource quality.")),
        when_to_hold=str(base.get("when_to_hold", "")),
        when_not_to_play=str(base.get("when_not_to_play", "")),
        common_mistakes=list(base.get("common_mistakes", [])),
        policy_rules=list(base.get("policy_rules", [])),
    )


def profile_names(profile: dict[str, Any]) -> list[str]:
    names: list[str] = []
    seen = set()
    for key in (
        "setup_priority_names",
        "main_attackers_names",
        "secondary_attackers_names",
        "setup_basics_names",
        "support_pokemon_names",
        "protected_cards_names",
    ):
        for name in profile.get(key, []) or []:
            text = str(name)
            if text and text not in seen:
                names.append(text)
                seen.add(text)
    return names


def analyses_to_dicts(analyses: dict[str, CardAnalysis]) -> list[dict[str, Any]]:
    return [analysis.to_dict() for analysis in analyses.values()]


def render_card_analysis_markdown(analyses: Optional[dict[str, CardAnalysis]] = None) -> str:
    analyses = analyses or build_all_card_analyses()
    lines = [
        "# N's Zoroark Card-By-Card Analysis",
        "",
        "This document is generated from the N's Zoroark ex / N's Zekrom analysis layer.",
        "",
    ]
    for analysis in analyses.values():
        lines.extend(
            [
                f"## {analysis.card_name}",
                "",
                f"Count: {analysis.count_in_deck}",
                f"Card type: {analysis.card_type}",
                f"Main role: {', '.join(analysis.role) or 'resource'}",
                f"Best stage of game: {best_stage(analysis)}",
                f"What this card enables: {', '.join(analysis.enables_cards) or analysis.primary_use}",
                f"What enables this card: {', '.join(analysis.enabled_by_cards) or 'Natural draw/search sequencing.'}",
                f"Searchable by: {', '.join(analysis.searched_by) or 'Natural draw only.'}",
                f"Searches: {', '.join(analysis.search_targets) or 'None.'}",
                f"Energy use: {analysis.energy_requirements or 'No Energy requirement.'}",
                f"Discard priority: {analysis.discard_priority}",
                f"When to play: {analysis.when_to_play}",
                f"When to hold: {analysis.when_to_hold or 'Context dependent.'}",
                f"When not to play: {analysis.when_not_to_play or 'Context dependent.'}",
                f"Policy rule: {', '.join(analysis.policy_rules) or 'Use normal legality and tactical score.'}",
                "",
            ]
        )
    return "\n".join(lines)


def best_stage(analysis: CardAnalysis) -> str:
    values = {
        "early": analysis.early_game_value,
        "mid": analysis.mid_game_value,
        "late": analysis.late_game_value,
    }
    return max(values, key=values.get)


def rule_box_status(card: Any) -> str:
    if not card:
        return ""
    if getattr(card, "mega_ex", False):
        return "Mega Pokemon ex"
    if getattr(card, "ex", False):
        return "Pokemon ex"
    if getattr(card, "ace_spec", False):
        return "ACE SPEC"
    rule = str(getattr(card, "rule", "") or "")
    return "" if rule.lower() == "n/a" else rule


def attack_costs(card: Any) -> list[str]:
    if not card:
        return []
    return ["/".join(str(part) for part in getattr(attack, "cost", ()) or ()) for attack in getattr(card, "attacks", ()) or ()]


def attack_damage(card: Any) -> list[str]:
    if not card:
        return []
    values = []
    for attack in getattr(card, "attacks", ()) or ():
        damage = str(getattr(attack, "damage_text", "") or getattr(attack, "damage", "") or "")
        values.append(damage)
    return values


def ability_text(card: Any) -> str:
    if not card:
        return ""
    pieces = []
    for skill in getattr(card, "skills", ()) or ():
        pieces.append(str(getattr(skill, "text", "") or ""))
    for attack in getattr(card, "attacks", ()) or ():
        name = str(getattr(attack, "name", "") or "")
        text = str(getattr(attack, "text", "") or "")
        if name.startswith("[Ability]") or "once during your turn" in text.lower():
            pieces.append(text)
    return " ".join(piece for piece in pieces if piece)


def effect_text(card: Any) -> str:
    if not card:
        return ""
    pieces = [str(getattr(card, "text", "") or "")]
    for attack in getattr(card, "attacks", ()) or ():
        name = str(getattr(attack, "name", "") or "")
        text = str(getattr(attack, "text", "") or "")
        if text and not name.startswith("[Ability]"):
            pieces.append(text)
    return " ".join(piece for piece in pieces if piece)


__all__ = [
    "CardAnalysis",
    "ROLE_OPTIONS",
    "analyze_card",
    "build_deck_context",
    "build_all_card_analyses",
    "analyses_to_dicts",
    "render_card_analysis_markdown",
]
