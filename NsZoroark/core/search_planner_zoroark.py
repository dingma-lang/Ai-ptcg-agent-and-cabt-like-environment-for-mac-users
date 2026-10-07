from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

from card_db import get_db
from state_eval import (
    CTX_ATTACH_FROM,
    CTX_ATTACH_TO,
    CTX_DISCARD,
    CTX_DISCARD_CARD_OR_ATTACHED_CARD,
    CTX_DISCARD_ENERGY,
    CTX_DISCARD_ENERGY_CARD,
    CTX_DISCARD_TOOL_CARD,
    CTX_EFFECT_TARGET,
    CTX_LOOK,
    CTX_TO_BENCH,
    CTX_TO_FIELD,
    CTX_TO_HAND,
    OPT_CARD,
    OPT_PLAY,
    bench_space,
    card_id,
    card_id_from_option,
    deck_count,
    getv,
    hand_cards,
    hand_count,
    option_type,
)
from core.copy_target_planner import zoroark_has_copy_source
from core.priority_tables import canonical_name, canonical_name_from_id, context_source_name, count_in_play, hand_ids, has_in_hand, has_in_play
from core.target_board import (
    BUDEW,
    DARKNESS_ENERGY_ID,
    DARMANITAN,
    DARUMAKA,
    FEZANDIPITI_EX,
    MUNKIDORI,
    PECHARUNT_EX,
    RESHIRAM,
    YVELTAL,
    ZEKROM,
    ZOROARK_EX,
    ZORUA,
    evaluate_target_board,
)


@dataclass(frozen=True)
class SearchDecision:
    should_act: bool
    score: float = 0.0
    option_index: Optional[int] = None
    reason: str = ""


DISCARD_CONTEXTS = {
    CTX_DISCARD,
    CTX_DISCARD_CARD_OR_ATTACHED_CARD,
    CTX_DISCARD_ENERGY_CARD,
    CTX_DISCARD_TOOL_CARD,
    CTX_DISCARD_ENERGY,
}

SEARCH_CONTEXTS = {
    CTX_TO_HAND,
    CTX_LOOK,
    CTX_TO_BENCH,
    CTX_TO_FIELD,
    CTX_EFFECT_TARGET,
    CTX_ATTACH_FROM,
    CTX_ATTACH_TO,
}


def should_use_poffin_zoroark(state: Any, legal_options: Sequence[Any] | None = None) -> SearchDecision:
    options = list(legal_options or getattr(state, "options", []) or [])
    idx = option_index_by_name(state, options, "Buddy-Buddy Poffin")
    if idx is None:
        return SearchDecision(False, reason="Buddy-Buddy Poffin is not legal.")
    if bench_space(state) <= 0:
        return SearchDecision(False, -1200.0, idx, "Bench is full.")
    report = evaluate_target_board(state)
    if report.zorua_count == 0:
        return SearchDecision(True, 8000.0, idx, "Use Buddy-Buddy Poffin for first N's Zorua.")
    if report.zorua_count == 1 and report.open_bench_slots > 0:
        return SearchDecision(True, 7000.0, idx, "Use Buddy-Buddy Poffin for second N's Zorua.")
    if len(getattr(state, "options", []) or []) and report.open_bench_slots > 1 and report.zorua_count < 3:
        return SearchDecision(True, 3600.0, idx, "Use Buddy-Buddy Poffin while Zorua backup count is low.")
    return SearchDecision(False, 0.0, idx, "Poffin is lower value after Zorua basics are established in this list.")


def score_poffin_target_zoroark(state: Any, cid: Optional[int]) -> float:
    if not is_poffin_eligible_target(cid):
        return -10000.0
    name = canonical_name_from_id(cid)
    report = evaluate_target_board(state)
    if name == ZORUA:
        if report.zorua_count == 0:
            return 6500.0
        if report.zorua_count == 1:
            return 5600.0
        return 1200.0
    return 250.0


