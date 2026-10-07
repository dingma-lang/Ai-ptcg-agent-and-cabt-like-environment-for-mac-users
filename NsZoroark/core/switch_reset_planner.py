from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

from state_eval import OPT_ABILITY, OPT_ATTACH, OPT_PLAY, OPT_RETREAT, bench_pokemon, card_id, card_id_from_option, option_type
from core.palafin_attack_state import track_giga_impact_lock
from core.palafin_planner import (
    attached_energy_count_any,
    benched_palafin_ex_ready_to_attack,
    palafin_ex_recharge_loop_available,
    palafin_ex_reset_or_recharge_ready,
)
from core.priority_tables import canonical_name_from_id


@dataclass(frozen=True)
class ResetLine:
    available: bool = False
    option_index: Optional[int] = None
    score: float = 0.0
    reason: str = ""


def find_palafin_reset_line(state: Any, legal_options: Sequence[Any]) -> ResetLine:
    status = track_giga_impact_lock(state, None)
    if not status.restriction_applies_now:
        return ResetLine(False, reason="No attack-locked Palafin ex.")
    if not palafin_ex_reset_or_recharge_ready(state):
        return ResetLine(False, reason="No powered Palafin ex or normal Palafin recharge line.")
    best = ResetLine(False, reason="No reset line.")
    for idx, option in enumerate(legal_options):
        typ = option_type(option)
        name = canonical_name_from_id(card_id_from_option(state, option))
        score = 0.0
        reason = ""
        if typ == OPT_PLAY and name == "Surfing Beach":
            score = 10000.0
            reason = "Use Surfing Beach to reset Giga Impact without spending Switch."
        elif typ == OPT_PLAY and name in {"Switch", "Kieran"}:
            score = 8500.0 if name == "Switch" else 8200.0
            reason = "Reset Palafin ex by moving it to Bench."
        elif typ == OPT_ATTACH and name == "Air Balloon":
            score = 7600.0
            reason = "Reset Palafin ex by moving it to Bench."
        elif typ == OPT_RETREAT:
            score = 7600.0
            reason = "Reset Palafin ex by moving it to Bench."
        elif typ == OPT_ABILITY and name == "Mega Dragonite ex":
            score = 8500.0
            reason = "Use Sky Transport to reset Giga Impact."
        if benched_palafin_ex_ready_to_attack(state):
            score += 900.0
        if palafin_ex_recharge_loop_available(state):
            score += 1200.0
        if score > best.score:
            best = ResetLine(True, idx, score, reason)
    return best


def reset_line_available_next_turn(state: Any) -> bool:
    names_in_hand_or_play = {canonical_name_from_id(card_id_from_option(state, option)) for option in getattr(state, "options", []) or []}
    if names_in_hand_or_play & {"Surfing Beach", "Switch", "Kieran", "Air Balloon"}:
        return True
    return any(
        canonical_name_from_id(card_id(pokemon)) in {"Palafin ex", "Palafin"} and attached_energy_count_any(pokemon) > 0
        for pokemon in bench_pokemon(state)
    )


__all__ = ["ResetLine", "find_palafin_reset_line", "reset_line_available_next_turn"]
