from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from action_classifier import ActionCategory, classify_legal_option
from deck_profile import load_profile
from state_eval import (
    OPT_ATTACK,
    OPT_END,
    OPT_PLAY,
    active_pokemon,
    attach_target_from_option,
    bench_pokemon,
    card_id,
    card_id_from_option,
    deck_count,
    getv,
    hand_count,
    option_type,
    pokemon_energy_count,
    prize_count,
)
from core.danger_evaluator import CRITICAL, HIGH, evaluate_danger, our_pokemon_knocked_out_last_turn
from core.energy_planner import score_energy_option
from core.evolution_planner import hydreigon_evolution_available, rare_candy_line_ready
from core.mega_gengar_planner import mega_gengar_evolution_available, mega_gengar_line_live
from core.opponent_model import OpponentThreat, infer_opponent_next_turn_threat
from core.pivot_planner import score_pivot_option
from core.priority_tables import CARD_IDS, SUPPORT_LIABILITY_IDS, canonical_name_from_id, count_in_play, has_in_hand, has_in_play
from core.resource_planner import should_attach_energy_this_turn, should_spend_supporter_this_turn
from core.supporter_planner import hand_playability_score


EARLY = "EARLY"
MID = "MID"
LATE = "LATE"


@dataclass(frozen=True)
class RoundPlan:
    game_stage: str
    board_goal: str
    primary_attacker_goal: str
    secondary_attacker_goal: str
    supporter_goal: str
    energy_goal: str
    evolution_goal: str
    search_goal: str
    danger_goal: str
    attack_goal: str
    pass_allowed: bool
    reason: str
    weights: Dict[str, float] = field(default_factory=dict)
    opponent_model: Optional[OpponentThreat] = None


