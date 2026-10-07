from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from action_classifier import ActionCategory, classify_legal_option
from card_db import get_db
from state_eval import OPT_ATTACK, OPT_ATTACH, OPT_CARD, OPT_EVOLVE, OPT_PLAY, active_pokemon, attach_target_from_option, card_id, card_id_from_option, getv, option_type, pokemon_energy_count, pokemon_hp
from core.energy_planner import pokemon_uses_energy_type
from core.opponent_model import infer_opponent_next_turn_threat
from core.priority_tables import CARD_IDS, canonical_name_from_id, context_source_name, has_in_hand, has_in_play


@dataclass(frozen=True)
class MegaGengarPlan:
    score: float
    reason: str
    ability_relevant: bool = False
    can_attack_soon: bool = False


def score_mega_gengar_plan(state: Any, opponent_model: Any = None) -> MegaGengarPlan:
    threat = opponent_model or infer_opponent_next_turn_threat(state)
    score = 0.0
    reasons = []
    if has_in_play(state, "Gastly"):
        score += 750.0
        reasons.append("Gastly in play")
    if has_in_play(state, "Haunter"):
        score += 1400.0
        reasons.append("Haunter in play")
    if has_in_play(state, "Mega Gengar ex"):
        score += 1800.0
        reasons.append("Mega Gengar ex in play")
    if has_in_hand(state, "Mega Gengar ex"):
        score += 800.0
        reasons.append("Mega Gengar ex available")
    if threat.likely_ex_heavy or threat.has_rulebox_attacker:
        score += 1500.0
        reasons.append("opponent ex prize trade matters")
    if not has_in_play(state, "Hydreigon ex"):
        score += 700.0
        reasons.append("Hydreigon is not online")
    if mega_gengar_line_live(state):
        score += 1200.0
        reasons.append("Mega Gengar line is live")
    can_attack = mega_gengar_can_attack_soon(state)
    if can_attack:
        score += 900.0
        reasons.append("Mega Gengar can attack soon")
    return MegaGengarPlan(
        score=score,
        reason="Mega Gengar ex is main attacker and prize-exchange engine." if score else "Mega Gengar line is not available.",
        ability_relevant=bool(threat.likely_ex_heavy or threat.has_rulebox_attacker),
        can_attack_soon=can_attack,
    )


def score_mega_gengar_option(state: Any, option: Any, base_score: float = 0.0) -> float:
    cid = card_id_from_option(state, option)
    name = canonical_name_from_id(cid)
    typ = option_type(option)
    threat = infer_opponent_next_turn_threat(state)
    bonus = 0.0
    if typ == OPT_CARD and int(getv(option, "playerIndex", state.your_index) or state.your_index) != state.your_index:
        return 0.0

    if typ == OPT_EVOLVE:
        target = attach_target_from_option(state, option)
        target_name = canonical_name_from_id(card_id(target))
        if name == "Mega Gengar ex" and target_name == "Haunter":
            bonus += 3600.0
            if threat.has_rulebox_attacker or threat.likely_ex_heavy:
                bonus += 2400.0
        elif name == "Haunter" and target_name == "Gastly" and (has_in_hand(state, "Mega Gengar ex") or threat.likely_ex_heavy):
            bonus += 1800.0
            if threat.has_rulebox_attacker or threat.likely_ex_heavy:
                bonus += 1200.0

    if typ == OPT_CARD and context_source_name(state) == "Ultra Ball" and name == "Mega Gengar ex" and has_in_play(state, "Haunter"):
        bonus += 3600.0
        if threat.has_rulebox_attacker or threat.likely_ex_heavy:
            bonus += 2800.0

    if typ == OPT_PLAY and name == "Crispin" and mega_gengar_needs_darkness_for_attack(state):
        bonus += 28000.0

    if typ == OPT_ATTACH and name == "Basic Darkness Energy":
        target = attach_target_from_option(state, option)
        target_name = canonical_name_from_id(card_id(target))
        if target_name == "Mega Gengar ex":
            bonus += 1800.0 if pokemon_energy_count(target) < 2 else 300.0
        elif target_name in {"Gastly", "Haunter"}:
            bonus += 1000.0

    if typ == OPT_ATTACK and canonical_name_from_id(card_id(active_pokemon(state))) == "Mega Gengar ex":
        if base_score >= 10000.0:
            bonus += 3500.0
        else:
            bonus += 3200.0

    if cid == CARD_IDS["Mega Gengar ex"] and (threat.has_rulebox_attacker or threat.likely_ex_heavy):
        bonus += 2800.0
    elif cid == CARD_IDS["Mega Gengar ex"] and threat.likely_one_prize:
        bonus -= 100.0
    return bonus


def mega_gengar_line_live(state: Any) -> bool:
    return (
        has_in_play(state, "Mega Gengar ex")
        or has_in_play(state, "Haunter")
        or (has_in_play(state, "Gastly") and (has_in_hand(state, "Haunter") or has_in_hand(state, "Mega Gengar ex")))
    )


def mega_gengar_evolution_available(state: Any) -> bool:
    return has_in_hand(state, "Mega Gengar ex") and has_in_play(state, "Haunter")


def mega_gengar_can_attack_soon(state: Any) -> bool:
    for pokemon in [active_pokemon(state)] + list(getv(getv(state.current, "players", [])[state.your_index], "bench", []) or []):
        if canonical_name_from_id(card_id(pokemon)) not in {"Mega Gengar ex", "Haunter", "Gastly"}:
            continue
        if pokemon_energy_count(pokemon) >= 1:
            return True
    return False


def mega_gengar_needs_darkness_for_attack(state: Any) -> bool:
    for pokemon in [active_pokemon(state)] + list(getv(getv(state.current, "players", [])[state.your_index], "bench", []) or []):
        if canonical_name_from_id(card_id(pokemon)) != "Mega Gengar ex":
            continue
        return pokemon_energy_count(pokemon) < 2
    return False