def score_search_option_zoroark(state: Any, option: Any) -> float:
    if option_type(option) != OPT_PLAY:
        return 0.0
    name = option_name(state, option)
    if name == "Buddy-Buddy Poffin":
        decision = should_use_poffin_zoroark(state, getattr(state, "options", []) or [])
        return decision.score if decision.should_act else decision.score
    if name == "Poke Pad":
        return score_pokepad_play(state)
    if name == "Cyrano":
        return score_cyrano_play(state)
    if name == "N's PP Up":
        try:
            from core.energy_planner_zoroark import score_ns_pp_up_option

            return score_ns_pp_up_option(state, option)
        except Exception:
            return 0.0
    if name == "Unfair Stamp":
        return 4700.0 if support_ex_needed_after_ko(state) else -2500.0
    if name == "Tool Scrapper":
        return 2400.0 if opponent_tool_or_special_seen(state) else -1200.0
    if name == "Air Balloon":
        return score_air_balloon_play_zoroark(state, option)
    if name == "Team Rocket's Watchtower":
        return score_watchtower_play(state)
    return 0.0


def score_search_selection_zoroark(state: Any, option: Any, name: Optional[str] = None, cid: Optional[int] = None) -> float:
    cid = card_id_from_option(state, option) if cid is None else cid
    name = canonical_name(name or canonical_name_from_id(cid))
    source = context_source_name(state)

    if source == "Buddy-Buddy Poffin":
        return score_poffin_target_zoroark(state, cid)
    if source == "Poke Pad":
        return score_pokepad_target(state, cid, name)
    if source == "Cyrano":
        return score_cyrano_target(state, cid, name)
    if source == "N's PP Up":
        try:
            from core.energy_planner_zoroark import score_attach_target_zoroark
            from state_eval import pokemon_from_card_option

            return score_attach_target_zoroark(state, pokemon_from_card_option(state, option))
        except Exception:
            return 0.0
    return score_general_search_target(state, cid, name)


def score_discard_selection_zoroark(state: Any, cid: Optional[int]) -> float:
    from core.trade_planner import score_trade_discard_selection

    name = canonical_name_from_id(cid)
    source = context_source_name(state)
    score = score_trade_discard_selection(state, cid)
    count = hand_ids(state).count(int(cid)) if cid is not None else 0
    if name == "Buddy-Buddy Poffin" and bench_space(state) > 0 and count_in_play(state, ZORUA) < 2:
        score -= 5500.0
    if name == "N's Zoroark ex" and has_in_play(state, ZORUA):
        score -= 6500.0
    if name in {"N's Zekrom", "N's Reshiram"} and not zoroark_has_copy_source(state):
        score -= 6500.0
    if name == "Binding Mochi":
        try:
            from core.poison_mochi_planner import mochi_math_available

            if mochi_math_available(state):
                score -= 5200.0
        except Exception:
            pass
    if cid == DARKNESS_ENERGY_ID and not has_in_hand(state, "N's PP Up"):
        score -= 1800.0
    if count >= 2 and name not in {ZORUA, ZOROARK_EX, ZEKROM, RESHIRAM}:
        score += 900.0
    return score


def score_setup_basic_play_zoroark(state: Any, option: Any) -> float:
    if option_type(option) != OPT_PLAY or bench_space(state) <= 0:
        return 0.0
    cid = card_id_from_option(state, option)
    card = get_db().get_card(cid)
    if not card or card.card_type != "Pokemon" or not card.basic:
        return 0.0
    name = canonical_name_from_id(cid)
    report = evaluate_target_board(state)
    if name == ZORUA:
        if report.zorua_count == 0:
            return 6200.0
        if report.zorua_count == 1:
            return 5200.0
        return 900.0
    if name == ZEKROM:
        return 5600.0 if not report.has_n_zekrom else 900.0
    if name == RESHIRAM:
        return 5000.0 if not report.has_n_reshiram else 900.0
    if name == DARUMAKA:
        return 2600.0 if not (report.has_darumaka or report.has_darmanitan) else 400.0
    if name in {FEZANDIPITI_EX, PECHARUNT_EX}:
        return score_support_ex_bench(state, name)
    if name in {YVELTAL, MUNKIDORI}:
        return 900.0
    return 300.0


def best_basic_bench_from_hand_zoroark(state: Any, legal_options: Sequence[Any]) -> Optional[int]:
    best_idx = None
    best_score = 0.0
    for idx, option in enumerate(legal_options):
        score = score_setup_basic_play_zoroark(state, option)
        if score > best_score:
            best_idx = idx
            best_score = score
    return best_idx if best_score >= 1800.0 else None