def build_round_plan(state: Any, opponent_model: Any = None, deck_profile: Any = None) -> RoundPlan:
    profile = deck_profile or load_profile()
    threat = opponent_model or infer_opponent_next_turn_threat(state)
    danger = evaluate_danger(state)
    stage = determine_game_stage(state, threat)
    hydreigon_online = hydreigon_is_online(state)
    hydreigon_present = has_in_play(state, "Hydreigon ex")
    gengar_present = has_in_play(state, "Mega Gengar ex")
    gengar_live = mega_gengar_line_live(state)
    deino_count = count_in_play(state, "Deino")
    bench_count = len(bench_pokemon(state))
    weak_hand = hand_count(state) <= 4 or hand_playability_score(state) < 180.0
    supporter = should_spend_supporter_this_turn(state)
    energy = should_attach_energy_this_turn(state)

    emergency_board = bench_count <= 1
    if stage == EARLY:
        board_goal = "establish basics" if bench_count <= 2 else "stabilize setup board"
        primary_goal = "build Mega Gengar ex or Hydreigon ex, whichever attacker line is live first"
        secondary_goal = "keep Toxel available for Call for Family; Toxtricity is not an attacker"
        supporter_goal = "use Lillie, Petrel, Dawn, or Secret Box to find Poffin/Basics" if emergency_board else "use Lillie's Determination if hand is weak" if weak_hand else "hold Supporter if strong evolution/search play is ready"
        energy_goal = "attach Metal/Psychic only to the Deino line; Darkness can support Hydreigon or Mega Gengar"
        evolution_goal = "evolve the fastest live attacker line: Haunter to Mega Gengar ex or Rare Candy/Zweilous to Hydreigon ex"
        search_goal = "find one each of Deino, Gastly, and Toxel; then Fezandipiti ex/Pecharunt ex via Call for Family if possible" if emergency_board else "find missing Deino, Gastly, Toxel, then Rare Candy/Hydreigon ex or Haunter/Mega Gengar ex"
        attack_goal = "attack only for KO or after setup actions"
    elif stage == MID:
        board_goal = "prepare backup attacker before trade"
        primary_goal = "attack with Mega Gengar ex or Hydreigon ex based on fastest prize route"
        secondary_goal = "keep Toxtricity as support only; do not spend Energy or attacks on it"
        supporter_goal = "use Boss, Crispin, Lillie, or disruption when it improves the trade"
        energy_goal = "complete the fastest live attacker: Darkness to Mega Gengar, Metal/Psychic to Hydreigon"
        evolution_goal = "finish whichever attacker line is closest; Mega Gengar ex is a damage dealer, not just backup"
        search_goal = "find missing attacker, Energy, recovery, or disruption"
        attack_goal = "attack for KO or strong two-turn prize route"
    else:
        board_goal = "protect final prize map"
        primary_goal = "use Mega Gengar ex or Hydreigon ex for final prize route"
        secondary_goal = "avoid extra liabilities unless they create a winning line"
        supporter_goal = "Boss for game, disruption to block game, draw only if safe"
        energy_goal = "attach only to final attacker"
        evolution_goal = "evolve only if it affects the final prize route"
        search_goal = "search for winning piece or final attacker only"
        attack_goal = "attack if it wins, KOs, or forces a bad prize trade"

    pass_allowed = not any(
        [
            supporter.should_spend,
            energy.should_spend,
            hydreigon_evolution_available(state),
            mega_gengar_evolution_available(state),
            danger.severity in (HIGH, CRITICAL) and positive_pivot_available(state),
            bench_count <= 1 and basic_or_setup_search_available(state),
            our_pokemon_knocked_out_last_turn(state) and fezandipiti_option_available(state),
        ]
    )
    if option_attack_can_ko(state):
        pass_allowed = False

    if danger.severity in (HIGH, CRITICAL):
        danger_goal = danger.reason
    elif threat.can_boss_benched_ex_for_game:
        danger_goal = "avoid giving opponent easy final prizes"
    elif threat.likely_ex_heavy:
        danger_goal = "Mega Gengar prize reduction may matter against ex attackers"
    elif threat.likely_one_prize:
        danger_goal = "avoid overbenching ex against one-prize pressure"
    else:
        danger_goal = "maintain backup attacker and safe resource use"

    reason = (
        f"{stage}: Hydreigon online={hydreigon_online}, Mega Gengar in play={gengar_present}, "
        f"Mega Gengar line live={gengar_live}, "
        f"bench={bench_count}, danger={danger.severity}."
    )
    return RoundPlan(
        game_stage=stage,
        board_goal=board_goal,
        primary_attacker_goal=primary_goal,
        secondary_attacker_goal=secondary_goal,
        supporter_goal=supporter_goal,
        energy_goal=energy_goal,
        evolution_goal=evolution_goal,
        search_goal=search_goal,
        danger_goal=danger_goal,
        attack_goal=attack_goal,
        pass_allowed=pass_allowed,
        reason=reason,
        weights=stage_weights(stage, threat),
        opponent_model=threat,
    )


