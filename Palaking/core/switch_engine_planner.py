from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from state_eval import OPT_ABILITY, OPT_ATTACH, OPT_PLAY, OPT_RETREAT, card_id_from_option, option_type
from core.palafin_planner import score_air_balloon_play_or_attach, score_palaking_option, score_switch_card_play, score_surfing_beach_play
from core.priority_tables import canonical_name_from_id


@dataclass(frozen=True)
class SwitchScore:
    score: float = 0.0
    reason: str = ""


def score_switch_action(state: Any, option: Any) -> SwitchScore:
    typ = option_type(option)
    name = canonical_name_from_id(card_id_from_option(state, option))
    if typ == OPT_RETREAT:
        score = score_palaking_option(state, option)
        return SwitchScore(score, "Retreat only when it triggers Zero to Hero, resets Palafin ex, or improves attack.")
    if typ == OPT_PLAY and name == "Surfing Beach":
        return SwitchScore(score_surfing_beach_play(state), "Use Surfing Beach as preferred Palafin switch engine.")
    if typ == OPT_PLAY and name in {"Switch", "Kieran"}:
        return SwitchScore(score_switch_card_play(state, name), "Use switch card to trigger Zero to Hero or reset Palafin ex.")
    if typ == OPT_ATTACH and name == "Air Balloon":
        return SwitchScore(score_air_balloon_play_or_attach(state, option), "Attach Air Balloon only for active Palafin Zero to Hero or locked Palafin ex reset lines.")
    if typ == OPT_ABILITY and name == "Mega Dragonite ex":
        score = score_palaking_option(state, option)
        return SwitchScore(score, "Use Sky Transport to rotate Palafin attackers or bring the right attacker Active.")
    return SwitchScore(0.0, "")
