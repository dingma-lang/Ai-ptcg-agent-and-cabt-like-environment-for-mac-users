from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from action_classifier import ActionCategory, classify_legal_option
from state_eval import OPT_ATTACH, OPT_PLAY, card_id_from_option, deck_count, getv, hand_count, option_type
from core.danger_evaluator import CRITICAL, HIGH, evaluate_danger, our_pokemon_knocked_out_last_turn
from core.energy_planner import score_energy_option
from core.mega_gengar_planner import mega_gengar_line_live
from core.priority_tables import canonical_name_from_id, count_in_play, has_in_hand, has_in_play
from core.supporter_planner import hand_playability_score, legal_main_attacker_evolution_option_exists


@dataclass(frozen=True)
class ResourceDecision:
    should_spend: bool
    score: float = 0.0
    reason: str = ""
    option_index: Optional[int] = None


def should_spend_supporter_this_turn(state: Any) -> ResourceDecision:
    if bool(getv(state.current, "supporterPlayed", False)):
        return ResourceDecision(False, reason="Supporter already used.")

    try:
        from core.deck_operating_system import compute_deck_goal_state
        from core.supporter_router import choose_best_supporter

        routed = choose_best_supporter(state, getattr(state, "options", []) or [], compute_deck_goal_state(state))
        if routed.should_use and routed.option_index is not None and routed.score >= 500.0:
            return ResourceDecision(True, routed.score, routed.reason, routed.option_index)
    except Exception:
        pass

    best_idx: Optional[int] = None
    best_name = ""
    best_score = -99999.0
    for idx, option in enumerate(state.options):
        action = classify_legal_option(state, option, idx)
        if action.category == ActionCategory.PLAY_SUPPORTER:
            name = action.card_name or canonical_name_from_id(card_id_from_option(state, option))
            try:
                from core.supporter_planner import score_supporter_option

                score = score_supporter_option(state, option)
            except Exception:
                score = 0.0
            if score > best_score:
                best_score = score
                best_idx = idx
                best_name = name
    if best_idx is None:
        return ResourceDecision(False, reason="No legal Supporter option.")

    if best_name == "Lillie's Determination" and legal_main_attacker_evolution_option_exists(state):
        return ResourceDecision(False, -900.0, "Hold Supporter because a main attacker evolution is already legal.", best_idx)
    if best_name == "Lillie's Determination" and deck_count(state) <= 3:
        return ResourceDecision(False, -1200.0, "Hold Supporter to avoid deck-out risk.", best_idx)

    danger = evaluate_danger(state)
    playability = hand_playability_score(state)
    weak_hand = hand_count(state) <= 4 or playability < 180.0
    no_setup = count_in_play(state, "Deino") == 0 and not any(has_in_hand(state, card) for card in ("Buddy-Buddy Poffin", "Ultra Ball", "Poke Pad"))
    missing_stage2 = has_in_play(state, "Deino") and not (has_in_hand(state, "Rare Candy") and has_in_hand(state, "Hydreigon ex"))

    if best_name == "Boss's Orders":
        return ResourceDecision(True, 350.0, "Use Boss's Orders when it improves prize route or creates a KO.", best_idx)
    if best_name == "Crispin" and mega_gengar_line_live(state):
        return ResourceDecision(True, 760.0, "Use Crispin because Mega Gengar ex is a live attacker line.", best_idx)
    if best_name == "Crispin" and (has_in_play(state, "Hydreigon ex") or has_in_play(state, "Deino") or has_in_play(state, "Zweilous")):
        return ResourceDecision(True, 700.0, "Use Crispin because Hydreigon needs Metal/Psychic.", best_idx)
    if best_name == "Lillie's Determination" and weak_hand:
        return ResourceDecision(True, 900.0, "Use Supporter because Supporter is unused and hand is weak.", best_idx)
    if best_name == "Lillie's Determination" and (no_setup or missing_stage2):
        return ResourceDecision(True, 750.0, "Use Lillie's Determination because no useful actions remain and hand is low value.", best_idx)
    if our_pokemon_knocked_out_last_turn(state) and weak_hand:
        return ResourceDecision(True, 600.0, "Use Supporter after KO to rebuild hand.", best_idx)
    if danger.severity in (HIGH, CRITICAL) and weak_hand:
        return ResourceDecision(True, 550.0, "Use Supporter because danger is high and setup is unstable.", best_idx)
    if best_name in {"Team Rocket's Petrel", "Special Red Card"} and danger.threat and danger.threat.hand_size >= 6:
        return ResourceDecision(True, 450.0, "Use disruption because opponent hand/threat is strong.", best_idx)
    if best_score >= 450.0:
        return ResourceDecision(True, best_score, f"Use {best_name} before attacking or ending turn.", best_idx)
    if best_name in {"Dawn", "Team Rocket's Petrel", "Special Red Card"} and best_score >= 120.0:
        return ResourceDecision(True, max(250.0, best_score), f"Use {best_name} before low-value attack or ending turn.", best_idx)
    return ResourceDecision(False, 0.0, "No useful Supporter spend required.", best_idx)


def should_attach_energy_this_turn(state: Any) -> ResourceDecision:
    if bool(getv(state.current, "energyAttached", False)):
        return ResourceDecision(False, reason="Manual Energy already attached.")

    best_score = -99999.0
    best_idx: Optional[int] = None
    best_name = ""
    for idx, option in enumerate(state.options):
        if option_type(option) != OPT_ATTACH:
            continue
        action = classify_legal_option(state, option, idx)
        if action.category != ActionCategory.ATTACH_ENERGY:
            continue
        score = score_energy_option(state, option)
        if score > best_score:
            best_score = score
            best_idx = idx
            best_name = action.card_name or canonical_name_from_id(card_id_from_option(state, option))

    if best_idx is None:
        return ResourceDecision(False, reason="No legal Energy attachment.")
    if best_score >= 500.0:
        if "Darkness" in best_name:
            return ResourceDecision(True, 800.0, "Attach Darkness to Mega Gengar or Hydreigon attacker line; manual Energy should not be wasted.", best_idx)
        return ResourceDecision(True, 750.0, f"Attach {best_name}; manual Energy should not be wasted.", best_idx)
    if best_name in {"Basic Metal Energy", "Basic Psychic Energy"}:
        return ResourceDecision(False, -700.0, "Hold Metal/Psychic Energy unless it attaches to the Deino evolution chain.", best_idx)
    return ResourceDecision(False, 0.0, "No useful Energy attachment target.", best_idx)