def score_option_against_round_plan(state: Any, option: Any, base_score: float, round_plan: RoundPlan) -> float:
    action = classify_legal_option(state, option, 0)
    cid = card_id_from_option(state, option)
    name = canonical_name_from_id(cid)
    category = action.category
    weights = round_plan.weights
    stage = round_plan.game_stage
    bonus = 0.0
    deino_count = count_in_play(state, "Deino")
    bench_count = len(bench_pokemon(state))
    hydreigon_online = hydreigon_is_online(state)
    hydreigon_stable = hydreigon_online or has_in_play(state, "Hydreigon ex")
    threat = round_plan.opponent_model or infer_opponent_next_turn_threat(state)
    try:
        from core.setup_recovery_planner import emergency_setup_needed, score_emergency_setup_play, weak_board_ignores_prize_liability, whole_team_setup_score

        if emergency_setup_needed(state):
            bonus += score_emergency_setup_play(state, option)
        team_score = whole_team_setup_score(state, cid)
        if team_score:
            bonus += min(2200.0, team_score * 0.25)
        ignore_prize_liability = weak_board_ignores_prize_liability(state)
    except Exception:
        ignore_prize_liability = False

    if category in (ActionCategory.PLAY_BASIC_TO_BENCH, ActionCategory.SETUP_CHOOSE_BENCH):
        if stage == EARLY and bench_count == 0:
            bonus += weights["bench_safety"]
        elif stage == EARLY and bench_count == 1:
            bonus += weights["bench_safety"] * 0.55
        if name == "Deino":
            bonus += weights["deino_setup"] if deino_count < 2 else weights["deino_setup"] * 0.2
        elif name in {"Gastly", "Toxel"}:
            if name == "Gastly":
                bonus += weights["mega_gengar"] * (0.8 if not has_in_play(state, "Gastly") else 0.25)
            bonus += weights["deino_setup"] * (0.35 if deino_count else 0.15)
        elif cid in SUPPORT_LIABILITY_IDS:
            if ignore_prize_liability:
                bonus += weights["bench_safety"]
            elif stage == LATE and threat.can_boss_benched_ex_for_game:
                bonus -= weights["avoid_final_prizes"]
            elif stage == EARLY and bench_count <= 1 and not safer_basic_available(state):
                bonus += weights["bench_safety"] * 0.8
            else:
                bonus -= 250.0

    if category in (ActionCategory.EVOLVE, ActionCategory.RARE_CANDY_EVOLVE):
        if name == "Hydreigon ex" or category == ActionCategory.RARE_CANDY_EVOLVE:
            bonus += weights["hydreigon_setup"]
            if rare_candy_line_ready(state):
                bonus += 700.0
        elif name == "Mega Gengar ex":
            bonus += weights["mega_gengar"] + 500.0
            if has_in_play(state, "Haunter"):
                bonus += 1800.0
            if threat.likely_ex_heavy:
                bonus += 1000.0
        elif name in {"Zweilous", "Haunter", "Toxtricity"}:
            bonus += 300.0
            if name == "Haunter" and (has_in_hand(state, "Mega Gengar ex") or threat.has_rulebox_attacker):
                bonus += weights["mega_gengar"] + 700.0

    if category == ActionCategory.DRAW_OR_SEARCH or name in {"Buddy-Buddy Poffin", "Poke Pad", "Ultra Ball", "Secret Box"}:
        if name == "Buddy-Buddy Poffin":
            if stage == EARLY and (deino_count < 2 or bench_count <= 2):
                bonus += weights["deino_setup"]
            elif stage == LATE:
                bonus -= 300.0
        elif name == "Poke Pad":
            bonus += 1450.0 if ignore_prize_liability else 450.0 if stage != LATE else -150.0
        elif name in {"Secret Box", "Team Rocket's Petrel", "Dawn"} and ignore_prize_liability:
            bonus += weights["bench_safety"] + weights["supporter"]
        elif name == "Ultra Ball":
            if mega_gengar_line_live(state):
                bonus += weights["mega_gengar"] + 550.0
            if hydreigon_evolution_available(state) or (has_in_play(state, "Deino") and has_in_hand(state, "Rare Candy")):
                bonus += weights["hydreigon_setup"]
        elif cid == CARD_IDS["Fezandipiti ex"] and our_pokemon_knocked_out_last_turn(state):
            bonus += weights["fezandipiti"]

    if category == ActionCategory.PLAY_SUPPORTER:
        if deck_count(state) <= 3 and name == "Lillie's Determination":
            bonus -= 5000.0
        try:
            from turn_sequencer import free_draw_or_search_ability_exists

            if name == "Lillie's Determination" and free_draw_or_search_ability_exists(state):
                bonus -= 1200.0
        except Exception:
            pass
        if name == "Lillie's Determination" and (hand_count(state) <= 4 or hand_playability_score(state) < 180.0):
            bonus += weights["supporter"]
        if name == "Crispin":
            bonus += weights["energy"] if hydreigon_stable or has_in_play(state, "Deino") or mega_gengar_line_live(state) else 100.0
        if "Boss" in name:
            bonus += weights["winning_line"] if stage == LATE else 250.0
        if name in {"Team Rocket's Petrel", "Special Red Card"}:
            bonus += min(900.0, 400.0 + threat.hand_size * 45.0) if threat.can_take_active_ko or threat.hand_size >= 6 else 150.0

    if category == ActionCategory.ATTACH_ENERGY:
        energy_score = score_energy_option(state, option)
        if energy_score >= 500.0:
            bonus += weights["energy"]
            target = attach_target_from_option(state, option)
            target_name = canonical_name_from_id(card_id(target))
            if target_name in {"Mega Gengar ex", "Haunter", "Gastly"}:
                bonus += weights["mega_gengar"] * (0.75 if stage != LATE else 0.35)
            if stage == LATE:
                bonus += weights["final_attacker"]

    if category == ActionCategory.USE_ABILITY:
        if name == "Fezandipiti ex" and our_pokemon_knocked_out_last_turn(state):
            bonus += weights["fezandipiti"]
        if name == "Pecharunt ex":
            bonus += weights["pecharunt"] if score_pivot_option(state, option) > 0 else -500.0
        if name == "Mega Gengar ex" and threat.likely_ex_heavy:
            bonus += weights["mega_gengar"]

    if category in (ActionCategory.RETREAT, ActionCategory.SWITCH_ACTIVE):
        pivot_score = score_pivot_option(state, option)
        if pivot_score > 0:
            bonus += weights["pecharunt"] * 0.5 + min(900.0, pivot_score * 0.25)

    if category == ActionCategory.ATTACK:
        attacker_name = canonical_name_from_id(card_id(active_pokemon(state)))
        if base_score >= 10000.0:
            bonus += weights["winning_line"] if stage == LATE else 1200.0
        elif stage == EARLY and useful_setup_option_available(state):
            bonus -= 450.0
        elif stage in (MID, LATE):
            bonus += 250.0
        if attacker_name == "Hydreigon ex":
            bonus += weights["hydreigon_attack"]
        elif attacker_name == "Mega Gengar ex":
            bonus += weights["mega_gengar"] + 450.0 if stage != EARLY or mega_gengar_line_live(state) else 0.0

    if option_type(option) == OPT_END or category == ActionCategory.END_TURN:
        if round_plan.pass_allowed:
            bonus += 150.0
        else:
            bonus -= 2200.0

    return bonus


