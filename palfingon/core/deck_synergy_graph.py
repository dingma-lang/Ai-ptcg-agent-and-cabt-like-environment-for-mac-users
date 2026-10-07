from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from core.card_analysis import build_all_card_analyses
from core.card_relationships import CardRelationship, build_card_relationships
from core.policy_rules_from_analysis import generate_policy_rules_from_card_analysis


def build_deck_synergy_graph() -> dict[str, Any]:
    analyses = build_all_card_analyses()
    relationships = build_card_relationships()
    rules = generate_policy_rules_from_card_analysis(analyses, relationships)
    return {
        "deck_name": "Palafin ex / Mega Dragonite ex",
        "nodes": [
            {
                "id": analysis.card_name,
                "count": analysis.count_in_deck,
                "roles": analysis.role,
                "card_type": analysis.card_type,
            }
            for analysis in analyses.values()
        ],
        "edges": [
            {
                "source": rel.source_card,
                "target": rel.target_card,
                "relationship": rel.relationship_type,
                "weight": rel.priority,
                "condition": rel.condition,
                "reason": rel.reason,
            }
            for rel in relationships
        ],
        "policy_rules": [rule.to_dict() for rule in rules],
    }


def export_deck_synergy_graph(path: str | Path = "data/deck_synergy_graph.json") -> dict[str, Any]:
    graph = build_deck_synergy_graph()
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(graph, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return graph


def render_synergy_map_markdown(graph: dict[str, Any] | None = None) -> str:
    graph = graph or build_deck_synergy_graph()
    edges = graph["edges"]
    lines = [
        "# Palaking Synergy Map",
        "",
        "## Main Combo Lines",
        "",
        "### Combo 1: Palafin ex setup",
        "Buddy-Buddy Poffin -> Finizen -> Poke Pad/Hilda -> Palafin -> Surfing Beach/Switch/Kieran/Air Balloon -> Zero to Hero -> Palafin ex -> Basic Water Energy -> attack.",
        "",
        "### Combo 2: Palafin reset",
        "Palafin ex attacks with Giga Impact, then Surfing Beach/Switch/Kieran/Mega Dragonite ex ability rotates or resets the attacker before the next attack.",
        "",
        "### Combo 3: Dragonite setup",
        "Dratini -> Dragonair -> attach Water/Lightning -> Hilda/Crispin -> Mega Dragonite ex -> use switch ability or attack for 330 when it matters.",
        "",
        "### Combo 4: Secret Box setup",
        "Secret Box discards 3 safe cards and finds an Item, Tool, Supporter, and Stadium package such as Poffin/Poke Pad/Switch + Air Balloon + Hilda/Lillie/Petrel/Crispin + Surfing Beach.",
        "",
        "### Combo 5: Final prize math",
        "Boss's Orders or Kieran plus Palafin ex 250/280 or Mega Dragonite ex 330/360 creates closing prize routes.",
        "",
        "## Search Relationships",
        "",
    ]
    lines.extend(format_edges(edges, {"searches", "finds_exact_trainer", "finds_evolution_piece", "finds_stadium", "finds_tool", "finds_supporter"}))
    lines.extend(["", "## Switch Relationships", ""])
    lines.extend(format_edges(edges, {"enables_zero_to_hero", "resets_attack_restriction"}))
    lines.extend(["", "## Energy Relationships", ""])
    lines.extend(format_edges(edges, {"enables_attack", "provides_energy", "should_not_target"}))
    lines.extend(["", "## Recovery Relationships", ""])
    lines.extend(format_edges(edges, {"recovers_energy", "recovers_pokemon"}))
    lines.extend(
        [
            "",
            "## Supporter Decision Map",
            "",
            "- Team Rocket's Petrel: exact Trainer search when one card solves the turn.",
            "- Hilda: Evolution plus Energy package; not for missing Basics.",
            "- Crispin: mixed Energy, especially Mega Dragonite ex.",
            "- Lillie's Determination: broad refresh only after exact setup actions are checked.",
            "- Boss's Orders and Kieran: use only for KO, final prize, switch reset, or exact damage math.",
            "",
            "## Common Wrong Plays",
            "",
            "- Lillie before legal Poffin, Poke Pad, evolution, Basic bench, or setup Ability.",
            "- Expecting Poffin to find Dratini when local Dratini has 80 HP.",
            "- Searching Palafin ex with Poke Pad instead of keeping it for Zero to Hero.",
            "- Attaching Lightning Energy to Palafin line or Tatsugiri.",
            "- Using Dragonite attack casually and discarding Energy without prize-route gain.",
            "- Attaching Air Balloon randomly instead of active Palafin Zero to Hero or locked Palafin ex reset.",
            "",
            "## Correct Sequencing Examples",
            "",
            "1. Bench Basic Pokemon from hand before Supporter, Ability, attack, or end.",
            "2. Use Poffin before Lillie when Bench has space and Finizen/Tatsugiri remain.",
            "3. Use Poke Pad for Palafin when Finizen is ready; use Poke Pad for Dratini when Dragonite line is absent.",
            "4. Move active Palafin to Bench with Surfing Beach/Switch/Kieran/Air Balloon to trigger Zero to Hero.",
            "5. Attach Water to Palafin ex once, then preserve switch/reset cards for real Giga Impact lock turns.",
        ]
    )
    return "\n".join(lines) + "\n"


def format_edges(edges: Iterable[dict[str, Any]], relationship_types: set[str]) -> list[str]:
    rows = []
    for edge in edges:
        if edge["relationship"] not in relationship_types:
            continue
        rows.append(f"- {edge['source']} -> {edge['target']} ({edge['relationship']}, {edge['weight']}): {edge['reason']}")
    return rows or ["- None."]


def export_synergy_map(path: str | Path = "docs/SYNERGY_MAP.md") -> str:
    text = render_synergy_map_markdown()
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
    return text


if __name__ == "__main__":
    export_deck_synergy_graph()
    export_synergy_map()
