from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable, List, Optional, Sequence

from action_classifier import ActionCategory, ClassifiedAction, classify_legal_option
from card_db import get_db
from deck_profile import list_value
from state_eval import active_pokemon, card_id, getv, int_or, normalize_state


def explain_option(state: Any, classified: ClassifiedAction, score: Optional[float] = None, chosen: bool = False) -> str:
    category = classified.category
    card_name = classified.card_name
    target_name = classified.target_name

    if category == ActionCategory.ATTACK:
        attacker = active_pokemon(state)
        attacker_name = get_db().card_name(card_id(attacker))
        if attacker_name in {"N’s Zoroark ex", "N's Zoroark ex"}:
            if score is not None and score >= 10000:
                return "Use Night Joker with best Benched N's attack for KO math."
            return "Attack with N's Zoroark ex using Night Joker copy plan."
        if score is not None and score >= 10000:
            return f"Take KO with {attacker_name}"
        if classified.attack_name:
            return f"Attack with {attacker_name} using {classified.attack_name}"
        return f"Attack with {attacker_name}"
    if category == ActionCategory.PLAY_BASIC_TO_BENCH:
        if card_name in {"N’s Zorua", "N's Zorua"}:
            return "Bench N's Zorua early for Zoroark ex setup."
        if card_name in {"N’s Zekrom", "N's Zekrom"}:
            return "Bench N's Zekrom as Night Joker copy source."
        try:
            from core.danger_evaluator import evaluate_danger
            from core.danger_evaluator import our_pokemon_knocked_out_last_turn
        except Exception:
            evaluate_danger = None
            our_pokemon_knocked_out_last_turn = None
        danger = evaluate_danger(state) if evaluate_danger else None
        if chosen and card_name == "Fezandipiti ex" and our_pokemon_knocked_out_last_turn and our_pokemon_knocked_out_last_turn(state):
            return "Bench Fezandipiti ex after our Pokemon was Knocked Out so Flip the Script is available."
        if chosen and card_name == "Fezandipiti ex" and danger and danger.bench_count == 0:
            return "Bench Fezandipiti ex because Bench is empty and early-game no-Bench loss risk is high."
        if card_name == "Pecharunt ex":
            return "Bench Pecharunt ex because a pivot line may matter."
        if is_two_prize_setup_liability(classified):
            return f"Do not bench {card_name} because it is a two-prize liability"
        if classified.card_id in list_value("setup_pokemon"):
            return f"Bench {card_name} early for setup"
        return f"Bench {card_name}"
    if category == ActionCategory.ATTACH_ENERGY:
        if "Darkness" in card_name and target_name in {"N’s Zoroark ex", "N's Zoroark ex"}:
            return "Attach Darkness to Zoroark; second Energy enables Night Joker."
        if "Darkness" in card_name and target_name in {"N’s Zekrom", "N's Zekrom"}:
            return "Do not attach Energy to N's Zekrom; Zoroark copies it from Bench."
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
        if card_name == "Buddy-Buddy Poffin":
            return "Use Buddy-Buddy Poffin because Bench can still add N's Zorua."
        if card_name == "Poke Pad" or card_name == "Poké Pad":
            return "Use Poké Pad to find non-Rule Box N's setup or copy-source piece."
        if card_name:
            return f"Use {card_name} to find setup pieces"
        return "Choose draw/search target"
    if category == ActionCategory.PLAY_SUPPORTER:
        if card_name == "Cyrano":
            return "Use Cyrano for N's Zoroark ex or exact support ex."
        if card_name == "Black Belt's Training":
            return "Use Black Belt only when +40 changes Pokémon ex KO math."
        if card_name == "Boss's Orders":
            return "Use Boss only for a clear Night Joker prize route."
        if card_name == "Lillie's Determination":
            return "Use Supporter because Supporter is unused and hand is weak."
        return f"Play Supporter {card_name}" if card_name else "Play Supporter"
    if category == ActionCategory.PLAY_ITEM:
        return f"Play Item {card_name}" if card_name else "Play Item"
    if category == ActionCategory.PLAY_STADIUM:
        return f"Play Stadium {card_name}" if card_name else "Play Stadium"
    if category == ActionCategory.USE_ABILITY:
        if card_name in {"N’s Zoroark ex", "N's Zoroark ex"}:
            return "Use Trade only with a safe discard to improve hand or enable N's PP Up."
        if card_name == "Pecharunt ex":
            return "Use Pecharunt ex only when switch/poison improves Zoroark KO math."
        if card_name == "Fezandipiti ex":
            return "Use Fezandipiti ex Flip the Script after our Pokemon was Knocked Out."
        return f"Use {card_name} Ability" if card_name else "Use Ability"
    if category == ActionCategory.RETREAT:
        return "Retreat to a better attacker or pivot"
    if category == ActionCategory.SWITCH_ACTIVE:
        return f"Switch into {card_name or target_name}"
    if category == ActionCategory.DISCARD_COST:
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
        if chosen and card_name == "Fezandipiti ex":
            return "Bench Fezandipiti ex because Bench is empty and early-game no-Bench loss risk is high."
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
    record["round_plan"] = {
        "game_stage": getattr(state, "moment_type", ""),
        "board_goal": "Establish N's Zorua/Zoroark ex, Bench N's copy sources, and keep two Darkness on the attacking Zoroark.",
        "primary_attacker_goal": "Attack with N's Zoroark ex using Night Joker.",
        "secondary_attacker_goal": "No secondary attacker; use Benched N's Zekrom, Reshiram, or Darmanitan only as Night Joker copy sources.",
        "supporter_goal": "Use Lillie for weak hands, Cyrano for ex access, and Boss/Black Belt only for prize math.",
        "energy_goal": "Preserve Darkness Energy for Zorua/Zoroark lines and N's PP Up acceleration.",
        "reason": "Deck-local N's Zoroark decision summary.",
    }
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
