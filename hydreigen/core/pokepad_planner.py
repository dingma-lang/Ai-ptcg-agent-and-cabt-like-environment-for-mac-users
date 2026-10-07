from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

from state_eval import OPT_CARD, OPT_PLAY, bench_pokemon, bench_space, card_id_from_option, option_type
from core.priority_tables import CARD_IDS, RULE_BOX_IDS, canonical_name_from_id, count_in_play, context_source_name, has_in_play


@dataclass(frozen=True)
class Decision:
    should_act: bool
    score: float = 0.0
    option_index: Optional[int] = None
    reason: str = ""


def should_use_pokepad_now(state: Any, legal_options: Sequence[Any] | None = None) -> Decision:
    options = list(legal_options or getattr(state, "options", []) or [])
    idx = pokepad_option_index(state, options)
    if idx is None:
        return Decision(False, reason="Poke Pad is not legal.")
    try:
        from core.setup_recovery_planner import emergency_setup_needed

        if emergency_setup_needed(state):
            return Decision(True, 8200.0, idx, "Use Poké Pad because Bench is nearly empty and hand has no Basic Pokémon.")
    except Exception:
        pass
    score = pokepad_need_score(state)
    if score <= 0:
        return Decision(False, reason="No missing non-Rule Box setup piece.")
    return Decision(True, score, idx, "Use Poké Pad to find non-Rule Box setup piece.")


def score_pokepad_play(state: Any, option: Any) -> float:
    if canonical_name_from_id(card_id_from_option(state, option)) != "Poke Pad":
        return 0.0
    decision = should_use_pokepad_now(state)
    return decision.score if decision.should_act else 0.0


def score_pokepad_target(state: Any, cid: Optional[int]) -> float:
    if cid in RULE_BOX_IDS:
        return -5000.0
    name = canonical_name_from_id(cid)
    if not name:
        return 0.0
    try:
        from core.combo_presence_planner import score_combo_search_target

        combo_score = score_combo_search_target(state, cid, "Poke Pad")
        if combo_score:
            return combo_score
    except Exception:
        pass
    try:
        from core.setup_recovery_planner import call_for_family_bridge_needed

        if call_for_family_bridge_needed(state):
            if name == "Toxel":
                return 12500.0
            if name == "Deino":
                return 700.0
    except Exception:
        pass
    try:
        from core.search_sequence_planner import score_pokepad_context_target

        context_score = score_pokepad_context_target(state, cid)
        if context_score:
            return context_score
    except Exception:
        pass
    try:
        from core.setup_recovery_planner import emergency_setup_needed

        if emergency_setup_needed(state):
            if name == "Toxel" and has_in_play(state, "Deino"):
                return 12500.0
            if name == "Deino":
                return 9000.0
            if name == "Gastly":
                return 8600.0
            if name == "Toxel":
                return 8200.0
    except Exception:
        pass
    if name == "Deino":
        if count_in_play(state, "Deino") == 0:
            return 2800.0
        if count_in_play(state, "Deino") == 1 and len(bench_pokemon(state)) < 3:
            return 2400.0
        return 600.0
    if name == "Zweilous" and has_in_play(state, "Deino"):
        return 2200.0
    if name == "Gastly" and not has_in_play(state, "Gastly"):
        return 2200.0
    if name == "Haunter" and has_in_play(state, "Gastly"):
        return 3000.0
    if name == "Toxel" and not (has_in_play(state, "Toxel") or has_in_play(state, "Toxtricity")):
        return 1800.0
    if name == "Toxtricity" and has_in_play(state, "Toxel"):
        return 1600.0
    return 100.0


def pokepad_need_score(state: Any) -> float:
    try:
        from core.combo_presence_planner import gengar_bridge_needed, hydreigon_bridge_needed

        if hydreigon_bridge_needed(state):
            return 7600.0
        if gengar_bridge_needed(state):
            return 7200.0
    except Exception:
        pass
    try:
        from core.setup_recovery_planner import call_for_family_bridge_needed

        if call_for_family_bridge_needed(state):
            return 9000.0
    except Exception:
        pass
    if not has_in_play(state, "Deino") and count_in_play(state, "Deino") == 0:
        try:
            from core.priority_tables import has_in_hand

            if has_in_hand(state, "Zweilous") and has_in_hand(state, "Hydreigon ex"):
                return 9000.0
        except Exception:
            pass
    try:
        from core.priority_tables import has_in_hand

        if not has_in_play(state, "Gastly") and has_in_hand(state, "Haunter") and has_in_hand(state, "Mega Gengar ex"):
            return 9000.0
        if has_in_play(state, "Gastly") and not has_in_play(state, "Haunter") and has_in_hand(state, "Mega Gengar ex"):
            return 5200.0
        if has_in_play(state, "Deino") and not has_in_play(state, "Zweilous") and has_in_hand(state, "Hydreigon ex"):
            return 5000.0
    except Exception:
        pass
    if count_in_play(state, "Deino") == 0:
        return 2800.0
    if count_in_play(state, "Deino") == 1 and len(bench_pokemon(state)) < 3:
        return 2400.0
    if has_in_play(state, "Deino"):
        return 2200.0
    if not has_in_play(state, "Gastly"):
        return 2200.0
    if has_in_play(state, "Gastly") and not has_in_play(state, "Haunter"):
        return 2000.0
    if not (has_in_play(state, "Toxel") or has_in_play(state, "Toxtricity")) and bench_space(state) > 0:
        return 1800.0
    if has_in_play(state, "Toxel") and not has_in_play(state, "Toxtricity"):
        return 1600.0
    return 0.0


def pokepad_option_index(state: Any, options: Sequence[Any]) -> Optional[int]:
    for idx, option in enumerate(options):
        if option_type(option) == OPT_PLAY and canonical_name_from_id(card_id_from_option(state, option)) == "Poke Pad":
            return idx
    return None


def is_pokepad_search_context(state: Any) -> bool:
    return context_source_name(state) == "Poke Pad"


def pokepad_search_has_setup_target(state: Any) -> bool:
    if not is_pokepad_search_context(state):
        return False
    for option in getattr(state, "options", []) or []:
        if option_type(option) != OPT_CARD:
            continue
        if score_pokepad_target(state, card_id_from_option(state, option)) > 0:
            return True
    return False