def score_pokepad_play(state: Any) -> float:
    report = evaluate_target_board(state)
    if report.zorua_count < 2:
        return 5600.0
    if not report.has_n_zekrom:
        return 5200.0
    if not report.has_n_reshiram:
        return 4500.0
    if not (report.has_darumaka or report.has_darmanitan) and basic_energy_in_opponent_discard_safe(state):
        return 3800.0
    return 900.0


def score_cyrano_play(state: Any) -> float:
    if bool(getv(state.current, "supporterPlayed", False)):
        return -5000.0
    report = evaluate_target_board(state)
    if report.zorua_count > 0 and report.zoroark_ex_count < 2:
        return 7600.0
    if not report.has_pecharunt_ex and mochi_or_switch_needed(state):
        return 4200.0
    if support_ex_needed_after_ko(state):
        return 3600.0
    return 700.0


def score_pokepad_target(state: Any, cid: Optional[int], name: str) -> float:
    card = get_db().get_card(cid)
    if card and card.ex:
        return -8000.0
    report = evaluate_target_board(state)
    if name == ZORUA:
        return 6800.0 if report.zorua_count == 0 else 5400.0 if report.zorua_count == 1 else 500.0
    if name == ZEKROM:
        return 6200.0 if not report.has_n_zekrom else 1000.0
    if name == RESHIRAM:
        return 5400.0 if not report.has_n_reshiram else 1000.0
    if name == DARMANITAN:
        return 4500.0 if report.has_darumaka else 2200.0
    if name == DARUMAKA:
        return 3600.0 if not (report.has_darumaka or report.has_darmanitan) else 500.0
    if name in {YVELTAL, MUNKIDORI}:
        return 900.0
    return 200.0


def score_cyrano_target(state: Any, cid: Optional[int], name: str) -> float:
    card = get_db().get_card(cid)
    if not card or not card.ex:
        return -5000.0
    report = evaluate_target_board(state)
    if name == ZOROARK_EX:
        return 8200.0 if report.zorua_count > report.zoroark_ex_count else 4200.0
    if name == PECHARUNT_EX:
        return 4300.0 if mochi_or_switch_needed(state) else 200.0
    if name == FEZANDIPITI_EX:
        return 3900.0 if support_ex_needed_after_ko(state) else 100.0
    return -1200.0


def score_supporter_search_target(state: Any, name: str) -> float:
    if name == "Boss's Orders":
        return 8500.0 if boss_line_needed(state) else 600.0
    if name == "Black Belt's Training":
        return 7600.0 if black_belt_math_needed(state) else -400.0
    if name == "Cyrano":
        return 5400.0 if evaluate_target_board(state).zoroark_ex_count < 2 else 500.0
    if name == "Lillie's Determination":
        return 5200.0 if hand_count(state) <= 4 else 1200.0
    if name == "Ciphermaniac's Codebreaking":
        return 4200.0 if trade_available(state) else 1500.0
    return 200.0


def score_general_search_target(state: Any, cid: Optional[int], name: str) -> float:
    report = evaluate_target_board(state)
    if name == ZORUA:
        return 6000.0 if report.zorua_count < 2 else 500.0
    if name == ZOROARK_EX:
        return 7000.0 if report.zoroark_ex_count < 2 and report.zorua_count > 0 else 2000.0
    if name == ZEKROM:
        return 5600.0 if not report.has_n_zekrom else 600.0
    if name == RESHIRAM:
        return 5000.0 if not report.has_n_reshiram else 600.0
    if name == DARMANITAN:
        return 3600.0
    if cid == DARKNESS_ENERGY_ID:
        return 4500.0 if report.ready_zoroark_count == 0 else 1400.0
    return 200.0


def option_index_by_name(state: Any, options: Sequence[Any], wanted: str) -> Optional[int]:
    wanted_name = canonical_name(wanted)
    for idx, option in enumerate(options):
        if option_type(option) == OPT_PLAY and option_name(state, option) == wanted_name:
            return idx
    return None


def option_name(state: Any, option: Any) -> str:
    name = canonical_name_from_id(card_id_from_option(state, option))
    if name:
        return name
    for key in ("cardName", "name", "label", "text"):
        raw = str(getv(option, key, "") or "")
        if raw:
            return canonical_name(raw)
    return ""


def is_poffin_eligible_target(cid: Optional[int]) -> bool:
    card = get_db().get_card(cid)
    return bool(card and card.card_type == "Pokemon" and card.basic and 0 < card.hp <= 70)


