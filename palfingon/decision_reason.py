from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable, List, Optional, Sequence

from action_classifier import ActionCategory, ClassifiedAction, classify_legal_option
from card_db import get_db
from deck_profile import list_value
from state_eval import active_pokemon, card_id, getv, int_or, normalize_state, pokemon_hp


def explain_option(state: Any, classified: ClassifiedAction, score: Optional[float] = None, chosen: bool = False) -> str:
    category = classified.category
    card_name = classified.card_name
    target_name = classified.target_name

    if classified.card_id == 1174 and 0 <= classified.index < len(state.options):
        from core.air_balloon_planner import score_air_balloon_target

        balloon = score_air_balloon_target(state, state.options[classified.index])
        if balloon.reason:
            return balloon.reason

    if category == ActionCategory.ATTACK:
        attacker = active_pokemon(state)
        attacker_name = get_db().card_name(card_id(attacker))
        if card_id(attacker) == 51:
            if score is not None and score < -100000:
                return "Avoid Vanguard Punch: recoil would Knock Out our Palafin."
            return "Use one-prize Palafin's Vanguard Punch; check existing damage for recoil."
        attack = next((a for a in (get_db().get_card(card_id(attacker)).attacks if get_db().get_card(card_id(attacker)) else [])
                       if a.name == classified.attack_name), None)
        opponent = active_pokemon(state, state.opponent_index)
        if attack is not None and opponent is not None:
            from policy import estimate_attack_damage

            if 0 < pokemon_hp(opponent) <= estimate_attack_damage(state, attack, attacker, opponent):
                return f"Take estimated KO with {attacker_name}"
        if classified.attack_name:
            return f"Attack with {attacker_name} using {classified.attack_name}"
        return f"Attack with {attacker_name}"
    if category == ActionCategory.PLAY_BASIC_TO_BENCH:
        try:
            from core.danger_evaluator import evaluate_danger
            from core.danger_evaluator import our_pokemon_knocked_out_last_turn
        except Exception:
            evaluate_danger = None
            our_pokemon_knocked_out_last_turn = None
        danger = evaluate_danger(state) if evaluate_danger else None
        if is_two_prize_setup_liability(classified):
            return f"Do not bench {card_name} because it is a two-prize liability"
        if classified.card_id in list_value("setup_pokemon"):
            return f"Bench {card_name} early for setup"
        return f"Bench {card_name}"
    if category == ActionCategory.ATTACH_ENERGY:
        if "Water" in card_name and target_name == "Palafin ex":
            return "Attach Water to Palafin ex only if it has no Energy yet."
        if "Lightning" in card_name and target_name in {"Dratini", "Dragonair", "Mega Dragonite ex"}:
            return "Attach Lightning to the Dragonite line."
        if target_name:
            return f"Attach {card_name} to {target_name}"
        return f"Attach {card_name}"
    if category == ActionCategory.EVOLVE:
        if card_name:
            return f"Evolve into {card_name}"
        return "Evolve key Pokemon"
    if category == ActionCategory.RARE_CANDY_EVOLVE:
        return "Use evolution shortcut when it is legal and valuable"
    if category == ActionCategory.DRAW_OR_SEARCH:
        try:
            from core.priority_tables import context_source_name

            source = context_source_name(state)
        except Exception:
            source = ""
        if source == "Poke Pad" and card_name == "Dratini":
            return "Poké Pad target: Dratini because the Dragonite basic is missing."
        if source == "Poke Pad" and card_name == "Palafin":
            return "Poké Pad target: Palafin because Finizen is ready to evolve."
        if card_name == "Buddy-Buddy Poffin":
            return "Use Buddy-Buddy Poffin because Bench is not full."
        if card_name == "Poke Pad" or card_name == "Poké Pad":
            return "Use Poké Pad to find non-Rule Box setup piece."
        if card_name:
            return f"Use {card_name} to find setup pieces"
        return "Choose draw/search target"
    if category == ActionCategory.PLAY_SUPPORTER:
        if card_name == "Judge":
            return "Judge: refresh a dead hand or reduce the opponent's visible hand after useful plays."
        if card_name == "Lillie's Determination":
            return "Use Supporter because Supporter is unused and hand is weak."
        if card_name == "Crispin":
            return "Use Crispin when it fixes Palafin or Dragonite Energy."
        return f"Play Supporter {card_name}" if card_name else "Play Supporter"
    if category == ActionCategory.PLAY_ITEM:
        return f"Play Item {card_name}" if card_name else "Play Item"
    if category == ActionCategory.PLAY_STADIUM:
        if card_name == "Battle Cage":
            return "Battle Cage: weigh visible counter-placement threats against losing Surfing Beach."
        return f"Play Stadium {card_name}" if card_name else "Play Stadium"
    if category == ActionCategory.USE_ABILITY:
        return f"Use {card_name} Ability" if card_name else "Use Ability"
    if category == ActionCategory.RETREAT:
        return "Retreat to a better attacker or pivot"
    if category == ActionCategory.SWITCH_ACTIVE:
        return f"Switch into {card_name or target_name}"
    if category == ActionCategory.DISCARD_COST:
        from core.expert_battle_planner import redundant_attacker_discard

        if redundant_attacker_discard(state, classified.card_id):
            return f"Discard spare {card_name}: its attackers are already established."
        if classified.card_id in list_value("protected_cards"):
            return f"Avoid discarding protected card {card_name}"
        return f"Discard {card_name} as lowest-value cost"
    if category == ActionCategory.RECOVER_FROM_DISCARD:
        return f"Recover {card_name} from discard" if card_name else "Recover key resource"
    if category == ActionCategory.SHUFFLE_INTO_DECK:
        return f"Shuffle {card_name} into deck" if card_name else "Shuffle resource into deck"
    if category == ActionCategory.PRIZE_SELECTION:
        return "Take prize card after KO"
    if category == ActionCategory.PROMOTE_AFTER_KO:
        return f"Promote {card_name or target_name} after KO"
    if category == ActionCategory.CHOOSE_ATTACK_TARGET:
        return f"Choose {card_name or target_name} as attack target"
    if category == ActionCategory.CHOOSE_EFFECT_TARGET:
        return f"Choose {card_name or target_name} as effect target"
    if category == ActionCategory.SETUP_CHOOSE_ACTIVE:
        return f"Choose {card_name} as setup Active"
    if category == ActionCategory.SETUP_CHOOSE_BENCH:
        if is_two_prize_setup_liability(classified):
            return f"Do not bench {card_name} because it is a two-prize liability"
        if classified.card_id in list_value("setup_pokemon"):
            return f"Bench {card_name} early for setup"
        return f"Choose {card_name} for setup Bench"
    if category == ActionCategory.GO_FIRST_SECOND_DECISION:
        return "Prefer going first for board setup"
    if category == ActionCategory.MULLIGAN_DECISION:
        return "Resolve mulligan decision"
    if category == ActionCategory.SPECIAL_CONDITION_CHECK:
        return "Resolve special condition or coin check"
    if category == ActionCategory.COUNT_SELECTION:
        return f"Choose count {classified.number}"
    if category == ActionCategory.YES_NO_DECISION:
        return "Choose beneficial optional effect" if chosen else "Evaluate optional effect"
    if category == ActionCategory.END_TURN:
        return "Pass because no useful legal action remains"
    return "Fallback to safest legal option"


