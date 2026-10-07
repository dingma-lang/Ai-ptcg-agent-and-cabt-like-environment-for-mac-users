from __future__ import annotations

from typing import Any, List, Sequence

from action_classifier import classify_legal_option
from state_eval import active_pokemon, attached_card_ids, bench_pokemon, card_id, getv, hand_cards, pokemon_energy_count, prize_count
from core.danger_evaluator import evaluate_danger, our_pokemon_knocked_out_last_turn
from core.opponent_model import infer_opponent_next_turn_threat
from core.pivot_planner import best_darkness_pivot_target
from core.priority_tables import CARD_IDS, canonical_name_from_id, count_in_play, has_in_hand, has_in_play
from core.resource_planner import should_attach_energy_this_turn, should_spend_supporter_this_turn
from core.round_plan import RoundPlan


def explain_turn_thought_process(state: Any, round_plan: RoundPlan, chosen_action: Sequence[int]) -> List[str]:
    from decision_reason import explain_choice

    danger = evaluate_danger(state)
    threat = round_plan.opponent_model or infer_opponent_next_turn_threat(state)
    supporter = should_spend_supporter_this_turn(state)
    energy = should_attach_energy_this_turn(state)
    try:
        from core.deck_operating_system import compute_deck_goal_state
        from core.recovery_timing_planner import recovery_threshold_debug
        from core.stuck_recovery import detect_stuck_recovery
        from core.supporter_router import supporter_debug

        deck_goal = compute_deck_goal_state(state)
        recovery = recovery_threshold_debug(state)
        stuck = detect_stuck_recovery(state, getattr(state, "options", []) or [])
        routed_supporter = supporter_debug(state)
    except Exception:
        deck_goal = None
        recovery = {}
        stuck = None
        routed_supporter = {}
    petrel_in_hand = has_in_hand(state, "Team Rocket's Petrel")
    return [
        f"Game stage: {round_plan.game_stage}",
        f"Prize counts: ours {prize_count(state)}, opponent {prize_count(state, state.opponent_index)}",
        (
            f"Target field: Hydreigon {deck_goal.hydreigon_chains_current}/2; "
            f"Mega Gengar {deck_goal.gengar_chains_current}/1; "
            f"Toxtricity {deck_goal.toxtricity_chains_current}/1; "
            f"Fezandipiti={deck_goal.has_fezandipiti_ex}; Pecharunt={deck_goal.has_pecharunt_ex}; "
            f"next={deck_goal.next_best_setup_piece}"
        )
        if deck_goal
        else "Target field: unavailable",
        f"Our board: Active {pokemon_name(active_pokemon(state))}; Bench {', '.join(pokemon_name(p) for p in bench_pokemon(state)) or 'empty'}",
        f"Opponent board: Active {pokemon_name(active_pokemon(state, state.opponent_index))}; Bench {', '.join(pokemon_name(p) for p in bench_pokemon(state, state.opponent_index)) or 'empty'}",
        f"Hydreigon status: {hydreigon_status(state)}",
        f"Mega Gengar status: {mega_gengar_status(state)}",
        f"Fezandipiti status: {fezandipiti_status(state)}",
        f"Pecharunt status: {pecharunt_status(state)}",
        f"Supporter status: {'unused' if not bool(getv(state.current, 'supporterPlayed', False)) else 'used'}; best={routed_supporter.get('best_supporter', '')}; {routed_supporter.get('reason', supporter.reason)}",
        f"Energy status: {'unused' if not bool(getv(state.current, 'energyAttached', False)) else 'used'}; {energy.reason}",
        f"Search access: Poffin in hand={has_in_hand(state, 'Buddy-Buddy Poffin')}; Petrel legal={petrel_in_hand}; Secret Box legal={has_in_hand(state, 'Secret Box')}; Dawn legal={has_in_hand(state, 'Dawn')}; Crispin legal={has_in_hand(state, 'Crispin')}",
        f"Recovery thresholds: Energy discard={recovery.get('energy_discard_count', 0)}; Pokemon discard={recovery.get('pokemon_discard_count', 0)}; key line lost={recovery.get('key_line_lost', False)}",
        f"Stuck detection: {bool(stuck and stuck.is_stuck)}; {getattr(stuck, 'reason', '') if stuck else ''}",
        f"Danger level: {danger.severity}; {danger.reason}",
        f"Opponent read: ex-heavy={threat.likely_ex_heavy}, one-prize={threat.likely_one_prize}, Boss-game-risk={threat.can_boss_benched_ex_for_game}",
        f"Board goal: {round_plan.board_goal}",
        f"Main attacker goal: {round_plan.primary_attacker_goal}",
        f"Secondary attacker goal: {round_plan.secondary_attacker_goal}",
        "Resource goal: use Supporter/Energy unless clearly held",
        f"Chosen action: {chosen_label(state, chosen_action)}",
        f"Reason: {explain_choice(state, chosen_action, [0.0] * len(state.options)) if chosen_action else 'Decline optional selection'}",
    ]


def pokemon_name(pokemon: Any) -> str:
    return canonical_name_from_id(card_id(pokemon)) or "none"


def hydreigon_status(state: Any) -> str:
    if has_in_play(state, "Hydreigon ex"):
        return energy_line_status(state, "Hydreigon ex")
    if has_in_play(state, "Zweilous"):
        return "Zweilous in play"
    if has_in_play(state, "Deino"):
        return f"Deino in play ({count_in_play(state, 'Deino')})"
    return "no Deino"


def mega_gengar_status(state: Any) -> str:
    if has_in_play(state, "Mega Gengar ex"):
        return energy_line_status(state, "Mega Gengar ex")
    if has_in_play(state, "Haunter"):
        return "Haunter in play"
    if has_in_play(state, "Gastly"):
        return "Gastly in play"
    return "no Gastly"


def energy_line_status(state: Any, name: str) -> str:
    rows: List[str] = []
    for pokemon in [active_pokemon(state)] + bench_pokemon(state):
        if pokemon_name(pokemon) != name:
            continue
        ids = attached_card_ids(pokemon, "energyCards") + attached_card_ids(pokemon, "energies")
        if not ids and pokemon_energy_count(pokemon):
            rows.append(f"{name} in play with {pokemon_energy_count(pokemon)} Energy")
        else:
            rows.append(f"{name} in play with Energy {ids or []}")
    return "; ".join(rows) if rows else f"{name} not in play"


def fezandipiti_status(state: Any) -> str:
    in_play = has_in_play(state, "Fezandipiti ex")
    in_hand = has_in_hand(state, "Fezandipiti ex")
    ko = our_pokemon_knocked_out_last_turn(state)
    risky = prize_count(state, state.opponent_index) <= 2
    return f"in_play={in_play}, in_hand={in_hand}, ability_after_KO={ko and in_play}, risky_to_bench={risky}"


def pecharunt_status(state: Any) -> str:
    target = best_darkness_pivot_target(state)
    return f"in_play={has_in_play(state, 'Pecharunt ex')}, pivot_target={pokemon_name(target) if target else 'none'}"


def chosen_label(state: Any, chosen_action: Sequence[int]) -> str:
    if not chosen_action:
        return "none"
    idx = int(chosen_action[0])
    if not (0 <= idx < len(state.options)):
        return "unknown"
    action = classify_legal_option(state, state.options[idx], idx)
    card = action.card_name or canonical_name_from_id(action.card_id)
    if action.attack_name:
        return f"{action.category} {action.attack_name}"
    return f"{action.category} {card}".strip()
