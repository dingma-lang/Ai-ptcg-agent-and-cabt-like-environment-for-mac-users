from __future__ import annotations

from typing import Any

from state_eval import OPT_EVOLVE, OPT_PLAY, attached_card_ids, bench_pokemon, card_id, card_id_from_option, deck_count, getv, hand_count, iter_in_play, option_type, pokemon_energy_count
from core.danger_evaluator import CRITICAL, HIGH, evaluate_danger, our_pokemon_knocked_out_last_turn
from core.priority_tables import canonical_name_from_id, deino_count, has_in_hand, has_in_play
from core.evolution_planner import rare_candy_line_ready
from core.mega_gengar_planner import mega_gengar_line_live


def hand_playability_score(state: Any) -> float:
    score = 0.0
    if deino_count(state) > 0:
        score += 40.0
    if rare_candy_line_ready(state):
        score += 300.0
    for name in ("Buddy-Buddy Poffin", "Ultra Ball", "Poke Pad", "Rare Candy"):
        if has_in_hand(state, name):
            score += 70.0
    if has_in_hand(state, "Hydreigon ex") and has_in_play(state, "Deino"):
        score += 80.0
    if has_in_hand(state, "Boss's Orders"):
        score -= 20.0
    if has_in_hand(state, "Energy Recycler"):
        score -= 20.0
    return score


def score_supporter_option(state: Any, option: Any) -> float:
    cid = card_id_from_option(state, option)
    name = canonical_name_from_id(cid)
    if not name:
        return 0.0
    if bool(getv(state.current, "supporterPlayed", False)):
        return -5000.0
    try:
        from core.setup_recovery_planner import emergency_setup_needed, stronger_board_action_legal

        emergency_setup = emergency_setup_needed(state) and not stronger_board_action_legal(state, getattr(state, "options", []) or [])
    except Exception:
        emergency_setup = False
    if name == "Lillie's Determination":
        try:
            from core.prize_availability_tracker import infer_card_availability
            from core.recovery_goal_planner import recovery_card_legal

            if infer_card_availability(state, None).all_deino_in_discard and recovery_card_legal(state):
                return -2500.0
        except Exception:
            pass
        try:
            from turn_sequencer import free_draw_or_search_ability_exists

            if free_draw_or_search_ability_exists(state):
                return -500.0
        except Exception:
            pass
        if deck_count(state) <= 3:
            return -9000.0
        try:
            from core.lillie_guard import useful_action_before_lillie

            precheck = useful_action_before_lillie(state)
            if precheck.should_wait:
                return -2600.0
        except Exception:
            pass
        if emergency_setup:
            return 9600.0
        danger = evaluate_danger(state)
        score = 7600.0
        playability = hand_playability_score(state)
        if hand_count(state) <= 3 and playability < 180.0:
            score += 900.0
        elif hand_count(state) <= 4 and playability < 220.0:
            score += 650.0
        if len(bench_pokemon(state)) <= 1:
            score += 800.0 if len(bench_pokemon(state)) == 0 else 500.0
        if deino_count(state) == 0 and not any(has_in_hand(state, card) for card in ("Buddy-Buddy Poffin", "Ultra Ball", "Poke Pad")):
            score += 700.0
        if deino_count(state) > 0 and not (has_in_hand(state, "Rare Candy") and has_in_hand(state, "Hydreigon ex")):
            score += 600.0 if deino_count(state) == 1 else 500.0
        if mega_gengar_line_live(state) and not has_in_play(state, "Mega Gengar ex"):
            score += 550.0
        if has_in_play(state, "Hydreigon ex") and not (has_in_hand(state, "Basic Metal Energy") or has_in_hand(state, "Basic Psychic Energy") or has_in_hand(state, "Crispin")):
            score += 500.0
        if our_pokemon_knocked_out_last_turn(state):
            score += 400.0
        if danger.severity in (HIGH, CRITICAL):
            score += 300.0
        if playability < 100.0:
            score += 300.0
        return score
    if name == "Crispin":
        energy_score = max(crispin_hydreigon_energy_score(state), crispin_mega_gengar_energy_score(state))
        if energy_score:
            return energy_score
        if has_in_play(state, "Hydreigon ex") or has_in_play(state, "Deino") or has_in_play(state, "Zweilous"):
            return 550.0
        if mega_gengar_line_live(state):
            return 520.0
        return 80.0
    if name == "Dawn":
        try:
            from core.fezandipiti_planner import score_post_ko_fezandipiti_enabler, score_pre_ko_fezandipiti_enabler

            post_ko_score = score_post_ko_fezandipiti_enabler(state, "Dawn")
            if post_ko_score:
                return post_ko_score
            pre_ko_score = score_pre_ko_fezandipiti_enabler(state, "Dawn")
            if pre_ko_score:
                return pre_ko_score
        except Exception:
            pass
        if emergency_setup:
            return 7600.0
        if our_pokemon_knocked_out_last_turn(state):
            return 900.0
        if mega_gengar_line_live(state) and not has_in_play(state, "Mega Gengar ex"):
            return 650.0
        if deino_count(state) > 0 and not has_in_play(state, "Hydreigon ex"):
            return 450.0
        return 120.0
    if name == "Boss's Orders":
        return 350.0
    if name == "Team Rocket's Petrel":
        if emergency_setup:
            return 2400.0 if has_in_hand(state, "Buddy-Buddy Poffin") else 8600.0
        return 120.0
    if name in {"Special Red Card"}:
        return 120.0
    return 0.0


