from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from state_eval import OPT_ABILITY, OPT_PLAY, OPT_RETREAT, active_pokemon, card_id, card_id_from_option, option_type
from core.palafin_planner import (
    bench_has_ready_attacker,
    bench_has_water_switch_target,
    palafin_ex_recharge_loop_available,
    palafin_ex_reset_or_recharge_ready,
    pokemon_has_air_balloon_attached,
)
from core.priority_tables import canonical_name_from_id, has_in_hand


@dataclass(frozen=True)
class SwitchUsageDecision:
    score: float
    reason: str


def score_switch_usage(state: Any, option: Any) -> SwitchUsageDecision:
    typ = option_type(option)
    name = canonical_name_from_id(card_id_from_option(state, option))
    active_name = canonical_name_from_id(card_id(active_pokemon(state)))
    if typ == OPT_RETREAT or (typ == OPT_PLAY and name in {"Switch", "Surfing Beach"}):
        from core.expert_battle_planner import progress_move_score

        score = progress_move_score(state, "Retreat" if typ == OPT_RETREAT else name)
        if score > 0:
            if typ == OPT_PLAY and name == "Switch" and any(
                option_type(o) == OPT_ABILITY and card_id_from_option(state, o) == 904 for o in state.options
            ):
                return SwitchUsageDecision(-1800.0, "Use the legal Sky Transport route before spending Switch for the same destination.")
            return SwitchUsageDecision(score, "Move to a ready attacker or productive pivot without paying retreat Energy.")
    if typ == OPT_RETREAT:
        from core.expert_battle_planner import free_manual_retreat, opening_tatsugiri_route

        if opening_tatsugiri_route(state) and free_manual_retreat(state):
            return SwitchUsageDecision(8400.0, "Free retreat into Tatsugiri opens Supporter access.")
        try:
            from core.turn_plan import retreat_should_yield_to_sky

            if retreat_should_yield_to_sky(state):
                return SwitchUsageDecision(-2200.0, "Hold manual retreat because Sky Transport can create the same movement without spending Energy.")
        except Exception:
            pass
        if active_name == "Palafin" and bench_has_water_switch_target(state):
            return SwitchUsageDecision(8000.0, "Use Switch because Palafin must move to Bench for Zero to Hero.")
        if active_name == "Palafin ex" and palafin_ex_reset_or_recharge_ready(state):
            score = 7600.0 if palafin_ex_recharge_loop_available(state) else 6500.0
            return SwitchUsageDecision(score, "Reset attack-locked Palafin ex by moving it to Bench.")
        if active_name == "Tatsugiri" and pokemon_has_air_balloon_attached(active_pokemon(state)) and bench_has_ready_attacker(state):
            return SwitchUsageDecision(8200.0, "Retreat Tatsugiri for free with Air Balloon into a ready attacker.")
        return SwitchUsageDecision(-7000.0, "Block useless Switch; no Zero to Hero, reset, KO, or survival value.")
    if typ != OPT_PLAY or name not in {"Switch", "Kieran", "Surfing Beach"}:
        return SwitchUsageDecision(0.0, "")
    try:
        from core.turn_plan import switch_item_should_yield_to_sky

        if switch_item_should_yield_to_sky(state, name):
            return SwitchUsageDecision(-2600.0, "Prefer Sky Transport before spending a one-use switch card.")
    except Exception:
        pass
    if active_name == "Palafin" and bench_has_water_switch_target(state):
        base = 8000.0 if name != "Surfing Beach" else 9500.0
        return SwitchUsageDecision(base, "Use Switch because Palafin must move to Bench for Zero to Hero.")
    if active_name == "Palafin ex" and palafin_ex_reset_or_recharge_ready(state):
        base = 7600.0 if name != "Surfing Beach" else 9200.0
        if palafin_ex_recharge_loop_available(state):
            base += 900.0
        return SwitchUsageDecision(base, "Use Switch because this Palafin ex is locked after Giga Impact.")
    if name == "Switch" and has_in_hand(state, "Surfing Beach"):
        return SwitchUsageDecision(-2500.0, "Prefer Surfing Beach over Switch because it saves the Item.")
    return SwitchUsageDecision(-7000.0, "Block useless Switch; no Zero to Hero, reset, KO, or survival value.")


__all__ = ["SwitchUsageDecision", "score_switch_usage"]
