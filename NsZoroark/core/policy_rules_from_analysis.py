from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, List

from core.card_analysis import CardAnalysis, build_all_card_analyses
from core.card_relationships import CardRelationship, build_card_relationships


@dataclass(frozen=True)
class PolicyRule:
    rule_name: str
    condition: List[str]
    action_preference: str
    priority: int
    reason: str
    forbidden_actions: List[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def generate_policy_rules_from_card_analysis(
    card_analyses: dict[str, CardAnalysis] | Iterable[CardAnalysis] | None = None,
    relationships: Iterable[CardRelationship] | None = None,
) -> List[PolicyRule]:
    analyses = normalize_analyses(card_analyses or build_all_card_analyses())
    rels = list(relationships or build_card_relationships())
    del analyses, rels

    return [
        PolicyRule(
            "Poffin for N's basics",
            ["Buddy-Buddy Poffin in hand", "Bench not full", "N's Zorua or support Basic needed"],
            "Play Buddy-Buddy Poffin before broad hand refresh.",
            6500,
            "Zoroark needs early Zorua density and Bench attackers for Night Joker.",
            ["Play Lillie's Determination before Poffin when Bench is empty"],
        ),
        PolicyRule(
            "Evolve Zorua first",
            ["N's Zorua in play", "N's Zoroark ex in hand", "evolution legal"],
            "Evolve into N's Zoroark ex before discard-cost Items.",
            7200,
            "Zoroark ex is the deck's main attacker and copy engine.",
            ["Discard the only Zoroark ex", "Shuffle away a live Zoroark evolution"],
        ),
        PolicyRule(
            "Keep Zekrom available",
            ["N's Zoroark ex can copy attacks", "N's Zekrom visible or searchable"],
            "Keep N's Zekrom in play or accessible.",
            6100,
            "Zoroark ex needs strong N's attacks available from the Bench.",
            ["Discard all Zekrom access without payoff"],
        ),
        PolicyRule(
            "Use N's PP Up",
            ["Darkness Energy in discard", "Benched N's attacker needs Energy", "N's PP Up legal"],
            "Attach Darkness Energy from discard to the best Benched N's attacker.",
            6400,
            "PP Up turns discard costs into acceleration.",
            ["End turn with legal PP Up acceleration"],
        ),
        PolicyRule(
            "Protect Tome",
            ["Transformation Tome in hand", "Tome line not ready"],
            "Hold Transformation Tome until it creates a real Basic swap line.",
            5000,
            "Transformation Tome is a specialized resource, not discard fodder by default.",
            ["Discard Tome casually for Ultra Ball or Secret Box"],
        ),
        PolicyRule(
            "Boss only for prizes",
            ["Boss's Orders legal"],
            "Use Boss only when it creates a KO, blocks opponent setup, or improves the prize route.",
            5600,
            "Gust should convert into prizes or tempo.",
            ["Use Boss without KO or tempo value"],
        ),
        PolicyRule(
            "Lillie for weak hands",
            ["Supporter unused", "hand is weak or clogged"],
            "Use Lillie's Determination after playable Basics, evolutions, and useful Items are checked.",
            5200,
            "Lillie refreshes the hand but can shuffle away usable board progress.",
            ["Lillie before benching a playable Basic", "Lillie before legal Zoroark evolution"],
        ),
    ]


def normalize_analyses(card_analyses: dict[str, CardAnalysis] | Iterable[CardAnalysis]) -> dict[str, CardAnalysis]:
    if isinstance(card_analyses, dict):
        return card_analyses
    return {analysis.card_name: analysis for analysis in card_analyses}


def rules_to_dicts(rules: Iterable[PolicyRule]) -> list[dict[str, Any]]:
    return [rule.to_dict() for rule in rules]


__all__ = ["PolicyRule", "generate_policy_rules_from_card_analysis", "rules_to_dicts"]
