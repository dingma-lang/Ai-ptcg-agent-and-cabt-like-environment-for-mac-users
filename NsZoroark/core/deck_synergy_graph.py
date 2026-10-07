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
        "deck_name": "N's Zoroark ex / N's Zekrom",
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
        "# N's Zoroark Synergy Map",
        "",
        "## Main Combo Lines",
        "",
        "### Combo 1: Zoroark setup",
        "Buddy-Buddy Poffin -> N's Zorua -> N's Zoroark ex -> keep N's Zekrom or N's Darmanitan available on Bench -> Night Joker.",
        "",
        "### Combo 2: PP Up acceleration",
        "Discard Darkness Energy through Ultra Ball, Secret Box, or Trade-style costs -> N's PP Up -> attach to Benched N's attacker.",
        "",
        "### Combo 3: Castle movement",
        "N's Castle removes retreat costs from N's Pokemon, letting Zoroark/Zekrom pivot without wasting Energy.",
        "",
        "### Combo 4: Tome transformation",
        "Transformation Tome should eventually swap a Basic Pokemon from discard with a Basic in play, preserving attached cards and damage state. This route needs the local cabt card ID before it can be tested.",
        "",
        "### Combo 5: Final prize math",
        "Boss's Orders plus Zoroark copied attacks, Binding Mochi damage, or N's Zekrom pressure creates closing prize routes.",
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
            "- Lillie's Determination: broad refresh after exact setup actions are checked.",
            "- Cyrano: Pokemon search when a Zoroark/Zekrom piece is missing.",
            "- Black Belt's Training: damage modifier for Pokemon ex KO math.",
            "- Boss's Orders: use only for KO, final prize, or exact tempo gain.",
            "- Ruffian and Special Red Card: disruption, not default setup.",
            "",
            "## Common Wrong Plays",
            "",
            "- Lillie before legal Poffin, Zoroark evolution, Basic bench, or useful N's PP Up.",
            "- Discarding the only N's Zoroark ex or only N's Zekrom without a replacement route.",
            "- Benching two-prize support Pokemon without using their value.",
            "- Using Boss's Orders without KO or prize-route benefit.",
            "- Spending N's PP Up on a low-impact target while a Benched N's attacker needs Energy.",
            "",
            "## Correct Sequencing Examples",
            "",
            "1. Bench Basic Pokemon from hand before Supporter, Ability, attack, or end.",
            "2. Use Poffin before Lillie when Bench has space and Zorua/support Basics remain.",
            "3. Evolve N's Zorua into N's Zoroark ex before discard-cost Items when legal.",
            "4. Use discard costs to create N's PP Up Energy targets only when payoff is real.",
            "5. Attack with Zoroark ex when Night Joker copies the best available N's attack or a KO is visible.",
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
