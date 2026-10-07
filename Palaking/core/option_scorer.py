from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List

from action_classifier import ActionCategory, classify_legal_option
from decision_reason import explain_option
from option_scorer import debug_scores, score_option, score_options
from state_eval import OPT_ATTACH, OPT_ATTACK, OPT_PLAY, attach_target_from_option, bench_space, card_id, card_id_from_option, option_type
from core.deck_profile import card_analysis_map, card_relationships, generated_policy_rules
from core.priority_tables import canonical_name, canonical_name_from_id, count_in_play, has_in_hand


@dataclass
class ScoredOption:
    index: int
    category: str
    score: float
    reason: str
    supporting_cards: List[str] | None = None
    blocked_by: List[str] | None = None
    relationship_explanation: str = ""


def score_option_with_reason(state: Any, option: Any, option_index: int = 0) -> ScoredOption:
    score = score_option(state, option, option_index=option_index, all_options=state.options)
    classified = classify_legal_option(state, option, option_index)
    reason = explain_option(state, classified, score)
    return ScoredOption(index=option_index, category=classified.category or ActionCategory.UNKNOWN, score=score, reason=reason)


def score_option_with_analysis(state: Any, option: Any, option_index: int = 0) -> ScoredOption:
    base = score_option(state, option, option_index=option_index, all_options=getattr(state, "options", []) or [])
    classified = classify_legal_option(state, option, option_index)
    card_name = canonical_name(classified.card_name or canonical_name_from_id(card_id_from_option(state, option)))
    target_name = canonical_name(classified.target_name or canonical_name_from_id(card_id(attach_target_from_option(state, option))))
    adjustment, supporting, blocked, rel_reason = analysis_adjustment(state, option, card_name, target_name)
    score = base + adjustment
    reason = rel_reason or explain_option(state, classified, score)
    return ScoredOption(
        index=option_index,
        category=classified.category or ActionCategory.UNKNOWN,
        score=score,
        reason=reason,
        supporting_cards=supporting,
        blocked_by=blocked,
        relationship_explanation=rel_reason,
    )


def score_options_with_analysis(state: Any) -> list[ScoredOption]:
    return [score_option_with_analysis(state, option, idx) for idx, option in enumerate(getattr(state, "options", []) or [])]


def analysis_adjustment(state: Any, option: Any, card_name: str, target_name: str = "") -> tuple[float, list[str], list[str], str]:
    analyses = card_analysis_map()
    relationships = card_relationships()
    rules = generated_policy_rules()
    typ = option_type(option)
    supporting: list[str] = []
    blocked: list[str] = []
    reasons: list[str] = []
    score = 0.0

    if card_name in analyses:
        analysis = analyses[card_name]
        if "search_card" in analysis.role:
            supporting.extend(analysis.search_targets[:4])
        if "switch_engine" in analysis.role:
            supporting.extend(["Palafin", "Palafin ex"])

    if card_name == "Buddy-Buddy Poffin" and bench_space(state) > 0 and count_in_play(state, "Finizen") < 2:
        score += rule_priority(rules, "Poffin before Lillie")
        supporting.extend(["Finizen", "Tatsugiri"])
        reasons.append("Poffin searches Finizen/Tatsugiri and Bench is weak.")
    if card_name == "Lillie's Determination" and has_in_hand(state, "Buddy-Buddy Poffin") and bench_space(state) > 0 and count_in_play(state, "Finizen") < 2:
        score -= 1500.0
        blocked.append("Buddy-Buddy Poffin")
        reasons.append("Lillie would shuffle before playable Poffin setup.")
    if card_name == "Poke Pad" and count_in_play(state, "Finizen") > 0 and count_in_play(state, "Palafin") == 0:
        score += rule_priority(rules, "Poke Pad for Palafin")
        supporting.append("Palafin")
        reasons.append("Poke Pad can find normal Palafin for Zero to Hero.")
    if card_name == "Surfing Beach":
        score += 1800.0
        supporting.extend(["Palafin", "Palafin ex"])
        reasons.append("Surfing Beach enables Zero to Hero and Palafin ex reset.")
    if typ == OPT_ATTACH and card_name == "Basic Lightning Energy" and target_name in {"Finizen", "Palafin", "Palafin ex", "Tatsugiri"}:
        score -= 5000.0
        blocked.append("Mega Dragonite ex")
        reasons.append("Lightning Energy is protected for Mega Dragonite ex and should not favor Palafin/Tatsugiri.")
    if typ == OPT_ATTACH and card_name == "Basic Water Energy" and target_name == "Palafin ex":
        score += rule_priority(rules, "Water to Palafin ex")
        supporting.append("Palafin ex")
        reasons.append("Water Energy enables Palafin ex attack.")
    if card_name in {"Air Balloon", "Switch", "Kieran", "Surfing Beach"}:
        try:
            from core.air_balloon_planner import score_air_balloon_target
            from core.switch_usage_guard import score_switch_usage

            switch_score = score_switch_usage(state, option)
            balloon_score = score_air_balloon_target(state, option)
            if switch_score.reason:
                score += switch_score.score * 0.15
                reasons.append(switch_score.reason)
            if balloon_score.reason:
                score += balloon_score.score * 0.15
                reasons.append(balloon_score.reason)
        except Exception:
            pass
    if typ == OPT_ATTACK:
        try:
            from core.giga_impact_planner import score_giga_impact_attack

            giga = score_giga_impact_attack(state, option)
            if giga.reason:
                score += giga.score * 0.15
                supporting.append("Giga Impact")
                reasons.append(giga.reason)
        except Exception:
            pass

    if not reasons:
        matching = [rel for rel in relationships if rel.source_card == card_name and rel.priority > 0]
        if matching:
            rel = max(matching, key=lambda item: item.priority)
            supporting.append(rel.target_card)
            reasons.append(f"{rel.source_card} {rel.relationship_type} {rel.target_card}: {rel.reason}")

    return score, unique(supporting), unique(blocked), " ".join(reasons)


def rule_priority(rules: Any, rule_name: str) -> float:
    for rule in rules:
        if rule.rule_name == rule_name:
            return float(rule.priority)
    return 0.0


def unique(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value and value not in seen:
            result.append(value)
            seen.add(value)
    return result


__all__ = [
    "score_option",
    "score_options",
    "debug_scores",
    "ScoredOption",
    "score_option_with_reason",
    "score_option_with_analysis",
    "score_options_with_analysis",
]
