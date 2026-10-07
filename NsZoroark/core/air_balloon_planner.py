from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from state_eval import OPT_ATTACH, active_pokemon, attach_target_from_option, card_id, option_type
from core.palafin_planner import (
    palafin_ex_recharge_loop_available,
    palafin_ex_reset_or_recharge_ready,
    target_is_active,
    zero_to_hero_combo_ready,
)
from core.priority_tables import canonical_name_from_id, count_in_play


@dataclass(frozen=True)
class AirBalloonDecision:
    score: float
    reason: str


def score_air_balloon_target(state: Any, option: Any) -> AirBalloonDecision:
    if option_type(option) != OPT_ATTACH:
        return AirBalloonDecision(0.0, "")
    target = attach_target_from_option(state, option)
    target_name = canonical_name_from_id(card_id(target))
    active_name = canonical_name_from_id(card_id(active_pokemon(state)))

    if target_name == "Palafin" and target_is_active(state, target) and zero_to_hero_combo_ready(state):
        return AirBalloonDecision(7000.0, "Attach Air Balloon to Palafin because it retreats this round to trigger Zero to Hero.")
    if target_name == "Tatsugiri":
        if target_is_active(state, target) or active_name == "Tatsugiri":
            return AirBalloonDecision(8800.0, "Attach Air Balloon to active Tatsugiri so it can pivot without discarding Energy.")
        if active_name == "Palafin ex" or count_in_play(state, "Mega Dragonite ex") > 0:
            return AirBalloonDecision(6800.0, "Attach Air Balloon to Tatsugiri because Dragonite can use it as the Palafin reset pivot.")
        if count_in_play(state, "Dragonair") > 0:
            return AirBalloonDecision(5200.0, "Attach Air Balloon to Tatsugiri before the Dragonite switch engine comes online.")
        return AirBalloonDecision(3600.0, "Attach Air Balloon to Tatsugiri as a useful support pivot.")
    if target_name == "Palafin ex":
        if target_is_active(state, target) and palafin_ex_reset_or_recharge_ready(state):
            score = 7200.0 if palafin_ex_recharge_loop_available(state) else 5600.0
            return AirBalloonDecision(score, "Palafin ex can use Air Balloon only for a real Giga Impact reset line.")
        return AirBalloonDecision(-5000.0, "Save Air Balloon for normal Palafin Zero to Hero.")
    if target is None:
        return AirBalloonDecision(1500.0, "Hold Air Balloon for Palafin or Tatsugiri.")
    return AirBalloonDecision(-6000.0, "Block random Air Balloon attachment.")


__all__ = ["AirBalloonDecision", "score_air_balloon_target"]
