from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List

from state_eval import active_pokemon, bench_space, card_id, getv, iter_in_play, pokemon_energy_count, prize_count
from core.priority_tables import canonical_name_from_id, has_in_hand


EARLY = "EARLY"
MID = "MID"
LATE = "LATE"

TARGET_BOARD_CORE = {
    "palafin_engine": ["Finizen", "Palafin", "Palafin ex"],
    "dragonite_engine": ["Dratini", "Dragonair", "Mega Dragonite ex"],
    "switch_engine": ["Surfing Beach", "Switch", "Air Balloon", "Kieran", "Mega Dragonite ex"],
    "support_engine": ["Tatsugiri", "Lillie's Determination", "Team Rocket's Petrel", "Hilda", "Crispin"],
}


@dataclass(frozen=True)
class TargetBoardReport:
    finizen_count: int = 0
    palafin_count: int = 0
    palafin_ex_count: int = 0
    dratini_count: int = 0
    dragonair_count: int = 0
    mega_dragonite_ex_count: int = 0
    has_tatsugiri: bool = False
    open_bench_slots: int = 0
    missing_core_pieces: List[str] = field(default_factory=list)
    missing_switch_engine: List[str] = field(default_factory=list)
    missing_energy: List[str] = field(default_factory=list)
    next_best_setup_piece: str = ""
    board_stage: str = EARLY
    reason: str = ""


def evaluate_target_board(state: Any) -> TargetBoardReport:
    counts = {
        "Finizen": 0,
        "Palafin": 0,
        "Palafin ex": 0,
        "Dratini": 0,
        "Dragonair": 0,
        "Mega Dragonite ex": 0,
        "Tatsugiri": 0,
    }
    water_ready = False
    lightning_ready = False
    for _, _, pokemon in iter_in_play(state):
        name = canonical_name_from_id(card_id(pokemon))
        if name in counts:
            counts[name] += 1
        if name in {"Palafin ex", "Palafin", "Finizen"} and pokemon_energy_count(pokemon) > 0:
            water_ready = True
        if name in {"Mega Dragonite ex", "Dragonair", "Dratini"} and pokemon_energy_count(pokemon) > 0:
            lightning_ready = True

    missing_core: List[str] = []
    if counts["Finizen"] < 2 and counts["Palafin ex"] == 0:
        missing_core.append("second Finizen")
    if counts["Finizen"] + counts["Palafin"] + counts["Palafin ex"] == 0:
        missing_core.insert(0, "Finizen")
    if counts["Palafin"] == 0 and counts["Palafin ex"] == 0:
        missing_core.append("Palafin")
    if counts["Dratini"] + counts["Dragonair"] + counts["Mega Dragonite ex"] == 0:
        missing_core.append("Dratini")

    missing_switch: List[str] = []
    if not any(has_in_hand(state, name) for name in ("Surfing Beach", "Switch", "Air Balloon", "Kieran")):
        active_name = canonical_name_from_id(card_id(active_pokemon(state)))
        if active_name not in {"Mega Dragonite ex"}:
            missing_switch.append("switch engine")

    missing_energy: List[str] = []
    if counts["Palafin ex"] > 0 and not water_ready:
        missing_energy.append("Water for Palafin ex")
    if counts["Dragonair"] + counts["Mega Dragonite ex"] > 0 and not lightning_ready:
        missing_energy.append("Lightning for Dragonite")

    turn = int(getv(state.current, "turn", 0) or 0)
    our_prizes = prize_count(state)
    opp_prizes = prize_count(state, state.opponent_index)
    if our_prizes <= 2 or opp_prizes <= 2:
        stage = LATE
    elif counts["Palafin ex"] > 0 or (counts["Palafin"] > 0 and not missing_switch):
        stage = MID
    elif turn <= 4 or counts["Finizen"] < 2:
        stage = EARLY
    else:
        stage = MID

    next_piece = ""
    for piece in ("Finizen", "second Finizen", "Palafin", "Surfing Beach", "Dratini", "Dragonair", "Mega Dragonite ex"):
        if piece in missing_core or piece in missing_switch:
            next_piece = piece
            break
    if not next_piece and missing_energy:
        next_piece = missing_energy[0]

    reason = f"{stage}: Finizen={counts['Finizen']}, Palafin={counts['Palafin']}, Palafin ex={counts['Palafin ex']}, Dragonite line={counts['Dratini']}/{counts['Dragonair']}/{counts['Mega Dragonite ex']}."
    return TargetBoardReport(
        finizen_count=counts["Finizen"],
        palafin_count=counts["Palafin"],
        palafin_ex_count=counts["Palafin ex"],
        dratini_count=counts["Dratini"],
        dragonair_count=counts["Dragonair"],
        mega_dragonite_ex_count=counts["Mega Dragonite ex"],
        has_tatsugiri=counts["Tatsugiri"] > 0,
        open_bench_slots=bench_space(state),
        missing_core_pieces=missing_core,
        missing_switch_engine=missing_switch,
        missing_energy=missing_energy,
        next_best_setup_piece=next_piece,
        board_stage=stage,
        reason=reason,
    )


def target_board_goal_names() -> dict[str, list[str]]:
    return {key: list(value) for key, value in TARGET_BOARD_CORE.items()}


def low_bench_needs_setup(state: Any) -> bool:
    report = evaluate_target_board(state)
    return report.open_bench_slots > 0 and (report.finizen_count + report.palafin_count + report.palafin_ex_count < 2)
