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
    del rels

    rules = [
        PolicyRule(
            "Poffin before Lillie",
            ["Buddy-Buddy Poffin in hand", "Bench not full", "Finizen count < 2"],
            "Play Buddy-Buddy Poffin.",
            6500,
            "Poffin searches Finizen/Tatsugiri and should establish the Bench before broad refresh.",
            ["Play Lillie's Determination before Poffin"],
        ),
        PolicyRule(
            "Poke Pad for Palafin",
            ["Finizen in play", "Palafin missing", "Poke Pad legal"],
            "Use Poke Pad for Palafin.",
            5500,
            "Palafin is the Zero to Hero bridge and is non-Rule Box.",
            ["Use Poke Pad for Palafin ex"],
        ),
        PolicyRule(
            "Zero to Hero",
            ["Palafin Active", "Switch effect legal", "Palafin ex available"],
            "Move Palafin to Bench and trigger Zero to Hero.",
            8000,
            "Palafin ex enters play through Palafin moving from Active to Bench.",
            ["Attack with Palafin instead of enabling Zero to Hero"],
        ),
        PolicyRule(
            "Water to Palafin ex",
            ["Palafin ex in play", "Water Energy in hand", "Palafin ex has no Energy"],
            "Attach Basic Water Energy to Palafin ex.",
            6500,
            "Palafin ex attacks for one Water and should not be overattached.",
            ["Attach extra Energy to Palafin ex", "Attach Lightning to Palafin ex"],
        ),
        PolicyRule(
            "Protect Lightning",
            ["Lightning Energy in hand", "Dragonite line exists or may exist"],
            "Attach Lightning only to Dratini, Dragonair, or Mega Dragonite ex.",
            6000,
            "Lightning Energy is scarce and required for Mega Dragonite ex.",
            ["Lightning to Palafin", "Lightning to Finizen", "Lightning to Tatsugiri"],
        ),
        PolicyRule(
            "Surfing Beach switch loop",
            ["Surfing Beach legal", "Palafin/Palafin ex switching needed"],
            "Play or use Surfing Beach.",
            6000,
            "Surfing Beach enables Zero to Hero and resets Palafin ex after Giga Impact.",
            ["Replace own useful Surfing Beach without reason"],
        ),
        PolicyRule(
            "Hilda package",
            ["Need Evolution plus Energy", "Hilda legal"],
            "Use Hilda for Palafin + Water, Dragonair + Lightning, or Mega Dragonite ex + Lightning.",
            5000,
            "Hilda solves paired evolution/energy needs but not missing Basics.",
            ["Use Hilda when missing Basic Finizen or Dratini"],
        ),
        PolicyRule(
            "Crispin Dragonite energy",
            ["Dragonite line needs mixed Energy", "Crispin legal"],
            "Use Crispin for Water + Lightning or Lightning acceleration.",
            5500,
            "Mega Dragonite ex needs Water plus two Lightning.",
            ["Spend Crispin when no attacker can use the Energy"],
        ),
        PolicyRule(
            "Boss/Kieran KO math",
            ["Boss or Kieran creates KO or final prize"],
            "Use Boss/Kieran line.",
            7000,
            "Prize-route cards should be used only when they change KO math or win path.",
            ["Boss without KO/prize benefit", "Kieran damage mode without changing KO math"],
        ),
        PolicyRule(
            "Bench Basic from hand",
            ["Basic Pokemon in hand", "Bench space exists"],
            "Bench the Basic before Supporter, setup Ability, attack, or end turn.",
            7200,
            "Known Basics in hand are guaranteed setup and should not be shuffled away or skipped.",
            ["End turn with playable Basic in hand", "Lillie before benching Basic"],
        ),
        PolicyRule(
            "Air Balloon active Palafin",
            ["Air Balloon legal", "Active Palafin evolution chain needs to retreat"],
            "Attach Air Balloon to active Palafin for Zero to Hero, locked Palafin ex for reset, or Tatsugiri for Dragonite pivot reset.",
            5200,
            "Air Balloon is designed for the Palafin loop and Tatsugiri Dragonite pivot, not random attachment.",
            ["Attach Air Balloon randomly"],
        ),
    ]

    if "Basic Lightning Energy" in analyses:
        rules.append(
            PolicyRule(
                "Lightning protected resource",
                ["Basic Lightning Energy visible"],
                "Protect Lightning for Mega Dragonite ex.",
                6000,
                "Analysis marks Lightning as protected for Dragonite.",
                ["Discard Lightning without recovery", "Attach Lightning to Palafin line"],
            )
        )
    return rules


def normalize_analyses(card_analyses: dict[str, CardAnalysis] | Iterable[CardAnalysis]) -> dict[str, CardAnalysis]:
    if isinstance(card_analyses, dict):
        return card_analyses
    return {analysis.card_name: analysis for analysis in card_analyses}


def rules_to_dicts(rules: Iterable[PolicyRule]) -> list[dict[str, Any]]:
    return [rule.to_dict() for rule in rules]


__all__ = ["PolicyRule", "generate_policy_rules_from_card_analysis", "rules_to_dicts"]
