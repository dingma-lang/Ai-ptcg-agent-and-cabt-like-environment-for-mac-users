from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class ActionIntentType:
    PLAY_CARD_FROM_HAND = "PLAY_CARD_FROM_HAND"
    ATTACH_ENERGY = "ATTACH_ENERGY"
    BENCH_BASIC = "BENCH_BASIC"
    EVOLVE = "EVOLVE"
    RARE_CANDY_EVOLVE = "RARE_CANDY_EVOLVE"
    USE_ABILITY = "USE_ABILITY"
    PLAY_SUPPORTER = "PLAY_SUPPORTER"
    PLAY_ITEM = "PLAY_ITEM"
    PLAY_STADIUM = "PLAY_STADIUM"
    RETREAT = "RETREAT"
    SWITCH_ACTIVE = "SWITCH_ACTIVE"
    ATTACK = "ATTACK"
    CHOOSE_TARGET = "CHOOSE_TARGET"
    DISCARD_CARD = "DISCARD_CARD"
    SEARCH_CARD = "SEARCH_CARD"
    TAKE_PRIZE = "TAKE_PRIZE"
    PROMOTE_AFTER_KO = "PROMOTE_AFTER_KO"
    PASS = "PASS"
    UNKNOWN = "UNKNOWN"


@dataclass
class ActionIntent:
    intent_type: str
    selected_option_indices: List[int] = field(default_factory=list)
    source_card_id: Optional[int] = None
    source_card_name: str = ""
    target_card_id: Optional[int] = None
    target_card_name: str = ""
    target_zone: str = ""
    selected_cards: List[int] = field(default_factory=list)
    priority_score: float = 0.0
    reason: str = ""
    warning: str = ""
    confidence: str = "medium"
    mandatory: bool = False
    optional: bool = False
    consumes_supporter: bool = False
    consumes_energy_attachment: bool = False
    consumes_retreat: bool = False
    consumes_stadium: bool = False
    submission_safe: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def as_event(self) -> Dict[str, Any]:
        return {
            "intent_type": self.intent_type,
            "source_card": self.source_card_name or self.source_card_id,
            "target_card": self.target_card_name or self.target_card_id,
            "target_zone": self.target_zone,
            "selected_cards": list(self.selected_cards),
            "priority_score": round(float(self.priority_score), 3),
            "reason": self.reason,
            "warning": self.warning,
            "confidence": self.confidence,
            "mandatory": self.mandatory,
            "optional": self.optional,
            "submission_safe": self.submission_safe,
        }
