from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from state_eval import OPT_ABILITY, active_pokemon, bench_pokemon, card_id_from_option, option_type, pokemon_hp
from core.poison_mochi_planner import mochi_math_available
from core.priority_tables import canonical_name_from_id, context_source_name
from core.target_board import PECHARUNT_EX, ZOROARK_EX, pokemon_name, ready_zoroarks


@dataclass(frozen=True)
class PecharuntDecision:
    should_use: bool
    score: float = 0.0
    reason: str = ""


def score_pecharunt_option(state: Any, option: Any) -> float:
    name = canonical_name_from_id(card_id_from_option(state, option))
    if name != PECHARUNT_EX:
        return 0.0
    if option_type(option) != OPT_ABILITY:
        return 0.0
    decision = evaluate_pecharunt(state)
    return decision.score if decision.should_use else -900.0


def evaluate_pecharunt(state: Any) -> PecharuntDecision:
    ready = ready_zoroarks(state)
    if not ready:
        return PecharuntDecision(False, -1200.0, "Do not use Pecharunt without a ready Zoroark.")
    active = active_pokemon(state)
    if mochi_math_available(state):
        return PecharuntDecision(True, 7500.0, "Use Pecharunt to switch in Zoroark and activate Binding Mochi KO math.")
    if pokemon_name(active) != ZOROARK_EX and any(pokemon_name(pokemon) == ZOROARK_EX for pokemon in bench_pokemon(state)):
        return PecharuntDecision(True, 2800.0, "Use Pecharunt to bring powered Zoroark active.")
    return PecharuntDecision(False, -1000.0, "No Pecharunt switch/poison benefit.")


def score_pecharunt_switch_target(state: Any, pokemon: Any) -> float:
    if context_source_name(state) != PECHARUNT_EX:
        return 0.0
    if pokemon_name(pokemon) == ZOROARK_EX:
        return 7600.0 if mochi_math_available(state) else 3000.0
    return -2500.0
