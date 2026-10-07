from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from action_classifier import ActionCategory, classify_legal_option
from decision_reason import explain_option
from option_scorer import debug_scores, score_option, score_options


@dataclass
class ScoredOption:
    index: int
    category: str
    score: float
    reason: str


def score_option_with_reason(state: Any, option: Any, option_index: int = 0) -> ScoredOption:
    score = score_option(state, option, option_index=option_index, all_options=state.options)
    classified = classify_legal_option(state, option, option_index)
    reason = explain_option(state, classified, score)
    return ScoredOption(index=option_index, category=classified.category or ActionCategory.UNKNOWN, score=score, reason=reason)

__all__ = ["score_option", "score_options", "debug_scores", "ScoredOption", "score_option_with_reason"]