def determine_game_stage(state: Any, threat: OpponentThreat) -> str:
    our_prizes = prize_count(state)
    opp_prizes = prize_count(state, state.opponent_index)
    bench_count = len(bench_pokemon(state))
    if bench_count <= 1 and not hydreigon_is_online(state) and not has_in_play(state, "Mega Gengar ex"):
        return EARLY
    if our_prizes <= 2 or opp_prizes <= 2:
        return LATE
    if hydreigon_is_online(state) and our_prizes <= 4 and opp_prizes <= 4:
        return MID
    if (has_in_play(state, "Hydreigon ex") or has_in_play(state, "Mega Gengar ex")) and our_prizes <= 4:
        return MID
    if not has_in_play(state, "Hydreigon ex") or bench_count <= 2 or our_prizes >= 5:
        return EARLY
    if threat.can_take_active_ko or threat.has_rulebox_attacker:
        return MID
    return MID


def stage_weights(stage: str, threat: OpponentThreat) -> Dict[str, float]:
    if stage == EARLY:
        return {
            "bench_safety": 1000.0,
            "deino_setup": 1000.0,
            "hydreigon_setup": 900.0,
            "supporter": 800.0,
            "energy": 700.0,
            "mega_gengar": 1150.0,
            "fezandipiti": 450.0,
            "pecharunt": 350.0,
            "hydreigon_attack": 200.0,
            "winning_line": 1400.0,
            "avoid_final_prizes": 250.0,
            "final_attacker": 200.0,
        }
    if stage == MID:
        gengar = 1200.0 if threat.likely_ex_heavy else 900.0 if not threat.likely_one_prize else 600.0
        return {
            "bench_safety": 450.0,
            "deino_setup": 550.0,
            "hydreigon_setup": 1200.0,
            "supporter": 700.0,
            "energy": 700.0,
            "mega_gengar": gengar,
            "fezandipiti": 1000.0,
            "pecharunt": 800.0,
            "hydreigon_attack": 1200.0,
            "winning_line": 1600.0,
            "avoid_final_prizes": 700.0,
            "final_attacker": 600.0,
        }
    gengar_late = 1100.0 if threat.likely_ex_heavy else 650.0
    return {
        "bench_safety": 150.0,
        "deino_setup": 150.0,
        "hydreigon_setup": 550.0,
        "supporter": 650.0,
        "energy": 1200.0,
        "mega_gengar": gengar_late,
        "fezandipiti": 350.0,
        "pecharunt": 650.0,
        "hydreigon_attack": 900.0,
        "winning_line": 2000.0,
        "avoid_final_prizes": 1500.0,
        "final_attacker": 1200.0,
    }


