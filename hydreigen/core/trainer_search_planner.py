from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from state_eval import OPT_CARD, OPT_PLAY, bench_space, card_id_from_option, option_type
from core.deck_operating_system import compute_deck_goal_state
from core.priority_tables import canonical_name_from_id, count_in_play, has_in_hand, has_in_play
from core.recovery_timing_planner import energy_discard_count, key_line_lost, pokemon_discard_count


@dataclass(frozen=True)
class TrainerNeed:
    name: str
    score: float
    reason: str


def best_petrel_trainer_need(state: Any) -> TrainerNeed:
    try:
        from core.combo_presence_planner import gengar_bridge_needed, hydreigon_bridge_needed

        if hydreigon_bridge_needed(state):
            return TrainerNeed("Rare Candy", 10000.0, "Use Petrel for Rare Candy because Deino plus Hydreigon ex needs an evolution bridge.")
        if gengar_bridge_needed(state):
            return TrainerNeed("Poke Pad", 8600.0, "Use Petrel for Poke Pad because Gastly plus Mega Gengar ex needs Haunter.")
    except Exception:
        pass
    if rare_candy_needed_now(state):
        return TrainerNeed("Rare Candy", 9500.0, "Use Petrel for Rare Candy because Hydreigon ex can evolve this turn.")
    if poffin_needed(state) and not has_in_hand(state, "Buddy-Buddy Poffin"):
        return TrainerNeed("Buddy-Buddy Poffin", 9000.0, "Use Petrel for Buddy-Buddy Poffin because target field basics are missing.")
    if ultra_ball_needed(state):
        return TrainerNeed("Ultra Ball", 7300.0, "Use Petrel for Ultra Ball because exact Pokemon is needed.")
    if secret_box_needed(state):
        return TrainerNeed("Secret Box", 6900.0, "Use Petrel for Secret Box because a multi-piece Trainer package is needed.")
    if energy_discard_count(state) >= 4:
        return TrainerNeed("Energy Recycler", 5400.0, "Use Petrel for Energy Recycler because 4+ Energy are in discard.")
    if pokemon_discard_count(state) >= 4 or key_line_lost(state):
        return TrainerNeed("Sacred Ash", 5200.0, "Use Petrel for Sacred Ash because key Pokemon recovery threshold is met.")
    if night_stretcher_needed(state):
        return TrainerNeed("Night Stretcher", 5000.0, "Use Petrel for Night Stretcher because exact discard recovery is needed.")
    if disruption_needed(state):
        return TrainerNeed("Special Red Card", 3600.0, "Use Petrel for disruption because setup is stable.")
    return TrainerNeed("", 0.0, "No exact Trainer need.")


def score_petrel_play(state: Any, option: Any) -> float:
    if option_type(option) != OPT_PLAY or canonical_name_from_id(card_id_from_option(state, option)) != "Team Rocket's Petrel":
        return 0.0
    need = best_petrel_trainer_need(state)
    if not need.name:
        return 0.0
    if need.name == "Buddy-Buddy Poffin" and has_in_hand(state, "Buddy-Buddy Poffin"):
        return -3500.0
    return need.score


def score_petrel_target_selection(state: Any, cid: Optional[int], name: str) -> float:
    if name == "Crispin":
        return -5000.0
    try:
        from core.combo_presence_planner import score_combo_search_target

        combo_score = score_combo_search_target(state, cid, "Team Rocket's Petrel")
        if combo_score:
            return combo_score
    except Exception:
        pass
    need = best_petrel_trainer_need(state)
    if name == "Buddy-Buddy Poffin" and has_in_hand(state, "Buddy-Buddy Poffin"):
        return -6000.0
    if name == "Poke Pad" and has_in_hand(state, "Buddy-Buddy Poffin"):
        return 2000.0
    if not need.name:
        return generic_trainer_score(state, name)
    if name == need.name:
        return need.score + 1000.0
    if name in {"Energy Recycler", "Sacred Ash"} and not recovery_trainer_ready(state, name):
        return -3500.0
    return generic_trainer_score(state, name)


def generic_trainer_score(state: Any, name: str) -> float:
    if name == "Rare Candy" and rare_candy_needed_now(state):
        return 8000.0
    if name == "Buddy-Buddy Poffin":
        return 6800.0 if poffin_needed(state) and not has_in_hand(state, "Buddy-Buddy Poffin") else -1800.0
    if name == "Ultra Ball" and ultra_ball_needed(state):
        return 6000.0
    if name == "Secret Box" and secret_box_needed(state):
        return 5600.0
    if name == "Energy Recycler":
        return 4600.0 if energy_discard_count(state) >= 4 else -2500.0
    if name == "Sacred Ash":
        return 4400.0 if pokemon_discard_count(state) >= 4 or key_line_lost(state) else -3000.0
    if name == "Night Stretcher" and night_stretcher_needed(state):
        return 4300.0
    return 0.0


def rare_candy_needed_now(state: Any) -> bool:
    return has_in_play(state, "Deino") and has_in_hand(state, "Hydreigon ex") and not has_in_hand(state, "Rare Candy") and count_in_play(state, "Hydreigon ex") < 2


def poffin_needed(state: Any) -> bool:
    goal = compute_deck_goal_state(state)
    return bench_space(state) > 0 and bool(set(goal.missing_core_pieces) & {"Deino", "Gastly", "Toxel"})


def ultra_ball_needed(state: Any) -> bool:
    goal = compute_deck_goal_state(state)
    return bool(goal.missing_evolution_pieces or goal.missing_core_pieces)


def secret_box_needed(state: Any) -> bool:
    goal = compute_deck_goal_state(state)
    return goal.setup_urgency >= 2500.0 and not has_in_hand(state, "Secret Box")


def recovery_trainer_ready(state: Any, name: str) -> bool:
    if name == "Energy Recycler":
        return energy_discard_count(state) >= 4
    if name == "Sacred Ash":
        return pokemon_discard_count(state) >= 4 or key_line_lost(state)
    return True


def night_stretcher_needed(state: Any) -> bool:
    try:
        from core.recovery_timing_planner import exact_resource_needed_from_discard

        return exact_resource_needed_from_discard(state)
    except Exception:
        return False


def disruption_needed(state: Any) -> bool:
    try:
        from state_eval import hand_count

        return compute_deck_goal_state(state).target_board_complete and hand_count(state, state.opponent_index) >= 6
    except Exception:
        return False


def is_petrel_search_context(state: Any) -> bool:
    try:
        from core.priority_tables import context_source_name

        return context_source_name(state) == "Team Rocket's Petrel"
    except Exception:
        return False


def current_search_option_is_trainer(state: Any, option: Any) -> bool:
    if option_type(option) != OPT_CARD:
        return False
    name = canonical_name_from_id(card_id_from_option(state, option))
    return name in {
        "Buddy-Buddy Poffin",
        "Rare Candy",
        "Ultra Ball",
        "Secret Box",
        "Energy Recycler",
        "Sacred Ash",
        "Night Stretcher",
        "Battle Cage",
        "Air Balloon",
        "Special Red Card",
    }