def crispin_hydreigon_energy_score(state: Any) -> float:
    best = 0.0
    for _, _, pokemon in iter_in_play(state):
        name = canonical_name_from_id(card_id(pokemon))
        if name not in {"Hydreigon ex", "Deino", "Zweilous"}:
            continue
        ids = set(attached_card_ids(pokemon, "energyCards")) | set(attached_card_ids(pokemon, "energies"))
        energy_count = pokemon_energy_count(pokemon)
        missing_metal = 8 not in ids
        missing_psychic = 5 not in ids
        missing_darkness = 7 not in ids
        has_required = not (missing_metal or missing_psychic or missing_darkness)
        if energy_count >= 4:
            continue
        if name == "Hydreigon ex":
            score = 350.0
            if missing_metal or missing_psychic:
                score += 900.0
            if missing_darkness:
                score += 700.0 if energy_count >= 2 else 350.0
            if has_required and energy_count == 3:
                score += 1500.0
            if energy_count >= 2 and (missing_metal or missing_psychic):
                score += 900.0
            best = max(best, score)
        elif name in {"Deino", "Zweilous"}:
            score = 500.0
            if missing_metal or missing_psychic:
                score += 250.0
            if missing_darkness:
                score += 150.0
            best = max(best, score)
    return best


def legal_main_attacker_evolution_option_exists(state: Any) -> bool:
    for option in getattr(state, "options", []) or []:
        typ = option_type(option)
        name = canonical_name_from_id(card_id_from_option(state, option))
        if typ == OPT_EVOLVE and name in {"Hydreigon ex", "Mega Gengar ex"}:
            return True
        if typ == OPT_PLAY and name == "Rare Candy":
            return True
    return False


def crispin_mega_gengar_energy_score(state: Any) -> float:
    best = 0.0
    try:
        from core.opponent_model import infer_opponent_next_turn_threat

        threat = infer_opponent_next_turn_threat(state)
        ex_pressure = bool(threat.has_rulebox_attacker or threat.likely_ex_heavy)
    except Exception:
        ex_pressure = False
    for _, _, pokemon in iter_in_play(state):
        name = canonical_name_from_id(card_id(pokemon))
        if name not in {"Mega Gengar ex", "Haunter", "Gastly"}:
            continue
        energy_count = pokemon_energy_count(pokemon)
        if energy_count >= 2:
            continue
        if name == "Mega Gengar ex":
            score = 800.0 if energy_count == 0 else 1500.0
        elif name == "Haunter":
            score = 850.0 if has_in_hand(state, "Mega Gengar ex") or ex_pressure else 450.0
        else:
            score = 650.0 if has_in_hand(state, "Haunter") or has_in_hand(state, "Mega Gengar ex") or ex_pressure else 250.0
        if ex_pressure:
            score += 500.0
        best = max(best, score)
    return best
