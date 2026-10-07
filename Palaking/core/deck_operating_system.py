from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List

from state_eval import bench_pokemon, bench_space, card_id, getv, iter_in_play, prize_count
from core.priority_tables import CARD_IDS, canonical_name_from_id, count_in_play, has_in_hand, has_in_play


@dataclass(frozen=True)
class DeckGoalState:
    hydreigon_chains_current: int
    hydreigon_chains_target: int = 2
    gengar_chains_current: int = 0
    gengar_chains_target: int = 1
    toxtricity_chains_current: int = 0
    toxtricity_chains_target: int = 1
    has_fezandipiti_ex: bool = False
    has_pecharunt_ex: bool = False
    open_bench_slots: int = 0
    missing_core_pieces: List[str] = field(default_factory=list)
    missing_evolution_pieces: List[str] = field(default_factory=list)
    missing_energy_engine: List[str] = field(default_factory=list)
    missing_support_basics: List[str] = field(default_factory=list)
    next_best_setup_piece: str = ""
    setup_urgency: float = 0.0
    target_board_complete: bool = False
    reason: str = ""


def compute_deck_goal_state(state: Any) -> DeckGoalState:
    hydreigon_chains = min(2, count_line_pokemon(state, {"Deino", "Zweilous", "Hydreigon ex"}))
    gengar_chains = min(1, count_line_pokemon(state, {"Gastly", "Haunter", "Mega Gengar ex"}))
    tox_chains = min(1, count_line_pokemon(state, {"Toxel", "Toxtricity"}))
    has_fez = has_in_play(state, "Fezandipiti ex")
    has_pech = has_in_play(state, "Pecharunt ex")
    open_slots = bench_space(state)

    missing_core: List[str] = []
    if count_in_play(state, "Deino") < 2:
        missing_core.append("Deino")
    if not has_in_play(state, "Gastly") and not has_in_play(state, "Haunter") and not has_in_play(state, "Mega Gengar ex"):
        missing_core.append("Gastly")
    if not has_in_play(state, "Toxel") and not has_in_play(state, "Toxtricity"):
        missing_core.append("Toxel")

    missing_evolution: List[str] = []
    if has_in_play(state, "Deino") and not has_in_play(state, "Hydreigon ex"):
        missing_evolution.extend(["Rare Candy", "Hydreigon ex"])
    if has_in_play(state, "Gastly") and not has_in_play(state, "Mega Gengar ex"):
        missing_evolution.extend(["Haunter", "Mega Gengar ex"])
    if has_in_play(state, "Toxel") and not has_in_play(state, "Toxtricity"):
        missing_evolution.append("Toxtricity")

    missing_engine = [] if tox_chains else ["Toxel", "Toxtricity"]
    missing_support: List[str] = []
    if not has_fez:
        missing_support.append("Fezandipiti ex")
    if not has_pech:
        missing_support.append("Pecharunt ex")

    stage = game_stage(state)
    next_piece = next_setup_piece(state, stage, missing_core, missing_evolution, missing_support)
    complete = (
        hydreigon_chains >= 2
        and gengar_chains >= 1
        and tox_chains >= 1
        and has_fez
        and has_pech
    )
    urgency = setup_urgency_score(state, complete, missing_core, missing_evolution, missing_support)
    reason = (
        f"Target field: Hydreigon {hydreigon_chains}/2, Mega Gengar {gengar_chains}/1, "
        f"Toxtricity {tox_chains}/1, Fezandipiti={has_fez}, Pecharunt={has_pech}."
    )
    return DeckGoalState(
        hydreigon_chains_current=hydreigon_chains,
        gengar_chains_current=gengar_chains,
        toxtricity_chains_current=tox_chains,
        has_fezandipiti_ex=has_fez,
        has_pecharunt_ex=has_pech,
        open_bench_slots=open_slots,
        missing_core_pieces=missing_core,
        missing_evolution_pieces=dedupe(missing_evolution),
        missing_energy_engine=missing_engine,
        missing_support_basics=missing_support,
        next_best_setup_piece=next_piece,
        setup_urgency=urgency,
        target_board_complete=complete,
        reason=reason,
    )


def count_line_pokemon(state: Any, names: set[str]) -> int:
    return sum(1 for _, _, pokemon in iter_in_play(state) if canonical_name_from_id(card_id(pokemon)) in names)


def game_stage(state: Any) -> str:
    turn = int(getv(state.current, "turn", 0) or 0)
    if turn <= 4 or len(bench_pokemon(state)) <= 1:
        return "early"
    if prize_count(state) <= 2:
        return "late"
    return "mid"


def next_setup_piece(state: Any, stage: str, missing_core: List[str], missing_evolution: List[str], missing_support: List[str]) -> str:
    if stage == "late":
        for name in ("Hydreigon ex", "Mega Gengar ex", "Crispin"):
            if needs_piece(state, name):
                return name
    if stage == "mid":
        for name in ("Hydreigon ex", "Mega Gengar ex", "Rare Candy", "Toxtricity", "Fezandipiti ex", "Pecharunt ex"):
            if name in missing_evolution or name in missing_support or needs_piece(state, name):
                return name
    for name in ("Deino", "Gastly", "Toxel", "Fezandipiti ex", "Pecharunt ex"):
        if name in missing_core or name in missing_support:
            if name == "Deino" and count_in_play(state, "Deino") >= 2:
                continue
            return name
    return (missing_evolution + missing_support + missing_core + [""])[0]


def needs_piece(state: Any, name: str) -> bool:
    if name == "Hydreigon ex":
        return has_in_play(state, "Deino") and not has_in_play(state, "Hydreigon ex")
    if name == "Mega Gengar ex":
        return has_in_play(state, "Gastly") and not has_in_play(state, "Mega Gengar ex")
    if name == "Rare Candy":
        return has_in_play(state, "Deino") and has_in_hand(state, "Hydreigon ex") and not has_in_hand(state, "Rare Candy")
    if name == "Crispin":
        return has_in_play(state, "Hydreigon ex")
    return False


def setup_urgency_score(state: Any, complete: bool, missing_core: List[str], missing_evolution: List[str], missing_support: List[str]) -> float:
    if complete:
        return 0.0
    score = 500.0
    if len(bench_pokemon(state)) <= 1:
        score += 4500.0
    if bench_space(state) > 0 and missing_core:
        score += 2600.0
    if missing_evolution:
        score += 1800.0
    if missing_support and len(bench_pokemon(state)) <= 2:
        score += 1200.0
    return score


def dedupe(values: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for value in values:
        if value not in seen:
            out.append(value)
            seen.add(value)
    return out


def target_field_status_debug(state: Any) -> dict[str, Any]:
    goal = compute_deck_goal_state(state)
    return {
        "hydreigon_chains": f"{goal.hydreigon_chains_current}/2",
        "mega_gengar_chains": f"{goal.gengar_chains_current}/1",
        "toxtricity_chains": f"{goal.toxtricity_chains_current}/1",
        "fezandipiti_ex": goal.has_fezandipiti_ex,
        "pecharunt_ex": goal.has_pecharunt_ex,
        "next_best_setup_piece": goal.next_best_setup_piece,
        "setup_urgency": goal.setup_urgency,
    }