def is_two_prize_setup_liability(classified: ClassifiedAction) -> bool:
    if classified.card_id in list_value("avoid_benching"):
        return True
    if not str(classified.card_name or "").endswith(" ex"):
        return False
    planned_attackers = set(list_value("primary_attackers")) | set(list_value("secondary_attackers"))
    setup_ids = set(list_value("setup_pokemon"))
    return classified.card_id not in planned_attackers and classified.card_id not in setup_ids


def explain_choice(obs_or_state: Any, choice: Sequence[int], scores: Sequence[float]) -> str:
    state = obs_or_state if hasattr(obs_or_state, "select") else normalize_state(obs_or_state)
    if choice and getattr(state, "expert_battle_reason", ""):
        return state.expert_battle_reason
    if not choice:
        return "Decline optional selection"
    idx = int(choice[0])
    options = getattr(state, "options", []) or []
    if not (0 <= idx < len(options)):
        return "Fallback to legal selection"
    classified = classify_legal_option(state, options[idx], idx)
    score = scores[idx] if 0 <= idx < len(scores) else None
    return explain_option(state, classified, score=score, chosen=True)


def build_decision_record(obs_or_state: Any, scores: Sequence[float], choice: Sequence[int]) -> dict:
    state = obs_or_state if hasattr(obs_or_state, "select") else normalize_state(obs_or_state)
    options = getattr(state, "options", []) or []
    option_rows = []
    choice_set = {int(idx) for idx in choice if isinstance(idx, int) or str(idx).isdigit()}
    for idx, option in enumerate(options):
        classified = classify_legal_option(state, option, idx)
        score = scores[idx] if 0 <= idx < len(scores) else None
        option_rows.append(classified.as_log_dict(score=score, reason=explain_option(state, classified, score, idx in choice_set)))
    record = {
        "turn": int_or(getv(state.current, "turn", 0), 0),
        "moment_type": str(getattr(state, "moment_type", "")),
        "phase_context": int_or(getv(state.select, "context", -1), -1),
        "select_type": int_or(getv(state.select, "type", -1), -1),
        "min_count": int_or(getv(state.select, "minCount", 0), 0),
        "max_count": int_or(getv(state.select, "maxCount", 0), 0),
        "legal_options": option_rows,
        "chosen_index": list(choice),
        "reason": explain_choice(state, choice, scores),
        "expert_lesson_status": "none",
        "expert_debug_lines": ["Expert lesson matched: none."],
    }
    if getattr(state, "expert_battle_reason", ""):
        record["expert_lesson_status"] = "matched"
        record["expert_lesson_matched"] = "palfingon_1.1_visible_finisher"
        record["expert_debug_lines"] = [state.expert_battle_reason]
    try:
        matches = list(getattr(state, "expert_matches", []))
        if matches:
            record["expert_matches"] = matches
            record["expert_lesson_status"] = "matched"
            chosen_set = {int(idx) for idx in choice if isinstance(idx, int) or str(idx).isdigit()}
            chosen_matches = [match for match in matches if int_or(getv(match, "option_index", -1), -1) in chosen_set]
            if chosen_matches:
                best = max(chosen_matches, key=lambda item: float(getv(item, "bonus", 0.0) or 0.0))
                record["expert_lesson_matched"] = getv(best, "lesson_id", "")
                record["expert_sequence"] = getv(best, "sequence", "")
                record["expert_override_reason"] = getv(best, "reason", "")
                sequence = getv(best, "sequence", "") or getv(best, "lesson_id", "")
                reason = getv(best, "reason", "")
                record["expert_debug_lines"] = [
                    f"Expert lesson matched: {sequence}.",
                    f"Reason: {reason}",
                    f"Override: {sequence} influenced the chosen legal option.",
                ]
    except Exception:
        pass
    return record


def log_decision_if_enabled(obs_or_state: Any, scores: Sequence[float], choice: Sequence[int]) -> None:
    target = os.environ.get("PTCG_AGENT_DECISION_LOG")
    if not target:
        return
    try:
        record = build_decision_record(obs_or_state, scores, choice)
        if target.lower() in ("1", "true", "stdout", "-"):
            print(json.dumps(record, ensure_ascii=True, sort_keys=True))
            return
        path = Path(target)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n")
    except Exception:
        return