def safe_discard_count_zoroark(state: Any) -> int:
    return sum(1 for cid in hand_ids(state) if score_discard_selection_zoroark(state, cid) >= 0.0)


def has_in_discard(state: Any, cid: int) -> bool:
    try:
        from state_eval import discard_cards

        return any(card_id(card) == cid for card in discard_cards(state))
    except Exception:
        return False


def early_turn(state: Any) -> bool:
    try:
        return int(getv(state.current, "turn", 0) or 0) <= 4
    except Exception:
        return True


def basic_energy_in_opponent_discard_safe(state: Any) -> bool:
    try:
        from core.target_board import basic_energy_in_opponent_discard

        return basic_energy_in_opponent_discard(state) >= 4
    except Exception:
        return False


def mochi_or_switch_needed(state: Any) -> bool:
    try:
        from core.poison_mochi_planner import mochi_math_available

        return mochi_math_available(state) or bool(evaluate_target_board(state).ready_zoroark_count and evaluate_target_board(state).has_pecharunt_ex)
    except Exception:
        return False


def support_ex_needed_after_ko(state: Any) -> bool:
    logs = getv(state.obs, "logs", []) or []
    text = " ".join(str(log) for log in logs[-8:]).lower() if isinstance(logs, list) else ""
    return "knocked out" in text and not has_in_play(state, FEZANDIPITI_EX)


def exact_supporter_needed(state: Any) -> bool:
    return boss_line_needed(state) or black_belt_math_needed(state) or hand_count(state) <= 3


def boss_line_needed(state: Any) -> bool:
    try:
        from core.copy_target_planner import choose_best_benched_n_attack_to_copy
        from state_eval import bench_pokemon, pokemon_hp

        damage = max(250, choose_best_benched_n_attack_to_copy(state).expected_damage)
        return any(pokemon_hp(pokemon) and pokemon_hp(pokemon) <= damage for pokemon in bench_pokemon(state, getattr(state, "opponent_index", 1)))
    except Exception:
        return False


def black_belt_math_needed(state: Any) -> bool:
    try:
        from card_db import get_db
        from state_eval import active_pokemon, pokemon_hp

        target = active_pokemon(state, getattr(state, "opponent_index", 1))
        info = get_db().get_card(card_id(target))
        hp = pokemon_hp(target)
        return bool(info and info.ex and 250 < hp <= 290)
    except Exception:
        return False


def score_air_balloon_play_zoroark(state: Any, option: Any) -> float:
    try:
        from state_eval import active_pokemon, attach_target_from_option
        from core.target_board import pokemon_name

        target = attach_target_from_option(state, option) or active_pokemon(state)
        target_name = pokemon_name(target)
        if target_name == ZOROARK_EX:
            return 2600.0
        if target_name in {ZEKROM, RESHIRAM, YVELTAL}:
            return 900.0
        if target_name in {PECHARUNT_EX, FEZANDIPITI_EX}:
            return -900.0
        return 300.0
    except Exception:
        return 0.0


def score_watchtower_play(state: Any) -> float:
    if our_abilities_still_matter(state):
        return -3600.0
    if opponent_colorless_ability_seen(state):
        return 3000.0
    return -700.0


def our_abilities_still_matter(state: Any) -> bool:
    report = evaluate_target_board(state)
    return report.ready_zoroark_count == 0 or report.has_pecharunt_ex or report.has_fezandipiti_ex or count_in_play(state, MUNKIDORI) > 0


def opponent_colorless_ability_seen(state: Any) -> bool:
    text = " ".join(str(log) for log in (getv(state.obs, "logs", []) or [])[-16:]).lower()
    return "colorless" in text and "ability" in text


def opponent_tool_or_special_seen(state: Any) -> bool:
    text = " ".join(str(log) for log in (getv(state.obs, "logs", []) or [])[-16:]).lower()
    return "tool" in text or "special energy" in text


def trade_available(state: Any) -> bool:
    try:
        from core.trade_planner import evaluate_trade

        return evaluate_trade(state).should_use
    except Exception:
        return False


def is_discard_context(context: int) -> bool:
    return context in DISCARD_CONTEXTS


def is_search_context(context: int) -> bool:
    return context in SEARCH_CONTEXTS
