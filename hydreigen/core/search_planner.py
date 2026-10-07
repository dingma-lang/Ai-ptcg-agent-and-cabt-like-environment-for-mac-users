from __future__ import annotations

from typing import Any, Optional

from action_classifier import ActionCategory, classify_legal_option
from state_eval import OPT_PLAY, card_id_from_option, getv, hand_cards, option_type
from core.priority_tables import (
    LOW_PRIORITY_DISCARD_IDS,
    PROTECTED_IDS,
    RULE_BOX_IDS,
    SUPPORT_LIABILITY_IDS,
    canonical_name_from_id,
    context_source_name,
    count_in_play,
    deino_count,
    has_in_hand,
    has_in_play,
)
from core.strategy_scope import use_hydreigon_gengar_strategy


def score_search_item_play(state: Any, option: Any) -> float:
    cid = card_id_from_option(state, option)
    name = canonical_name_from_id(cid)
    try:
        from core.combo_presence_planner import score_combo_play_option

        combo_score = score_combo_play_option(state, option)
        if combo_score:
            return combo_score
    except Exception:
        pass
    if name == "Buddy-Buddy Poffin":
        from core.poffin_planner import score_poffin_play

        return max(score_poffin_play(state, option), 80.0)
    if name == "Poke Pad":
        from core.pokepad_planner import score_pokepad_play

        return max(score_pokepad_play(state, option), 120.0)
    if name == "Ultra Ball":
        try:
            from core.ultra_ball_guard import score_ultra_ball_play_safety

            safety = score_ultra_ball_play_safety(state)
            if safety <= -3000.0:
                return safety
        except Exception:
            pass
        try:
            from core.fezandipiti_planner import score_post_ko_fezandipiti_enabler, score_pre_ko_fezandipiti_enabler

            post_ko_score = score_post_ko_fezandipiti_enabler(state, "Ultra Ball")
            if post_ko_score:
                return post_ko_score
            pre_ko_score = score_pre_ko_fezandipiti_enabler(state, "Ultra Ball")
            if pre_ko_score:
                return pre_ko_score
        except Exception:
            pass
        if stage_two_search_needed(state):
            return 6200.0
        if has_in_play(state, "Deino") and (has_in_hand(state, "Rare Candy") or has_in_play(state, "Zweilous")):
            return 420.0
        if count_in_play(state, "Deino") == 0:
            return 360.0
        return 180.0
    if name == "Secret Box":
        try:
            from core.discard_cost_guard import score_discard_cost_play_safety

            safety = score_discard_cost_play_safety(state, "Secret Box", 3)
            if safety <= -4500.0:
                return safety
        except Exception:
            pass
        try:
            from core.setup_recovery_planner import emergency_setup_needed

            if emergency_setup_needed(state):
                return 6900.0
        except Exception:
            pass
        if should_try_secret_box_without_supporter(state):
            return 5600.0 if hydreigon_or_gengar_supporter_needed(state) else 4200.0
        if protected_count_in_hand(state) >= 4:
            return -500.0
        if has_in_play(state, "Deino") and not (has_in_hand(state, "Rare Candy") and has_in_hand(state, "Hydreigon ex")):
            return 260.0
        return 80.0
    return 0.0