def hydreigon_is_online(state: Any) -> bool:
    for pokemon in [active_pokemon(state)] + bench_pokemon(state):
        if canonical_name_from_id(card_id(pokemon)) != "Hydreigon ex":
            continue
        if pokemon_energy_count(pokemon) >= 2:
            return True
    return False


def basic_or_setup_search_available(state: Any) -> bool:
    for idx, option in enumerate(state.options):
        action = classify_legal_option(state, option, idx)
        if action.category == ActionCategory.PLAY_BASIC_TO_BENCH:
            return True
        name = action.card_name or canonical_name_from_id(card_id_from_option(state, option))
        if name in {"Buddy-Buddy Poffin", "Poke Pad", "Ultra Ball", "Secret Box", "Team Rocket's Petrel", "Dawn", "Lillie's Determination"}:
            return True
    return False


def fezandipiti_option_available(state: Any) -> bool:
    for idx, option in enumerate(state.options):
        action = classify_legal_option(state, option, idx)
        if action.card_id == CARD_IDS["Fezandipiti ex"] or action.card_name == "Fezandipiti ex":
            return True
    return False


def option_attack_can_ko(state: Any) -> bool:
    for idx, option in enumerate(state.options):
        action = classify_legal_option(state, option, idx)
        if action.category == ActionCategory.ATTACK:
            # The main policy scores KO attacks above 10000, but this function
            # avoids importing policy and stays conservative.
            opponent = active_pokemon(state, state.opponent_index)
            active = active_pokemon(state)
            if not opponent or not active:
                continue
            from card_db import get_db

            attack = get_db().get_attack(getv(option, "attackId"))
            if attack and int(getattr(attack, "damage", 0) or 0) >= int(getv(opponent, "hp", 9999) or 9999):
                return True
    return False


def safer_basic_available(state: Any) -> bool:
    for idx, option in enumerate(state.options):
        action = classify_legal_option(state, option, idx)
        if action.card_id in {CARD_IDS["Deino"], CARD_IDS["Gastly"], CARD_IDS["Toxel"]}:
            return True
    return False


def useful_setup_option_available(state: Any) -> bool:
    for idx, option in enumerate(state.options):
        action = classify_legal_option(state, option, idx)
        if action.category in (
            ActionCategory.PLAY_BASIC_TO_BENCH,
            ActionCategory.DRAW_OR_SEARCH,
            ActionCategory.EVOLVE,
            ActionCategory.RARE_CANDY_EVOLVE,
            ActionCategory.ATTACH_ENERGY,
            ActionCategory.PLAY_SUPPORTER,
        ):
            if option_type(option) != OPT_ATTACK:
                return True
    return False


def positive_pivot_available(state: Any) -> bool:
    for option in state.options:
        if score_pivot_option(state, option) > 500.0:
            return True
    return False
