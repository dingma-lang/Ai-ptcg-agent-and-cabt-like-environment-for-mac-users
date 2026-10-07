from __future__ import annotations

from typing import Any, Optional, Sequence

from action_classifier import ActionCategory, classify_legal_option
from core.action_intent import ActionIntent, ActionIntentType
from state_eval import OPT_ATTACH, OPT_PLAY, active_pokemon, attach_target_from_option, bench_pokemon, card_id, card_id_from_option, getv, hand_count, option_type
from core.disposable_active_planner import identify_disposable_active, obvious_setup_action_exists
from core.priority_tables import CARD_IDS, canonical_name_from_id, count_in_play, has_in_hand, has_in_play


def opening_low_setup_plan(state: Any, legal_options: Sequence[Any]) -> Optional[ActionIntent]:
    best_idx: Optional[int] = None
    best_score = 0.0
    for idx, option in enumerate(legal_options):
        score = score_opening_low_setup_option(state, option)
        if score > best_score:
            best_idx = idx
            best_score = score
    if best_idx is None or best_score <= 0.0:
        return None
    action = classify_legal_option(state, legal_options[best_idx], best_idx)
    return ActionIntent(
        intent_type=ActionIntentType.SEARCH_CARD,
        selected_option_indices=[best_idx],
        source_card_id=action.card_id,
        source_card_name=action.card_name,
        priority_score=best_score,
        reason=opening_reason(action.card_name),
        submission_safe=True,
    )


def score_opening_low_setup_option(state: Any, option: Any) -> float:
    turn = int(getv(state.current, "turn", 0) or 0)
    if turn > 3:
        return 0.0
    name = canonical_name_from_id(card_id_from_option(state, option))
    typ = option_type(option)
    report = identify_disposable_active(state)
    board_basic_count = len([pokemon for pokemon in [active_pokemon(state)] + bench_pokemon(state) if pokemon is not None])
    low_setup = board_basic_count <= 1 or (count_in_play(state, "Deino") <= 1 and len(bench_pokemon(state)) <= 1)
    if not low_setup:
        return 0.0

    if typ == OPT_PLAY and name in {"Poke Pad", "Poké Pad"} and count_in_play(state, "Deino") <= 1:
        return 4200.0
    if typ == OPT_PLAY and name == "Buddy-Buddy Poffin":
        return 5500.0
    if typ == OPT_PLAY and name == "Ultra Ball" and report.opponent_can_ko and not has_in_play(state, "Fezandipiti ex"):
        return 3600.0
    if typ == OPT_PLAY and name == "Lillie's Determination":
        return -2000.0 if obvious_setup_action_exists(state) else (3000.0 if hand_count(state) <= 4 else 900.0)
    if typ == OPT_ATTACH and report.is_disposable:
        target = attach_target_from_option(state, option)
        target_name = canonical_name_from_id(card_id(target))
        if target_name == "Deino" and target is not active_pokemon(state):
            return 3000.0
        if target_name == "Deino":
            return -2500.0
    return 0.0


def score_pokepad_context_target(state: Any, cid: Optional[int]) -> float:
    name = canonical_name_from_id(cid)
    if not name:
        return 0.0
    try:
        from core.setup_recovery_planner import call_for_family_bridge_needed

        if call_for_family_bridge_needed(state):
            if name == "Toxel":
                return 12800.0
            if name == "Deino":
                return 700.0
    except Exception:
        pass
    has_gengar_chain = has_in_hand(state, "Haunter") or has_in_hand(state, "Mega Gengar ex") or has_in_play(state, "Haunter")
    has_full_gengar_chain = has_in_hand(state, "Haunter") and has_in_hand(state, "Mega Gengar ex")
    has_full_hydreigon_chain = has_in_hand(state, "Zweilous") and has_in_hand(state, "Hydreigon ex")
    if name == "Deino" and has_full_hydreigon_chain and not has_in_play(state, "Deino"):
        return 13200.0
    if name == "Deino" and count_in_play(state, "Deino") <= 1:
        return 9800.0
    if name == "Gastly" and has_full_gengar_chain and not has_in_play(state, "Gastly"):
        return 13400.0
    if name == "Gastly" and has_gengar_chain and not has_in_play(state, "Gastly"):
        return 11800.0
    if name == "Haunter" and has_in_play(state, "Gastly") and has_in_hand(state, "Mega Gengar ex") and not has_in_play(state, "Haunter"):
        return 9800.0
    if name == "Zweilous" and has_in_play(state, "Deino") and has_in_hand(state, "Hydreigon ex") and not has_in_hand(state, "Rare Candy"):
        return 9600.0
    if name == "Zweilous" and has_in_play(state, "Deino") and not has_in_hand(state, "Rare Candy"):
        return 7600.0
    if name == "Toxel" and has_gengar_chain and not has_in_play(state, "Gastly"):
        return -1800.0
    return 0.0


def opening_reason(card_name: str) -> str:
    if card_name in {"Poke Pad", "Poké Pad"}:
        return "Opening low setup: use Poké Pad to find another setup Basic before Lillie."
    if card_name == "Buddy-Buddy Poffin":
        return "Opening low setup: fill Bench with setup Basics before Lillie."
    if card_name == "Ultra Ball":
        return "Prepare Fezandipiti ex because Active is likely to be Knocked Out."
    return "Opening low setup plan."