def score_search_selection(state: Any, cid: Optional[int]) -> float:
    source = context_source_name(state)
    name = canonical_name_from_id(cid)
    if not name:
        return 0.0
    try:
        from core.combo_presence_planner import score_combo_search_target

        combo_score = score_combo_search_target(state, cid, source)
        if combo_score:
            return combo_score
    except Exception:
        pass
    try:
        from core.fezandipiti_planner import FEZANDIPITI_EX_ID, score_fezandipiti_search_target

        if cid == FEZANDIPITI_EX_ID:
            return score_fezandipiti_search_target(state)
    except Exception:
        pass
    try:
        from core.pivot_planner import PECHARUNT_EX_ID, score_pecharunt_bench

        if cid == PECHARUNT_EX_ID:
            return score_pecharunt_bench(state) * 0.75
    except Exception:
        pass
    if source == "Buddy-Buddy Poffin":
        return score_poffin_target(state, cid)
    if source == "Toxel":
        try:
            from core.call_for_family_planner import score_call_for_family_target as planner_score

            routed = planner_score(state, cid)
            if routed:
                return routed
        except Exception:
            pass
        return score_call_for_family_target(state, cid)
    if source == "Poke Pad":
        return score_poke_pad_target(state, cid, name)
    if source == "Dawn":
        return score_dawn_target(state, cid, name)
    if source == "Team Rocket's Petrel":
        try:
            from core.trainer_search_planner import score_petrel_target_selection

            routed = score_petrel_target_selection(state, cid, name)
            if routed:
                return routed
        except Exception:
            pass
        return score_petrel_target(state, cid, name)
    if source == "Secret Box":
        try:
            from core.secret_box_planner import score_secret_box_target_selection

            routed = score_secret_box_target_selection(state, cid, name)
            if routed:
                return routed
        except Exception:
            pass
        return score_secret_box_target(state, cid, name)
    if source == "Ultra Ball":
        return score_ultra_ball_target(state, name)
    if source == "Crispin":
        from core.energy_planner import crispin_energy_selection_score
        try:
            from core.crispin_planner import score_crispin_energy_selection

            return max(crispin_energy_selection_score(state, cid), score_crispin_energy_selection(state, cid))
        except Exception:
            pass

        return crispin_energy_selection_score(state, cid)
    return generic_search_score(state, name)


def score_poffin_target(state: Any, cid: Optional[int]) -> float:
    from core.poffin_planner import score_poffin_target as planner_score

    return planner_score(state, cid)


def score_call_for_family_target(state: Any, cid: Optional[int]) -> float:
    from card_db import get_db

    card = get_db().get_card(cid)
    if card is None or card.card_type != "Pokemon" or not card.basic:
        return -10000.0
    name = canonical_name_from_id(cid)
    core_ready = has_core_setup_basics(state)
    if name == "Deino":
        if count_in_play(state, "Deino") == 0:
            return 5200.0
        if count_in_play(state, "Deino") == 1 and not core_ready:
            return 4700.0
        return 1200.0
    if name == "Gastly":
        return 5000.0 if not has_in_play(state, "Gastly") else 900.0
    if name == "Toxel":
        return 4200.0 if not (has_in_play(state, "Toxel") or has_in_play(state, "Toxtricity")) else 650.0
    if cid in SUPPORT_LIABILITY_IDS:
        if core_ready:
            if name == "Fezandipiti ex" and not has_in_play(state, "Fezandipiti ex"):
                return 5100.0
            if name == "Pecharunt ex" and not has_in_play(state, "Pecharunt ex"):
                return 5000.0
        if count_in_play(state, "Deino") >= 1 and has_in_play(state, "Gastly"):
            return 3600.0
        return 1800.0
    return 1000.0


def score_poke_pad_target(state: Any, cid: Optional[int], name: str) -> float:
    from core.pokepad_planner import score_pokepad_target as planner_score

    return planner_score(state, cid)


def score_ultra_ball_target(state: Any, name: str) -> float:
    try:
        from core.opponent_model import infer_opponent_next_turn_threat

        threat = infer_opponent_next_turn_threat(state)
        ex_pressure = bool(threat.has_rulebox_attacker or threat.likely_ex_heavy)
    except Exception:
        ex_pressure = False
    if name == "Mega Gengar ex" and has_in_play(state, "Haunter"):
        return 10600.0 if ex_pressure else 10000.0
    if name == "Hydreigon ex" and (has_in_hand(state, "Rare Candy") or has_in_play(state, "Zweilous")):
        return 9800.0
    if name == "Hydreigon ex" and has_in_play(state, "Deino"):
        return 6500.0
    if name == "Deino" and deino_count(state) == 0:
        return 800.0
    if name == "Mega Gengar ex" and has_in_play(state, "Gastly"):
        return 7200.0 if ex_pressure else 6800.0
    if name in {"Fezandipiti ex", "Pecharunt ex"}:
        return -250.0
    return generic_search_score(state, name)


def stage_two_search_needed(state: Any) -> bool:
    return (
        (has_in_play(state, "Haunter") and not has_in_play(state, "Mega Gengar ex"))
        or ((has_in_hand(state, "Rare Candy") or has_in_play(state, "Zweilous")) and has_in_play(state, "Deino") and not has_in_play(state, "Hydreigon ex"))
    )


def score_petrel_target(state: Any, cid: Optional[int], name: str) -> float:
    try:
        from core.setup_recovery_planner import emergency_setup_needed, poffin_trainer_target_score, whole_team_setup_score

        poffin_already_in_hand = has_in_hand(state, "Buddy-Buddy Poffin")
        if emergency_setup_needed(state):
            if name == "Buddy-Buddy Poffin":
                return -1800.0 if poffin_already_in_hand else 9000.0
            if poffin_already_in_hand and name == "Secret Box":
                return 9300.0
            if name == "Poke Pad":
                return 7200.0
            if name == "Ultra Ball":
                return 6200.0
            if name == "Secret Box":
                return 5800.0
        if name == "Buddy-Buddy Poffin":
            if poffin_already_in_hand:
                return -1800.0
            return poffin_trainer_target_score(state)
        return whole_team_setup_score(state, cid)
    except Exception:
        return generic_search_score(state, name)


def score_secret_box_target(state: Any, cid: Optional[int], name: str) -> float:
    try:
        from core.setup_recovery_planner import emergency_setup_needed, poffin_trainer_target_score, whole_team_setup_score

        if name == "Buddy-Buddy Poffin":
            return 9200.0 if emergency_setup_needed(state) else poffin_trainer_target_score(state)
        if name == "Poke Pad":
            return 6200.0
        if name == "Crispin":
            if hydreigon_or_gengar_supporter_needed(state):
                return 9400.0
            return 5600.0
        if name == "Lillie's Determination":
            return 5200.0
        if name == "Dawn":
            return 5000.0
        if name == "Team Rocket's Petrel":
            return 4200.0 if not has_in_hand(state, "Buddy-Buddy Poffin") else 1600.0
        if name == "Battle Cage":
            return 4200.0
        return whole_team_setup_score(state, cid)
    except Exception:
        return generic_search_score(state, name)


def score_dawn_target(state: Any, cid: Optional[int], name: str) -> float:
    try:
        from core.danger_evaluator import our_pokemon_knocked_out_last_turn
        from core.disposable_active_planner import identify_disposable_active
        from core.prize_availability_tracker import infer_card_availability

        availability = infer_card_availability(state, None)
        if name in {"Toxel", "Toxtricity"} and availability.toxel_availability_low:
            return -2500.0
        if name == "Mega Gengar ex" and has_in_play(state, "Haunter"):
            return 9200.0
        if name == "Hydreigon ex" and (has_in_hand(state, "Rare Candy") or has_in_play(state, "Zweilous")):
            return 8500.0
        if name == "Mega Gengar ex" and has_in_play(state, "Gastly"):
            return 7800.0
        if name == "Deino" and (count_in_play(state, "Deino") < 2 or identify_disposable_active(state).opponent_can_ko):
            return 6200.0
        if name == "Zweilous" and has_in_play(state, "Deino") and not has_in_hand(state, "Rare Candy"):
            return 6000.0
        if name == "Gastly" and not has_in_play(state, "Gastly"):
            return 5600.0
        if name == "Haunter" and has_in_play(state, "Gastly"):
            return 5400.0
        if name == "Fezandipiti ex" and (our_pokemon_knocked_out_last_turn(state) or identify_disposable_active(state).opponent_can_ko):
            return 7600.0
    except Exception:
        pass
    try:
        from core.setup_recovery_planner import emergency_setup_needed, whole_team_setup_score

        score = whole_team_setup_score(state, cid)
        if emergency_setup_needed(state):
            if name == "Fezandipiti ex":
                return 24000.0
            if name == "Pecharunt ex":
                return 23000.0
            if name == "Toxtricity":
                return 23500.0
            if name == "Hydreigon ex":
                return 24000.0
            if name == "Mega Gengar ex":
                return 18000.0
            if name == "Deino":
                return 12000.0
            if name == "Gastly":
                return 11200.0
            if name == "Toxel":
                return 10800.0
        return score
    except Exception:
        return generic_search_score(state, name)


def generic_search_score(state: Any, name: str) -> float:
    try:
        from core.setup_recovery_planner import whole_team_setup_score

        team_score = whole_team_setup_score(state, None if not name else card_id_for_search_name(name))
        if team_score:
            return max(team_score, 0.0)
    except Exception:
        pass
    if name == "Deino":
        return 900.0 if deino_count(state) < 1 else 240.0
    if name == "Hydreigon ex":
        return 650.0 if has_in_play(state, "Deino") or has_in_play(state, "Zweilous") else 180.0
    if name == "Rare Candy":
        return 550.0 if has_in_play(state, "Deino") else 150.0
    if name in {"Basic Metal Energy", "Basic Psychic Energy"}:
        return 430.0 if has_in_play(state, "Hydreigon ex") or has_in_play(state, "Deino") else 120.0
    if name == "Zweilous":
        return 360.0 if has_in_play(state, "Deino") else 80.0
    if name == "Mega Gengar ex":
        if has_in_play(state, "Haunter"):
            return 950.0
        return 780.0 if has_in_play(state, "Gastly") else 150.0
    if name in {"Gastly", "Toxel", "Toxtricity"}:
        if name == "Gastly" and not has_in_play(state, "Gastly"):
            return 780.0
        if name == "Toxel" and not (has_in_play(state, "Toxel") or has_in_play(state, "Toxtricity")):
            return 760.0
        return 220.0
    return 0.0


def card_id_for_search_name(name: str) -> Optional[int]:
    try:
        from core.priority_tables import card_id_for_name

        return card_id_for_name(name)
    except Exception:
        return None


def score_discard_selection(state: Any, cid: Optional[int]) -> float:
    if cid is None:
        return 0.0
    if not use_hydreigon_gengar_strategy(state):
        return score_generic_discard_selection(state, cid)
    try:
        from core.priority_tables import context_source_name
        from core.discard_cost_guard import score_discard_cost_card

        source = context_source_name(state)
        if source in {"Ultra Ball", "Secret Box"}:
            return score_discard_cost_card(state, cid, source)
    except Exception:
        pass
    if cid in PROTECTED_IDS:
        return -2200.0
    if cid in LOW_PRIORITY_DISCARD_IDS:
        return 450.0
    name = canonical_name_from_id(cid)
    if name == "Basic Darkness Energy":
        return 220.0
    if duplicate_in_hand(state, cid):
        return 300.0
    return 0.0


def score_generic_discard_selection(state: Any, cid: int) -> float:
    name = canonical_name_from_id(cid)
    if duplicate_in_hand(state, cid):
        return 300.0
    if "Energy" in name:
        return 120.0
    return 0.0


def protected_count_in_hand(state: Any) -> int:
    return sum(1 for card in hand_cards(state) if getv(card, "id") in PROTECTED_IDS)


def duplicate_in_hand(state: Any, cid: int) -> bool:
    return sum(1 for card in hand_cards(state) if getv(card, "id") == cid) >= 2


def should_try_secret_box_without_supporter(state: Any) -> bool:
    if bool(getv(state.current, "supporterPlayed", False)):
        return False
    for idx, option in enumerate(getattr(state, "options", []) or []):
        try:
            if classify_legal_option(state, option, idx).category == ActionCategory.PLAY_SUPPORTER:
                return False
        except Exception:
            continue
    return True


def secret_box_supporter_search_index(state: Any) -> Optional[int]:
    if not should_try_secret_box_without_supporter(state):
        return None
    try:
        from core.discard_cost_guard import score_discard_cost_play_safety

        if score_discard_cost_play_safety(state, "Secret Box", 3) <= -4500.0:
            return None
    except Exception:
        pass
    if protected_count_in_hand(state) >= 4:
        return None
    for idx, option in enumerate(getattr(state, "options", []) or []):
        if option_type(option) != OPT_PLAY:
            continue
        if canonical_name_from_id(card_id_from_option(state, option)) == "Secret Box":
            return idx
    return None


def hydreigon_or_gengar_supporter_needed(state: Any) -> bool:
    try:
        from core.supporter_planner import crispin_hydreigon_energy_score, crispin_mega_gengar_energy_score

        if max(crispin_hydreigon_energy_score(state), crispin_mega_gengar_energy_score(state)) >= 700.0:
            return True
    except Exception:
        pass
    return (
        (has_in_play(state, "Hydreigon ex") or has_in_play(state, "Mega Gengar ex"))
        and not any(has_in_hand(state, name) for name in ("Crispin", "Lillie's Determination", "Dawn", "Team Rocket's Petrel"))
    )


def has_core_setup_basics(state: Any) -> bool:
    return count_in_play(state, "Deino") >= 1 and has_in_play(state, "Gastly") and (
        has_in_play(state, "Toxel") or has_in_play(state, "Toxtricity")
    )
