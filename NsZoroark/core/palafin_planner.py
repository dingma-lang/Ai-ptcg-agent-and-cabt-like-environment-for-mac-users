from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

from card_db import get_db
from state_eval import (
    CTX_ATTACH_TO,
    CTX_DISCARD,
    CTX_DISCARD_CARD_OR_ATTACHED_CARD,
    CTX_DISCARD_ENERGY,
    CTX_DISCARD_ENERGY_CARD,
    CTX_DISCARD_TOOL_CARD,
    CTX_EFFECT_TARGET,
    CTX_EVOLVE,
    CTX_EVOLVES_FROM,
    CTX_EVOLVES_TO,
    CTX_LOOK,
    CTX_SWITCH,
    CTX_TO_ACTIVE,
    CTX_TO_BENCH,
    CTX_TO_FIELD,
    CTX_TO_HAND,
    OPT_ABILITY,
    OPT_ATTACK,
    OPT_ATTACH,
    OPT_CARD,
    OPT_ENERGY,
    OPT_ENERGY_CARD,
    OPT_EVOLVE,
    OPT_PLAY,
    OPT_RETREAT,
    OPT_TOOL_CARD,
    active_pokemon,
    attach_target_from_option,
    attached_card_ids,
    bench_pokemon,
    bench_space,
    card_id,
    card_id_from_option,
    deck_count,
    discard_cards,
    get_pokemon_by_area,
    getv,
    hand_cards,
    hand_count,
    iter_in_play,
    option_type,
    pokemon_energy_count,
    pokemon_from_card_option,
    pokemon_hp,
    prize_count,
)
from deck_profile import load_deck_ids
from core.priority_tables import (
    DRAGONITE_LINE_IDS,
    PALAFIN_LINE_IDS,
    RULE_BOX_IDS,
    canonical_name_from_id,
    context_source_name,
    count_in_play,
    has_in_hand,
    has_in_play,
)
from core.target_board import EARLY, evaluate_target_board


FINIZEN = 105
PALAFIN = 106
PALAFIN_EX = 107
TATSUGIRI = 122
DRATINI = 902
DRAGONAIR = 903
MEGA_DRAGONITE_EX = 904

WATER_ENERGY = 3
LIGHTNING_ENERGY = 4
POFFIN = 1086
SECRET_BOX = 1092
ENERGY_RETRIEVAL = 1118
SWITCH = 1123
SACRED_ASH = 1129
POKE_PAD = 1152
AIR_BALLOON = 1174
BOSS = 1182
KIERAN = 1191
CRISPIN = 1198
PETREL = 1219
HILDA = 1225
LILLIE = 1227
SURFING_BEACH = 1262

PALAFIN_NAMES = {"Finizen", "Palafin", "Palafin ex"}
DRAGONITE_NAMES = {"Dratini", "Dragonair", "Mega Dragonite ex"}
WATER_SWITCH_NAMES = {"Finizen", "Palafin", "Palafin ex"}
SWITCH_CARD_NAMES = {"Surfing Beach", "Switch", "Air Balloon", "Kieran"}
SUPPORTER_NAMES = {"Lillie's Determination", "Team Rocket's Petrel", "Boss's Orders", "Crispin", "Hilda", "Kieran"}
RECOVERY_NAMES = {"Energy Retrieval", "Night Stretcher", "Sacred Ash"}


@dataclass(frozen=True)
class PalafinPlan:
    should_act: bool
    option_index: Optional[int] = None
    score: float = 0.0
    reason: str = ""


def score_palaking_option(state: Any, option: Any, base_score: float = 0.0, option_index: int = 0) -> float:
    typ = option_type(option)
    cid = card_id_from_option(state, option)
    name = canonical_name_from_id(cid)
    context = getattr(state, "context", 0)

    if typ == OPT_PLAY:
        return score_play_option(state, option, name, cid, option_index)
    if typ == OPT_EVOLVE:
        return score_evolve_option(state, option, name, cid)
    if typ == OPT_ATTACH:
        return score_attach_option(state, option, name, cid)
    if typ == OPT_ABILITY:
        return score_ability_option(state, option, name, cid)
    if typ == OPT_RETREAT:
        return score_retreat_option(state)
    if typ == OPT_ATTACK:
        return score_attack_option(state, option, base_score)
    if typ in (OPT_CARD, OPT_TOOL_CARD, OPT_ENERGY_CARD, OPT_ENERGY):
        if context in (CTX_DISCARD, CTX_DISCARD_CARD_OR_ATTACHED_CARD, CTX_DISCARD_ENERGY, CTX_DISCARD_ENERGY_CARD, CTX_DISCARD_TOOL_CARD):
            return score_discard_selection(state, cid)
        return score_selection_option(state, option, name, cid, context)
    return 0.0


def palaking_setup_ability_attack_index(state: Any, legal_options: Sequence[Any]) -> Optional[int]:
    best: tuple[float, Optional[int]] = (0.0, None)
    for idx, option in enumerate(legal_options):
        if option_type(option) != OPT_ATTACK:
            continue
        if not is_setup_ability_attack(state, option):
            continue
        score = score_attack_option(state, option, 0.0)
        if score > best[0]:
            best = (score, idx)
    if best[0] >= 8000.0:
        return best[1]
    return None


def is_setup_ability_attack(state: Any, option: Any) -> bool:
    attack = get_db().get_attack(getv(option, "attackId"))
    attack_name = str(getattr(attack, "name", "") or "")
    attack_text = str(getattr(attack, "text", "") or "")
    text = f"{attack_name} {attack_text}".lower()
    if "attract customers" in text and active_name(state) == "Tatsugiri":
        return True
    if "evolutionary guidance" in text:
        return dragonair_ability_ready(state)
    return attack_name.startswith("[Ability]") or text.startswith("[ability]")


def palaking_basic_bench_from_hand_index(state: Any, legal_options: Sequence[Any]) -> Optional[int]:
    if bench_space(state) <= 0:
        return None
    best: tuple[float, Optional[int]] = (0.0, None)
    for idx, option in enumerate(legal_options):
        if option_type(option) != OPT_PLAY:
            continue
        cid = card_id_from_option(state, option)
        card = get_db().get_card(cid)
        if not card or card.card_type != "Pokemon" or not card.basic:
            continue
        score = score_basic_bench(state, canonical_name_from_id(cid)) + 12000.0
        if score > best[0]:
            best = (score, idx)
    if best[0] > 0.0:
        return best[1]
    return None


def score_palafin_plan(state: Any, legal_options: Sequence[Any]) -> PalafinPlan:
    best = PalafinPlan(False, reason="No Palafin setup option.")
    for idx, option in enumerate(legal_options):
        score = score_palaking_option(state, option, 0.0, idx)
        if score > best.score:
            best = PalafinPlan(score > 0.0, idx, score, palafin_reason_for_option(state, option))
    return best


def score_play_option(state: Any, option: Any, name: str, cid: Optional[int], option_index: int) -> float:
    card = get_db().get_card(cid)
    score = 0.0

    if card and card.card_type == "Pokemon" and card.basic and bench_space(state) > 0:
        score += score_basic_bench(state, name)

    if name == "Buddy-Buddy Poffin":
        score += score_poffin_play(state)
    elif name == "Poke Pad":
        score += score_pokepad_play(state)
    elif name == "Secret Box":
        score += score_secret_box_play(state)
    elif name == "Surfing Beach":
        score += score_surfing_beach_play(state)
    elif name == "Switch":
        score += score_switch_card_play(state, "Switch")
    elif name == "Air Balloon":
        score += score_air_balloon_play_or_attach(state, option)
    elif name == "Kieran":
        score += score_kieran_play(state)
    elif name == "Crispin":
        score += score_crispin_play(state)
    elif name == "Hilda":
        score += score_hilda_play(state)
    elif name == "Team Rocket's Petrel":
        score += score_petrel_play(state)
    elif name == "Lillie's Determination":
        score += score_lillie_play(state)
    elif name == "Boss's Orders":
        score += 420.0 if boss_has_prize_value(state) else -600.0
    elif name in RECOVERY_NAMES:
        score += score_recovery_play(state, name)

    if name in {"Buddy-Buddy Poffin", "Poke Pad", "Secret Box", "Surfing Beach", "Switch"}:
        score += 150.0
    return score


def score_basic_bench(state: Any, name: str) -> float:
    if name == "Finizen":
        current = count_in_play(state, "Finizen") + count_in_play(state, "Palafin") + count_in_play(state, "Palafin ex")
        if current == 0:
            return 7200.0
        if current == 1:
            return 5600.0
        return 2200.0
    if name == "Dratini":
        if dragonite_line_count(state) == 0:
            return 4300.0 if palafin_line_count(state) >= 1 else 2500.0
        return 1200.0
    if name == "Tatsugiri":
        if count_in_play(state, "Tatsugiri") == 0 and bench_space(state) >= 1:
            return 3000.0 if supporter_access_needed(state) else 1500.0
        return 400.0
    return 0.0


def score_poffin_play(state: Any) -> float:
    if bench_space(state) <= 0:
        return -3000.0
    report = evaluate_target_board(state)
    if not poffin_targets_likely_remaining(state):
        return -900.0
    if report.finizen_count + report.palafin_count + report.palafin_ex_count == 0:
        return 7800.0
    if report.finizen_count + report.palafin_count + report.palafin_ex_count == 1:
        return 7200.0
    if report.finizen_count + report.palafin_count + report.palafin_ex_count < 4 and report.open_bench_slots > 0:
        return 6100.0
    if report.open_bench_slots >= 2 and not report.has_tatsugiri and supporter_access_needed(state):
        return 5800.0
    if report.open_bench_slots > 0 and not report.has_tatsugiri:
        return 5200.0
    if report.board_stage == EARLY and report.open_bench_slots > 0:
        return 4600.0
    return 2600.0


def score_pokepad_play(state: Any) -> float:
    if has_ready_finizen_for_palafin(state) and not has_in_hand(state, "Palafin"):
        return 8200.0
    if dragonite_line_count(state) == 0 and not has_in_hand(state, "Dratini"):
        try:
            from core.finizen_setup_planner import finizen_setup_stable

            return 7600.0 if finizen_setup_stable(state) else 3600.0
        except Exception:
            return 7600.0
    if count_in_play(state, "Finizen") == 0 and not has_in_hand(state, "Buddy-Buddy Poffin"):
        return 4600.0
    if count_in_play(state, "Dratini") > 0 and count_in_play(state, "Dragonair") == 0:
        return 3900.0
    if supporter_access_needed(state) and not has_in_play(state, "Tatsugiri"):
        return 2500.0
    return 450.0


def score_secret_box_play(state: Any) -> float:
    try:
        from core.palafin_evolution_guard import score_before_palafin_evolution_guard

        guard = score_before_palafin_evolution_guard(state, {"type": OPT_PLAY, "cardId": SECRET_BOX})
        if guard <= -5000.0:
            return guard
    except Exception:
        pass
    safety = secret_box_discard_safety(state)
    if safety <= -4500.0:
        return safety
    if secret_box_palafin_chain_available(state):
        return 7800.0 + safety
    if bench_space(state) > 0 and not has_in_hand(state, "Buddy-Buddy Poffin") and palafin_line_count(state) < 2:
        return 6200.0 + safety
    if not bool(getv(state.current, "supporterPlayed", False)) and not legal_supporter_in_options(state):
        return 4800.0 + safety
    if missing_switch_engine(state):
        return 4300.0 + safety
    return -500.0 + safety


def score_surfing_beach_play(state: Any) -> float:
    if own_stadium_name(state) == "Surfing Beach":
        return -6000.0
    active_name = canonical_name_from_id(card_id(active_pokemon(state)))
    if active_name == "Palafin" and bench_has_water_switch_target(state):
        return 7600.0
    if active_name == "Palafin ex" and palafin_ex_reset_or_recharge_ready(state):
        return 8800.0 if palafin_ex_recharge_loop_available(state) else 7600.0
    if palafin_line_count(state) > 0 and bench_space(state) >= 0:
        return 3400.0
    return 900.0


def score_switch_card_play(state: Any, source_name: str) -> float:
    try:
        from core.switch_usage_guard import score_switch_usage

        cid = SWITCH if source_name == "Switch" else KIERAN if source_name == "Kieran" else SURFING_BEACH
        guarded = score_switch_usage(state, {"type": OPT_PLAY, "cardId": cid})
        if guarded.score:
            return guarded.score
    except Exception:
        pass
    active_name = canonical_name_from_id(card_id(active_pokemon(state)))
    if active_name == "Palafin" and bench_has_water_switch_target(state):
        return 7200.0
    if active_name == "Palafin ex" and palafin_ex_reset_or_recharge_ready(state):
        return 7600.0 if palafin_ex_recharge_loop_available(state) else 6500.0
    return -7000.0 if source_name == "Switch" else 0.0


def score_kieran_play(state: Any) -> float:
    if score_switch_card_play(state, "Kieran") >= 3000.0:
        return 5000.0
    if kieran_plus_damage_creates_visible_ko(state):
        return 6200.0
    return -300.0


def score_crispin_play(state: Any) -> float:
    if active_palafin_ex_missing_energy(state):
        return 6800.0
    if dragonite_energy_gap(state) >= 2:
        return 6200.0
    if dragonite_line_count(state) > 0 and has_in_hand(state, "Basic Lightning Energy"):
        return 3600.0
    if palafin_line_count(state) > 0 and not palafin_has_water_attached(state):
        return 2700.0
    return -400.0


def score_hilda_play(state: Any) -> float:
    if active_palafin_ex_missing_energy(state):
        return 6400.0
    if has_ready_finizen_for_palafin(state):
        return 5600.0
    if count_in_play(state, "Dratini") > 0 and count_in_play(state, "Dragonair") == 0:
        return 4700.0
    if count_in_play(state, "Dragonair") > 0 and count_in_play(state, "Mega Dragonite ex") == 0:
        return 5200.0
    return 1200.0


def score_petrel_play(state: Any) -> float:
    if bool(getv(state.current, "supporterPlayed", False)):
        return -5000.0
    if low_bench_with_both_engine_roots(state) and not has_in_hand(state, "Buddy-Buddy Poffin"):
        return 7600.0
    package_score = secret_box_petrel_package_score(state)
    if package_score >= 7600.0 and not has_in_hand(state, "Secret Box"):
        return package_score
    if bench_space(state) > 0 and palafin_line_count(state) < 2 and not has_in_hand(state, "Buddy-Buddy Poffin"):
        return 6400.0
    if secret_box_palafin_chain_available(state) and not has_in_hand(state, "Surfing Beach"):
        return 5900.0
    if active_name(state) == "Palafin" and not any(has_in_hand(state, name) for name in ("Surfing Beach", "Switch", "Kieran")):
        return 5600.0
    if has_ready_finizen_for_palafin(state) and not has_in_hand(state, "Poke Pad"):
        return 4800.0
    return -500.0 if has_in_hand(state, "Buddy-Buddy Poffin") and bench_space(state) > 0 else 650.0


def score_lillie_play(state: Any) -> float:
    try:
        from core.palafin_evolution_guard import score_before_palafin_evolution_guard

        guard = score_before_palafin_evolution_guard(state, {"type": OPT_PLAY, "cardId": LILLIE})
        if guard <= -4000.0:
            return guard
    except Exception:
        pass
    if deck_count(state) <= 4:
        return -9000.0
    if has_in_hand(state, "Buddy-Buddy Poffin") and bench_space(state) > 0 and palafin_line_count(state) < 2:
        return -3600.0
    overloaded_palafin_ex = palafin_ex_overloaded_in_hand(state)
    if zero_to_hero_combo_ready(state) and not overloaded_palafin_ex:
        return -5000.0
    try:
        from core.lillie_guard import useful_action_before_lillie

        precheck = useful_action_before_lillie(state)
        if precheck.should_wait:
            return -4200.0
    except Exception:
        pass
    if overloaded_palafin_ex:
        return 8800.0
    if exact_setup_supporter_legal_before_lillie(state):
        return -2600.0
    if low_bench_setup_emergency(state):
        return 11200.0
    if hand_count(state) <= 4:
        return 5200.0
    if evaluate_target_board(state).board_stage == EARLY and not has_ready_finizen_for_palafin(state):
        return 2700.0
    return 650.0


def low_bench_setup_emergency(state: Any) -> bool:
    if bench_space(state) <= 0:
        return False
    if len(bench_pokemon(state)) >= 2:
        return False
    if has_in_hand(state, "Buddy-Buddy Poffin"):
        return False
    if playable_basic_in_hand(state):
        return False
    if setup_ability_legal(state):
        return False
    if exact_setup_supporter_legal_before_lillie(state):
        return False
    if palafin_line_count(state) >= 2 and (dragonite_line_count(state) > 0 or has_in_play(state, "Tatsugiri")):
        return False
    return True


def playable_basic_in_hand(state: Any) -> bool:
    for hand_card in hand_cards(state):
        card = get_db().get_card(card_id(hand_card))
        if card and card.card_type == "Pokemon" and card.basic:
            return True
    return False


def setup_ability_legal(state: Any) -> bool:
    for idx, option in enumerate(getattr(state, "options", []) or []):
        typ = option_type(option)
        cid = card_id_from_option(state, option)
        name = canonical_name_from_id(cid)
        if typ == OPT_ABILITY and score_ability_option(state, option, name, cid) >= 5000.0:
            return True
        if typ == OPT_ATTACK and is_setup_ability_attack(state, option):
            return True
    return False


def exact_setup_supporter_legal_before_lillie(state: Any) -> bool:
    for option in getattr(state, "options", []) or []:
        if option_type(option) != OPT_PLAY:
            continue
        name = canonical_name_from_id(card_id_from_option(state, option))
        if name == "Team Rocket's Petrel" and score_petrel_play(state) >= 3500.0:
            return True
        if name == "Hilda" and score_hilda_play(state) >= 3500.0:
            return True
        if name == "Crispin" and score_crispin_play(state) >= 3500.0:
            return True
        if name == "Kieran" and score_kieran_play(state) >= 3500.0:
            return True
    return False


def score_recovery_play(state: Any, name: str) -> float:
    discard_names = [canonical_name_from_id(card_id(card)) for card in discard_cards(state)]
    energy_discards = discard_names.count("Basic Water Energy") + discard_names.count("Basic Lightning Energy")
    key_pokemon_discards = sum(1 for name_ in discard_names if name_ in PALAFIN_NAMES or name_ in DRAGONITE_NAMES)
    if name == "Energy Retrieval":
        if energy_discards >= 2 and (palafin_line_count(state) > 0 or dragonite_line_count(state) > 0):
            return 3200.0
        return -900.0
    if name == "Night Stretcher":
        return 3000.0 if key_pokemon_discards >= 1 or energy_discards >= 1 else -700.0
    if name == "Sacred Ash":
        if key_pokemon_discards >= 3:
            return 8800.0
        if all_piece_lost(discard_names, "Finizen") or all_piece_lost(discard_names, "Dratini"):
            return 8200.0
        return -1200.0
    return 0.0


def score_evolve_option(state: Any, option: Any, name: str, cid: Optional[int]) -> float:
    target = attach_target_from_option(state, option)
    if target is None:
        target = get_pokemon_by_area(state, getv(option, "inPlayArea"), getv(option, "inPlayIndex"), state.your_index)
    target_name = canonical_name_from_id(card_id(target))
    target_energy = pokemon_energy_count(target) if target is not None else 0
    if name == "Palafin" and target_name == "Finizen":
        score = 6800.0
        if target is active_pokemon(state):
            score += 900.0
        if target_energy > 0:
            score += 450.0
        return score
    if name == "Palafin ex":
        return -9000.0
    if name == "Dragonair" and target_name == "Dratini":
        return 4200.0 + target_energy * 350.0
    if name == "Mega Dragonite ex" and target_name == "Dragonair":
        return 5200.0 + target_energy * 500.0
    return 0.0


def score_attach_option(state: Any, option: Any, name: str, cid: Optional[int]) -> float:
    target = attach_target_from_option(state, option)
    target_name = canonical_name_from_id(card_id(target))
    if cid in (WATER_ENERGY, LIGHTNING_ENERGY):
        return score_energy_attachment(state, cid, target)
    if name == "Air Balloon":
        return score_air_balloon_play_or_attach(state, option)
    if target_name in {"Palafin ex", "Tatsugiri"}:
        return 1800.0
    return 0.0


def score_energy_attachment(state: Any, energy_cid: Optional[int], target: Any) -> float:
    target_name = canonical_name_from_id(card_id(target))
    if energy_cid is None or target is None:
        return 0.0
    if target_name in PALAFIN_NAMES and energy_cid != WATER_ENERGY:
        return -100000.0
    current_energy = attached_energy_count_any(target)
    if target_name == "Tatsugiri":
        return -100000.0
    if energy_cid == WATER_ENERGY:
        if target_name == "Palafin ex":
            return 7000.0 if current_energy == 0 else -100000.0
        if target_name == "Palafin":
            return 4200.0 if current_energy == 0 else -1200.0
        if target_name == "Finizen":
            return 3200.0 if current_energy == 0 and has_in_hand(state, "Palafin") else 900.0
        if target_name in DRAGONITE_NAMES:
            if palafin_ex_attackers_have_exact_water(state) and dragonite_attack_plan_realistic(state) and current_energy < 3:
                return 5200.0 if target_name in {"Dragonair", "Mega Dragonite ex"} else 4200.0
            return 2600.0 if dragonite_attack_plan_realistic(state) and current_energy < 3 else -700.0
        return -1200.0
    if energy_cid == LIGHTNING_ENERGY:
        if target_name in DRAGONITE_NAMES:
            if attached_energy_count(target, LIGHTNING_ENERGY) >= 2:
                return -2500.0
            return 5600.0 if dragonite_line_count(state) > 0 else 3200.0
        if target_name in PALAFIN_NAMES or target_name == "Tatsugiri":
            return -100000.0 if target_name == "Palafin ex" and current_energy >= 1 else -6500.0
        return -5000.0
    return 0.0


def score_air_balloon_play_or_attach(state: Any, option: Any) -> float:
    try:
        from core.air_balloon_planner import score_air_balloon_target

        decision = score_air_balloon_target(state, option)
        if decision.score:
            return decision.score
    except Exception:
        pass
    target = attach_target_from_option(state, option)
    target_name = canonical_name_from_id(card_id(target))
    if target_name == "Palafin" and target is active_pokemon(state):
        return 6500.0
    if target_name == "Palafin ex":
        if target_is_active(state, target) and palafin_ex_reset_or_recharge_ready(state):
            return 7200.0 if palafin_ex_recharge_loop_available(state) else 5600.0
        return -6000.0
    if target_name == "Tatsugiri":
        if target_is_active(state, target):
            return 8800.0
        if active_name(state) == "Palafin ex" or count_in_play(state, "Mega Dragonite ex") > 0:
            return 6800.0
        if count_in_play(state, "Dragonair") > 0:
            return 5200.0
        return 3600.0
    if target_name in {"Dragonair", "Mega Dragonite ex"} and not has_in_play(state, "Tatsugiri"):
        return -6000.0
    return -6000.0 if target is not None else 1500.0


def score_ability_option(state: Any, option: Any, name: str, cid: Optional[int]) -> float:
    text = card_text(cid).lower()
    if name == "Palafin" or "zero to hero" in text:
        if palafin_ex_overloaded_in_hand(state) and lillie_play_option_legal(state):
            return -9000.0
        return 9000.0
    if name == "Tatsugiri" or "attract customers" in text:
        if active_name(state) == "Tatsugiri" and not bool(getv(state.current, "supporterPlayed", False)):
            return 9600.0
        return 3600.0 if not bool(getv(state.current, "supporterPlayed", False)) else 1200.0
    if name == "Dragonair" or "evolutionary guidance" in text:
        if not dragonair_ability_ready(state):
            return -10000.0
        return max(8200.0, dragonair_ability_need_score(state))
    if name == "Mega Dragonite ex" or "sky transport" in text:
        active = active_name(state)
        if active == "Palafin ex" and active_palafin_ex_can_giga_impact(state):
            return -4500.0
        if active == "Palafin" and zero_to_hero_combo_ready(state):
            return 7200.0
        if active == "Palafin ex" and palafin_ex_reset_or_recharge_ready(state):
            return 9000.0 if tatsugiri_balloon_reset_pivot_available(state) else 8200.0
        if active == "Palafin ex" and active_palafin_ex_needs_visible_recharge(state):
            return 7600.0
        return -5000.0
    return 0.0


def score_retreat_option(state: Any) -> float:
    active = active_pokemon(state)
    name = canonical_name_from_id(card_id(active))
    if name == "Mega Dragonite ex":
        return -100000.0
    if not palaking_switch_or_retreat_allowed(state):
        return -9000.0
    if retreat_discards_energy_without_urgency(state):
        return -9000.0
    if name == "Tatsugiri" and pokemon_has_air_balloon_attached(active) and bench_has_ready_attacker(state):
        return 8200.0
    if name == "Palafin" and bench_has_water_switch_target(state):
        return 7800.0
    if name == "Palafin ex" and palafin_ex_reset_or_recharge_ready(state):
        return 7600.0 if palafin_ex_recharge_loop_available(state) else 6500.0
    return -9000.0


def score_attack_option(state: Any, option: Any, base_score: float) -> float:
    active = active_pokemon(state)
    name = canonical_name_from_id(card_id(active))
    attack = get_db().get_attack(getv(option, "attackId"))
    attack_name = str(getattr(attack, "name", "") or "")
    attack_text = str(getattr(attack, "text", "") or "")
    combined_text = f"{attack_name} {attack_text}".lower()
    if name == "Tatsugiri" and "attract customers" in combined_text:
        if bool(getv(state.current, "supporterPlayed", False)):
            return 2600.0
        return 16500.0
    if "evolutionary guidance" in combined_text:
        if not dragonair_ability_ready(state):
            return -10000.0
        return max(8600.0, dragonair_ability_need_score(state))
    if name == "Palafin ex":
        try:
            from core.giga_impact_planner import score_giga_impact_attack

            giga = score_giga_impact_attack(state, option)
            if giga.score:
                return giga.score
        except Exception:
            pass
        if pokemon_energy_count(active) <= 0:
            return -5000.0
        return 1600.0 if base_score < 10000.0 else 5200.0
    if name == "Mega Dragonite ex":
        if base_score >= 10000.0:
            return 6000.0
        return -2500.0 if "Ryuno" in attack_name or "Glide" in attack_name else 700.0
    if name == "Palafin":
        return -2500.0
    if name == "Finizen" and palafin_line_count(state) <= 1:
        return -1200.0
    return 0.0


def score_selection_option(state: Any, option: Any, name: str, cid: Optional[int], context: int) -> float:
    source = context_source_name(state)
    if context == CTX_TO_ACTIVE:
        target = pokemon_from_card_option(state, option)
        return score_promote_target(state, target)
    if context == CTX_SWITCH:
        target = pokemon_from_card_option(state, option)
        return score_switch_target(state, target, source)
    if context == CTX_ATTACH_TO:
        target = pokemon_from_card_option(state, option)
        if target is None:
            target = attach_target_from_option(state, option)
        return score_attach_target(state, target, source)
    if context in (CTX_EVOLVES_FROM, CTX_EVOLVES_TO, CTX_EVOLVE):
        return score_evolution_selection(state, name)
    if source == "Buddy-Buddy Poffin":
        return score_poffin_target(state, cid, name)
    if source == "Poke Pad":
        return score_pokepad_target(state, cid, name)
    if source == "Secret Box":
        return score_secret_box_target(state, name)
    if source == "Team Rocket's Petrel":
        return score_petrel_target(state, name)
    if source == "Hilda":
        return score_hilda_target(state, name)
    if source == "Crispin":
        return score_crispin_target(state, cid, name)
    if source in {"Palafin", "Zero to Hero"} or "zero" in str(source).lower():
        return 9500.0 if name == "Palafin ex" else -500.0
    if is_dragonair_source(source):
        return score_dragonair_evolution_target(state, name)
    if is_tatsugiri_source(source):
        return score_tatsugiri_supporter_target(state, name)
    if context in (CTX_TO_HAND, CTX_LOOK, CTX_TO_BENCH, CTX_TO_FIELD, CTX_EFFECT_TARGET):
        return generic_target_score(state, cid, name)
    return 0.0


def score_poffin_target(state: Any, cid: Optional[int], name: str) -> float:
    card = get_db().get_card(cid)
    if not card or card.card_type != "Pokemon" or not card.basic or card.hp > 70:
        return -10000.0
    line_count = palafin_line_count(state)
    if name == "Finizen":
        if line_count == 0:
            return 8200.0
        if line_count == 1:
            return 7600.0
        if line_count < 4:
            return 5600.0
        return 2400.0
    if name == "Tatsugiri":
        if not has_in_play(state, "Tatsugiri"):
            return 6800.0 if supporter_access_needed(state) else 5400.0
        return 1800.0
    if name == "Dratini":
        return -10000.0
    return 500.0


def score_pokepad_target(state: Any, cid: Optional[int], name: str) -> float:
    try:
        from core.pokepad_dragonite_planner import score_pokepad_target_from_plan

        planned = score_pokepad_target_from_plan(state, name)
        if planned:
            if planned < 0.0:
                return planned
            return planned + (3500.0 if name == "Palafin" else 2500.0)
    except Exception:
        pass
    if cid in RULE_BOX_IDS:
        return -6500.0
    if name == "Dragonair" and count_in_play(state, "Dratini") == 0:
        return -9000.0
    if name == "Dratini" and dragonite_line_count(state) == 0 and not has_in_hand(state, "Dratini"):
        return 8600.0
    if name == "Palafin" and count_in_play(state, "Finizen") > 0:
        return 7400.0
    if name == "Finizen":
        return 5600.0 if palafin_line_count(state) == 0 else 2600.0
    if name == "Dratini" and dragonite_line_count(state) == 0:
        return 6200.0
    if name == "Dragonair" and count_in_play(state, "Dratini") > 0:
        return 5400.0
    if name == "Tatsugiri" and supporter_access_needed(state):
        return 3200.0
    return generic_target_score(state, cid, name)


def score_secret_box_target(state: Any, name: str) -> float:
    try:
        from core.secret_box_palafin_guard import score_secret_box_item_target

        guard = score_secret_box_item_target(state, name)
        if guard:
            return guard + (1200.0 if name == "Buddy-Buddy Poffin" else 0.0)
    except Exception:
        pass
    if name == "Poke Pad":
        if dragonite_line_count(state) == 0 and not has_in_hand(state, "Dratini"):
            return 8600.0
        return 8200.0 if active_name(state) == "Finizen" and not has_in_hand(state, "Palafin") else 5200.0
    if name == "Air Balloon":
        return 7800.0 if active_name(state) in {"Palafin", "Palafin ex"} else 4600.0
    if name == "Surfing Beach":
        return 7600.0 if secret_box_palafin_chain_available(state) or missing_switch_engine(state) else 4200.0
    if name == "Switch":
        return 6200.0 if active_name(state) == "Palafin" else 3600.0
    if name == "Hilda":
        return 5600.0
    if name == "Crispin":
        if active_palafin_ex_missing_energy(state):
            return 6800.0
        return 5200.0 if dragonite_line_count(state) > 0 else 2600.0
    if name == "Lillie's Determination":
        if hand_count(state) <= 4:
            return 8400.0
        return 6200.0 if hand_count(state) <= 5 else 3000.0
    if name == "Team Rocket's Petrel":
        return 4600.0 if not has_in_hand(state, "Buddy-Buddy Poffin") else 2200.0
    if name == "Buddy-Buddy Poffin":
        return 7000.0 if palafin_line_count(state) < 2 and bench_space(state) > 0 else -1200.0
    return generic_target_score(state, None, name)


def score_petrel_target(state: Any, name: str) -> float:
    if name == "Buddy-Buddy Poffin" and low_bench_with_both_engine_roots(state):
        return -8000.0 if has_in_hand(state, "Buddy-Buddy Poffin") else 9200.0
    try:
        from core.secret_box_palafin_guard import score_petrel_poffin_target
        from core.petrel_exact_search_planner import score_petrel_exact_target

        poffin_guard = score_petrel_poffin_target(state, name)
        if poffin_guard:
            return poffin_guard
        exact = score_petrel_exact_target(state, name)
        if exact.score:
            return exact.score
    except Exception:
        pass
    if name == "Buddy-Buddy Poffin":
        return -2500.0 if has_in_hand(state, "Buddy-Buddy Poffin") else (7800.0 if poffin_targets_likely_remaining(state) else 1200.0)
    if name == "Surfing Beach":
        try:
            from core.pokepad_dragonite_planner import needed_non_rulebox_evolution_piece

            if needed_non_rulebox_evolution_piece(state) == "Palafin" and not has_in_hand(state, "Poke Pad"):
                return 1600.0
        except Exception:
            pass
        return 7200.0 if missing_switch_engine(state) or active_name(state) == "Palafin" else 2600.0
    if name == "Switch":
        return 6600.0 if active_name(state) == "Palafin" else 2400.0
    if name == "Poke Pad":
        try:
            from core.pokepad_dragonite_planner import dratini_in_play, needed_non_rulebox_evolution_piece

            needed = needed_non_rulebox_evolution_piece(state)
            if needed == "Dragonair" and not dratini_in_play(state):
                return -8000.0
            if needed not in {"Palafin", "Dratini", "Dragonair", "Tatsugiri"} and not has_ready_finizen_for_palafin(state):
                return -2500.0
            if not dratini_in_play(state) and has_in_hand(state, "Dratini") and needed != "Dratini" and not has_ready_finizen_for_palafin(state):
                return -3500.0
        except Exception:
            pass
        if has_ready_finizen_for_palafin(state) and not has_in_hand(state, "Palafin"):
            return 9000.0
        if dragonite_line_count(state) == 0 and not has_in_hand(state, "Dratini"):
            return 8400.0
        return 6200.0 if has_ready_finizen_for_palafin(state) else 2800.0
    if name == "Secret Box":
        return secret_box_petrel_package_score(state)
    if name == "Air Balloon":
        return 4800.0 if active_name(state) in {"Palafin", "Palafin ex", "Tatsugiri"} else 1600.0
    if name in RECOVERY_NAMES:
        return score_recovery_play(state, name)
    return 800.0


def secret_box_petrel_package_score(state: Any) -> float:
    if has_in_hand(state, "Secret Box"):
        return -1800.0
    safety = secret_box_discard_safety(state)
    if safety <= -4500.0:
        return -3000.0

    pieces = 0
    score = 5000.0 + safety
    if poffin_targets_likely_remaining(state) and not has_in_hand(state, "Buddy-Buddy Poffin") and bench_space(state) > 0:
        pieces += 1
        score += 1800.0
    if dragonite_line_count(state) == 0 and not has_in_hand(state, "Dratini") and not has_in_hand(state, "Poke Pad"):
        pieces += 1
        score += 1800.0
    if has_ready_finizen_for_palafin(state) and not has_in_hand(state, "Palafin") and not has_in_hand(state, "Poke Pad"):
        pieces += 1
        score += 1400.0
    if missing_switch_engine(state):
        pieces += 1
        score += 1700.0
    if bool(getv(state.current, "supporterPlayed", False)) or not legal_supporter_in_options(state):
        pieces += 1
        score += 1500.0
    if secret_box_palafin_chain_available(state):
        pieces += 1
        score += 1200.0

    if pieces >= 3:
        score += 900.0
    elif pieces >= 2:
        score += 400.0
    elif pieces == 0:
        score = min(score, 3200.0)
    return score


def score_hilda_target(state: Any, name: str) -> float:
    if name == "Palafin ex":
        return -100000.0
    if name == "Basic Water Energy" and active_palafin_ex_missing_energy(state):
        return 8800.0
    if name == "Palafin" and has_ready_finizen_for_palafin(state):
        return 8400.0
    if name == "Dragonair" and count_in_play(state, "Dratini") > 0:
        return 7600.0
    if name == "Mega Dragonite ex" and count_in_play(state, "Dragonair") > 0:
        return 6800.0
    if name == "Basic Water Energy" and palafin_line_count(state) > 0 and not palafin_has_water_attached(state):
        return 5900.0
    if name == "Basic Lightning Energy" and dragonite_line_count(state) > 0:
        return 6200.0
    return generic_target_score(state, None, name)


def score_dragonair_evolution_target(state: Any, name: str) -> float:
    if name == "Palafin ex":
        return -9000.0
    if name == "Mega Dragonite ex":
        if count_in_play(state, "Dragonair") > 0 and not has_in_hand(state, "Mega Dragonite ex"):
            return 9000.0
        return 5200.0
    if name == "Palafin":
        if has_ready_finizen_for_palafin(state) and not has_in_hand(state, "Palafin"):
            return 8600.0
        if count_in_play(state, "Finizen") > 0:
            return 6200.0
        return 1600.0
    if name == "Dragonair" and count_in_play(state, "Dratini") > 0:
        return 4200.0
    return -1200.0


def score_tatsugiri_supporter_target(state: Any, name: str) -> float:
    if name == "Lillie's Determination":
        return 9200.0 if hand_count(state) <= 5 else 7000.0
    if name == "Team Rocket's Petrel":
        if has_ready_finizen_for_palafin(state) and not has_in_hand(state, "Palafin"):
            return 8800.0
        if bench_space(state) > 0 and not has_in_hand(state, "Buddy-Buddy Poffin") and poffin_targets_likely_remaining(state):
            return 8600.0
        if missing_switch_engine(state):
            return 7600.0
        return 5600.0
    if name == "Hilda":
        if has_ready_finizen_for_palafin(state) or count_in_play(state, "Dragonair") > 0:
            return 8200.0
        return 5200.0
    if name == "Crispin":
        return score_crispin_play(state) + 2600.0
    if name == "Kieran":
        return 6200.0 if zero_to_hero_combo_ready(state) or missing_switch_engine(state) else 2400.0
    if name == "Boss's Orders":
        return 7200.0 if boss_has_prize_value(state) else -800.0
    if name in SUPPORTER_NAMES:
        return 1200.0
    return -2000.0


def score_crispin_target(state: Any, cid: Optional[int], name: str) -> float:
    if name == "Basic Water Energy" and active_palafin_ex_missing_energy(state):
        return 8600.0
    if name == "Basic Lightning Energy":
        return 7000.0 if dragonite_line_count(state) > 0 else 2600.0
    if name == "Basic Water Energy":
        if not palafin_has_water_attached(state):
            return 6200.0
        if palafin_ex_attackers_have_exact_water(state) and dragonite_line_count(state) > 0:
            return 5600.0
        return 2400.0 if dragonite_line_count(state) > 0 else -1800.0
    return -200.0


def score_switch_target(state: Any, target: Any, source: str = "") -> float:
    target_name = canonical_name_from_id(card_id(target))
    current_active = active_name(state)
    if target is None:
        return 0.0
    if current_active == "Mega Dragonite ex":
        return -100000.0
    if current_active == "Palafin ex" and not palafin_ex_reset_or_recharge_ready(state, resolving_switch=True):
        return -9000.0
    if is_mega_dragonite_source(source) and current_active == "Palafin ex":
        if target_name == "Palafin" and palafin_ex_recharge_target_available(state):
            return 9800.0
        if target_name == "Tatsugiri":
            if palafin_ex_reset_pivot_ready(state, target):
                return 10100.0
            return 5200.0 if palafin_ex_reset_or_recharge_ready(state, resolving_switch=True) else -4200.0
        if target_name == "Palafin ex" and attached_energy_count_any(target) >= 1:
            return 11200.0
    if source == "Surfing Beach" and target_name == "Palafin ex":
        return 8200.0 if current_active == "Palafin" or palafin_ex_giga_locked(state) else -4000.0
    if current_active == "Palafin":
        if target_name in {"Finizen", "Palafin ex"}:
            return 7000.0
        if target_name == "Tatsugiri":
            return 5200.0
    if current_active == "Palafin ex" and target_name == "Palafin" and palafin_ex_recharge_target_available(state):
        return 9800.0
    if current_active == "Palafin ex" and target_name == "Palafin ex" and attached_energy_count_any(target) >= 1:
        return 11200.0 if palafin_ex_reset_or_recharge_ready(state, resolving_switch=True) else 6500.0
    if current_active == "Palafin ex" and target_name == "Tatsugiri":
        return 10100.0 if palafin_ex_reset_pivot_ready(state, target) else -4200.0
    if target_name == "Palafin ex" and attached_energy_count_any(target) >= 1:
        return 6500.0
    if target_name == "Mega Dragonite ex" and pokemon_energy_count(target) >= 3:
        return 6200.0
    if target_name == "Tatsugiri" and supporter_access_needed(state):
        return 3300.0
    if target_name == "Finizen" and current_active == "Palafin":
        return 5000.0
    return 200.0


def score_promote_target(state: Any, target: Any) -> float:
    target_name = canonical_name_from_id(card_id(target))
    if target is None:
        return 0.0
    if pokemon_can_attack_now(target):
        score = 8500.0
        if canonical_name_from_id(card_id(target)) in {"Palafin ex", "Mega Dragonite ex"}:
            score += 1400.0
        return score
    if not bench_has_ready_attacker(state):
        if target_name == "Finizen":
            return 13000.0
        if target_name == "Tatsugiri":
            return 3200.0
        if target_name in {"Dratini", "Dragonair", "Palafin"}:
            return 2600.0
    if target_name in {"Finizen", "Dratini", "Dragonair", "Palafin"} and count_in_play(state, target_name) <= 1:
        return -1200.0
    if target_name == "Tatsugiri":
        return 4200.0 if pokemon_has_air_balloon_attached(target) else 1600.0
    return 300.0


def score_attach_target(state: Any, target: Any, source: str = "") -> float:
    name = canonical_name_from_id(card_id(target))
    target_energy = attached_energy_count_any(target)
    attach_energy = current_attach_energy_id(state)
    if name in PALAFIN_NAMES and attach_energy is not None and attach_energy != WATER_ENERGY:
        return -100000.0
    if name == "Palafin ex" and target_energy >= 1:
        return -100000.0
    if name == "Tatsugiri":
        return -100000.0
    if source == "Crispin":
        if name in DRAGONITE_NAMES:
            return 7200.0
        if name == "Palafin ex" and target_energy == 0:
            return 6800.0 if active_palafin_ex_missing_energy(state) else 4800.0
        return -2600.0
    if source == "Hilda":
        if name == "Palafin ex" and target_energy == 0:
            return 7000.0 if active_palafin_ex_missing_energy(state) else 3600.0
        if name in DRAGONITE_NAMES:
            return 6000.0
        return -2200.0
    if name == "Palafin ex":
        return 5800.0 if target_energy == 0 else -100000.0
    if name == "Palafin":
        return 4200.0
    if name in DRAGONITE_NAMES:
        return 5200.0
    return 0.0


def score_evolution_selection(state: Any, name: str) -> float:
    if name == "Finizen":
        return 6500.0
    if name == "Dratini":
        return 4300.0
    if name == "Dragonair":
        return 5200.0
    return generic_target_score(state, None, name)


def generic_target_score(state: Any, cid: Optional[int], name: str) -> float:
    if name == "Finizen":
        return 5200.0 if palafin_line_count(state) < 2 else 1400.0
    if name == "Palafin":
        return 6200.0 if count_in_play(state, "Finizen") > 0 else 1600.0
    if name == "Palafin ex":
        return 1800.0
    if name == "Dratini":
        return 4600.0 if dragonite_line_count(state) == 0 else 1200.0
    if name == "Dragonair":
        return 4600.0 if count_in_play(state, "Dratini") > 0 else 900.0
    if name == "Mega Dragonite ex":
        return 5200.0 if count_in_play(state, "Dragonair") > 0 else 1000.0
    if name == "Tatsugiri":
        return 2200.0
    if name == "Basic Water Energy":
        return 2600.0
    if name == "Basic Lightning Energy":
        return 4400.0 if dragonite_line_count(state) > 0 else 1600.0
    if cid in (POFFIN, POKE_PAD, SECRET_BOX, SURFING_BEACH, AIR_BALLOON):
        return 1600.0
    return 0.0


def current_attach_energy_id(state: Any) -> Optional[int]:
    for key in ("energyCardId", "selectedEnergyCardId", "selectedEnergyId", "attachEnergyCardId", "attachedEnergyCardId"):
        value = getv(state.select, key)
        if value is not None:
            try:
                return int(value)
            except Exception:
                pass
    for key in ("energyCard", "selectedEnergy", "attachEnergy"):
        cid = card_id(getv(state.select, key))
        if cid is not None:
            return cid
    return None


def score_discard_selection(state: Any, cid: Optional[int]) -> float:
    name = canonical_name_from_id(cid)
    if not name:
        return 0.0
    try:
        from core.palafin_evolution_guard import score_palafin_discard_guard

        guard = score_palafin_discard_guard(state, cid)
        if guard <= -8000.0:
            return guard
    except Exception:
        pass
    if is_only_critical_copy(state, cid):
        return -9000.0
    if secret_box_recovery_discard_mode(state) and name in {"Palafin ex", "Mega Dragonite ex", "Palafin"}:
        if name == "Palafin ex":
            return 850.0
        if name == "Mega Dragonite ex":
            return 650.0
        return 250.0
    if live_next_turn_evolution_piece_in_hand(state, name):
        return -6200.0
    if name in {"Palafin ex", "Palafin", "Finizen", "Mega Dragonite ex", "Dragonair", "Dratini", "Secret Box", "Basic Lightning Energy"}:
        return -5200.0
    if name in {"Surfing Beach", "Switch", "Kieran", "Crispin", "Hilda", "Energy Retrieval", "Night Stretcher", "Sacred Ash"}:
        return -2800.0
    if name == "Buddy-Buddy Poffin":
        if bench_needs_basic_search(state):
            return -9000.0
        return 700.0 if bench_space(state) <= 0 or palafin_line_count(state) >= 2 else -3600.0
    if name == "Air Balloon":
        return 650.0 if has_switch_engine_ready(state) else -1600.0
    if name in {"Lillie's Determination", "Team Rocket's Petrel"}:
        return 500.0 if bool(getv(state.current, "supporterPlayed", False)) else -800.0
    if name == "Basic Water Energy":
        return 500.0 if extra_water_discard_safe(state) else -1400.0
    if duplicate_in_hand(state, cid):
        return 900.0
    return 0.0


def secret_box_discard_safety(state: Any) -> float:
    cards = hand_cards(state)
    if len(cards) < 4:
        return -6000.0
    scores = sorted(score_discard_selection(state, card_id(card)) for card in cards if card_id(card) != SECRET_BOX)
    if len(scores) < 3:
        return -6000.0
    three = scores[-3:]
    if any(score <= -5000.0 for score in three):
        return -6000.0
    if sum(1 for score in three if score < 0.0) >= 2:
        return -2600.0
    return min(900.0, sum(three) * 0.1)


def live_next_turn_evolution_piece_in_hand(state: Any, name: str) -> bool:
    if name == "Palafin" and count_in_play(state, "Finizen") > 0:
        return True
    if name == "Palafin ex" and count_in_play(state, "Palafin") > 0:
        return True
    if name == "Dragonair" and count_in_play(state, "Dratini") > 0:
        return True
    if name == "Mega Dragonite ex" and count_in_play(state, "Dragonair") > 0:
        return True
    return False


def secret_box_recovery_discard_mode(state: Any) -> bool:
    if context_source_name(state) != "Secret Box":
        return False
    if not (has_in_hand(state, "Sacred Ash") or has_in_hand(state, "Night Stretcher")):
        return False
    candidate_names = {"Palafin ex", "Mega Dragonite ex", "Palafin"}
    candidates = [
        card_id(card)
        for card in hand_cards(state)
        if canonical_name_from_id(card_id(card)) in candidate_names and not is_only_critical_copy(state, card_id(card))
    ]
    return len(candidates) >= 2


def score_palaking_end_penalty(state: Any, scores: Sequence[float]) -> float:
    try:
        from core.giga_impact_planner import choose_giga_impact_priority_action
        from core.palafin_evolution_guard import finizen_can_evolve_to_palafin
        from core.pokepad_dragonite_planner import pokepad_can_find_needed_piece
        from core.secret_box_palafin_guard import bench_needs_poffin

        giga = choose_giga_impact_priority_action(state, getattr(state, "options", []) or [], scores)
        if giga.should_act:
            return -10000.0 if giga.score >= 8000.0 else -7000.0
        if finizen_can_evolve_to_palafin(state, getattr(state, "options", []) or []):
            return -9000.0
        if bench_needs_poffin(state) and (has_in_hand(state, "Buddy-Buddy Poffin") or has_in_hand(state, "Team Rocket's Petrel") or has_in_hand(state, "Secret Box")):
            return -8500.0
        if pokepad_can_find_needed_piece(state) and (has_in_hand(state, "Poke Pad") or has_in_hand(state, "Team Rocket's Petrel")):
            return -7500.0
    except Exception:
        pass
    best = max((scores[idx] for idx, option in enumerate(getattr(state, "options", []) or []) if option_type(option) != 14), default=0.0)
    if best >= 4000.0:
        return -9000.0
    if useful_palaking_action_exists(state, scores):
        return -5000.0
    return 0.0


def useful_palaking_action_exists(state: Any, scores: Sequence[float]) -> bool:
    for idx, option in enumerate(getattr(state, "options", []) or []):
        if option_type(option) == 14:
            continue
        if idx < len(scores) and scores[idx] >= 1200.0:
            return True
        name = canonical_name_from_id(card_id_from_option(state, option))
        if name in {"Buddy-Buddy Poffin", "Poke Pad", "Secret Box", "Surfing Beach", "Switch", "Hilda", "Crispin"}:
            return True
        typ = option_type(option)
        if typ in (OPT_ABILITY, OPT_RETREAT) and score_palaking_option(state, option, 0.0, idx) < 0.0:
            continue
        if typ in (OPT_EVOLVE, OPT_ATTACH, OPT_ABILITY, OPT_RETREAT):
            return True
    return False


def palafin_reason_for_option(state: Any, option: Any) -> str:
    name = canonical_name_from_id(card_id_from_option(state, option))
    typ = option_type(option)
    if name == "Buddy-Buddy Poffin":
        return "Use Poffin to establish Finizen."
    if name == "Poke Pad":
        return "Use Poké Pad to find Palafin or Dragonite line pieces."
    if name == "Secret Box":
        return "Use Secret Box for Poke Pad / Air Balloon / Surfing Beach combo package."
    if name == "Palafin":
        return "Evolve Finizen into Palafin for Zero to Hero."
    if name == "Palafin ex":
        return "Zero to Hero into Palafin ex."
    if name == "Air Balloon":
        return "Attach Air Balloon only for active Palafin Zero to Hero or locked Palafin ex reset lines."
    if name == "Surfing Beach":
        return "Use Surfing Beach as the Palafin switch engine."
    if typ == OPT_RETREAT and active_name(state) == "Palafin":
        return "Retreat Palafin to Bench to trigger Zero to Hero."
    return f"Palaking score for {name or typ}."


def active_name(state: Any) -> str:
    return canonical_name_from_id(card_id(active_pokemon(state)))


def card_text(cid: Optional[int]) -> str:
    card = get_db().get_card(cid)
    if not card:
        return ""
    return " ".join([card.text] + [skill.text for skill in getattr(card, "skills", []) or []])


def palafin_line_count(state: Any) -> int:
    return sum(1 for _, _, pokemon in iter_in_play(state) if card_id(pokemon) in PALAFIN_LINE_IDS)


def dragonite_line_count(state: Any) -> int:
    return sum(1 for _, _, pokemon in iter_in_play(state) if card_id(pokemon) in DRAGONITE_LINE_IDS)


def poffin_targets_likely_remaining(state: Any) -> bool:
    if bench_space(state) <= 0:
        return False
    for cid in (FINIZEN, TATSUGIRI):
        total = deck_card_count(cid)
        if total > 0 and seen_card_count(state, cid) < total:
            return True
    if deck_card_count(FINIZEN) <= 0 and deck_card_count(TATSUGIRI) <= 0:
        return palafin_line_count(state) < 4 or not has_in_play(state, "Tatsugiri")
    return False


def seen_card_count(state: Any, cid: int) -> int:
    seen = sum(1 for card in hand_cards(state) if card_id(card) == cid)
    seen += sum(1 for card in discard_cards(state) if card_id(card) == cid)
    seen += sum(1 for _, _, pokemon in iter_in_play(state) if card_id(pokemon) == cid)
    return seen


def has_ready_finizen_for_palafin(state: Any) -> bool:
    return count_in_play(state, "Finizen") > 0 and not has_in_play(state, "Palafin ex")


def bench_has_water_switch_target(state: Any) -> bool:
    return any(canonical_name_from_id(card_id(pokemon)) in WATER_SWITCH_NAMES for pokemon in bench_pokemon(state))


def bench_has_attacker_or_pivot(state: Any) -> bool:
    return any(canonical_name_from_id(card_id(pokemon)) in {"Palafin ex", "Palafin", "Finizen", "Tatsugiri", "Mega Dragonite ex"} for pokemon in bench_pokemon(state))


def bench_has_ready_attacker(state: Any) -> bool:
    return any(
        canonical_name_from_id(card_id(pokemon)) in {"Palafin ex", "Mega Dragonite ex"} and pokemon_energy_count(pokemon) > 0
        for pokemon in bench_pokemon(state)
    )


def benched_palafin_ex_ready_to_attack(state: Any) -> bool:
    return any(
        canonical_name_from_id(card_id(pokemon)) == "Palafin ex" and attached_energy_count_any(pokemon) >= 1
        for pokemon in bench_pokemon(state)
    )


def retreat_discards_energy_without_urgency(state: Any) -> bool:
    active = active_pokemon(state)
    if active is None:
        return False
    if attached_energy_count_any(active) <= 0:
        return False
    info = get_db().get_card(card_id(active))
    retreat_cost = int(getattr(info, "retreat_cost", 0) or 0) if info else 0
    if retreat_cost <= 0:
        return False
    if pokemon_has_air_balloon_attached(active):
        return False
    return not palaking_retreat_is_urgent(state, active)


def palaking_retreat_is_urgent(state: Any, active: Any) -> bool:
    name = canonical_name_from_id(card_id(active))
    if name == "Mega Dragonite ex":
        return False
    if name == "Tatsugiri" and pokemon_has_air_balloon_attached(active) and bench_has_ready_attacker(state):
        return True
    if name == "Palafin ex" and palafin_ex_reset_or_recharge_ready(state):
        return True
    if name != "Palafin":
        return False
    max_hp = int(getv(active, "maxHp", 0) or getv(active, "maxHP", 0) or 0)
    hp = pokemon_hp(active)
    if hp and max_hp and hp <= max(40, max_hp * 0.25):
        return True
    if benched_attacker_takes_visible_ko(state):
        return True
    if not pokemon_can_attack_now(active) and bench_has_ready_attacker(state):
        return True
    return False


def benched_attacker_takes_visible_ko(state: Any) -> bool:
    opponent = active_pokemon(state, state.opponent_index)
    opponent_hp = pokemon_hp(opponent) if opponent is not None else 0
    if opponent_hp <= 0:
        return False
    return any(pokemon_can_attack_for_at_least(pokemon, opponent_hp) for pokemon in bench_pokemon(state))


def pokemon_can_attack_now(pokemon: Any) -> bool:
    return pokemon_can_attack_for_at_least(pokemon, 1)


def pokemon_can_attack_for_at_least(pokemon: Any, damage: int) -> bool:
    info = get_db().get_card(card_id(pokemon))
    if info is None:
        return False
    energy_count = attached_energy_count_any(pokemon)
    for attack in getattr(info, "attacks", ()) or ():
        if energy_count >= len(getattr(attack, "cost", ()) or ()) and int(getattr(attack, "damage", 0) or 0) >= damage:
            return True
    return False


def tatsugiri_needs_retreat_energy_for_ready_palafin(state: Any, target: Any) -> bool:
    del state, target
    return False


def target_is_active(state: Any, target: Any) -> bool:
    active = active_pokemon(state)
    if target is None or active is None:
        return False
    if target is active:
        return True
    for key in ("serial", "instanceId", "instance_id", "uid", "localId"):
        target_value = getv(target, key)
        active_value = getv(active, key)
        if target_value is not None and active_value is not None and target_value == active_value:
            return True
    return False


def pokemon_has_air_balloon_attached(pokemon: Any) -> bool:
    for field in ("tools", "toolCards", "attachedTools", "attachedCards"):
        cards = getv(pokemon, field, [])
        if not isinstance(cards, list):
            continue
        for item in cards:
            if card_id(item) == AIR_BALLOON:
                return True
    return False


def air_balloon_available_for_active_tatsugiri(state: Any) -> bool:
    if not has_in_hand(state, "Air Balloon"):
        return False
    options = getattr(state, "options", []) or []
    if not options:
        return True
    active = active_pokemon(state)
    for option in options:
        if option_type(option) != OPT_ATTACH or card_id_from_option(state, option) != AIR_BALLOON:
            continue
        if target_is_active(state, attach_target_from_option(state, option)) and canonical_name_from_id(card_id(active)) == "Tatsugiri":
            return True
    return False


def palafin_has_water_attached(state: Any) -> bool:
    for _, _, pokemon in iter_in_play(state):
        if canonical_name_from_id(card_id(pokemon)) == "Palafin ex":
            if attached_energy_count(pokemon, WATER_ENERGY) > 0 or attached_energy_count_any(pokemon) > 0:
                return True
    return False


def palafin_ex_attackers_have_exact_water(state: Any) -> bool:
    found = False
    for _, _, pokemon in iter_in_play(state):
        if canonical_name_from_id(card_id(pokemon)) != "Palafin ex":
            continue
        found = True
        if attached_energy_count(pokemon, WATER_ENERGY) != 1:
            return False
        if attached_energy_count_any(pokemon) != 1:
            return False
    return found


def attached_energy_count(pokemon: Any, energy_cid: int) -> int:
    return sum(1 for cid in attached_energy_ids_any(pokemon) if cid == energy_cid)


def attached_energy_count_any(pokemon: Any) -> int:
    explicit = None
    for key in ("energyCount", "attachedEnergyCount", "energy_count"):
        value = getv(pokemon, key)
        if value is not None:
            try:
                explicit = max(0, int(value))
            except Exception:
                pass
    ids = attached_energy_ids_any(pokemon)
    if ids:
        return len(ids)
    if explicit is not None:
        return explicit
    return pokemon_energy_count(pokemon)


def attached_energy_ids_any(pokemon: Any) -> list[int]:
    for field in ("energyCards", "energies", "attachedEnergyCards", "attachedEnergies", "attachedEnergy", "attachedCards"):
        cards = getv(pokemon, field, [])
        if not isinstance(cards, list) or not cards:
            continue
        ids = []
        for item in cards:
            cid = card_id(item)
            if cid is None:
                continue
            card = get_db().get_card(cid)
            item_type = str(getv(item, "type", "") or getv(item, "cardType", "") or "")
            item_name = str(getv(item, "name", "") or "")
            if field in ("energyCards", "energies", "attachedEnergyCards", "attachedEnergies", "attachedEnergy"):
                ids.append(cid)
            elif card and "Energy" in card.card_type:
                ids.append(cid)
            elif "Energy" in item_type or "Energy" in item_name:
                ids.append(cid)
        if ids:
            return ids
    return []


def pokemon_with_name_has_energy(state: Any, name: str) -> bool:
    return any(canonical_name_from_id(card_id(pokemon)) == name and pokemon_energy_count(pokemon) > 0 for _, _, pokemon in iter_in_play(state))


def dragonair_ability_ready(state: Any) -> bool:
    return any(
        canonical_name_from_id(card_id(pokemon)) == "Dragonair" and attached_energy_count_any(pokemon) > 0
        for _, _, pokemon in iter_in_play(state)
    )


def dragonair_ability_need_score(state: Any) -> float:
    score = 0.0
    if count_in_play(state, "Dragonair") > 0 and not has_in_hand(state, "Mega Dragonite ex") and count_in_play(state, "Mega Dragonite ex") == 0:
        score = max(score, 9000.0)
    if has_ready_finizen_for_palafin(state) and not has_in_hand(state, "Palafin"):
        score = max(score, 8600.0)
    if count_in_play(state, "Dratini") > 0 and count_in_play(state, "Dragonair") == 0:
        score = max(score, 4200.0)
    return score


def is_dragonair_source(source: str) -> bool:
    lowered = str(source or "").lower()
    return lowered == "dragonair" or "evolutionary guidance" in lowered


def is_tatsugiri_source(source: str) -> bool:
    lowered = str(source or "").lower()
    return lowered == "tatsugiri" or "attract customers" in lowered


def dragonite_energy_gap(state: Any) -> int:
    best_attached = 0
    for _, _, pokemon in iter_in_play(state):
        if canonical_name_from_id(card_id(pokemon)) in DRAGONITE_NAMES:
            best_attached = max(best_attached, pokemon_energy_count(pokemon))
    return max(0, 3 - best_attached) if dragonite_line_count(state) > 0 else 0


def dragonite_attack_plan_realistic(state: Any) -> bool:
    return count_in_play(state, "Dragonair") > 0 or count_in_play(state, "Mega Dragonite ex") > 0 or has_in_hand(state, "Mega Dragonite ex")


def supporter_access_needed(state: Any) -> bool:
    return not bool(getv(state.current, "supporterPlayed", False)) and not legal_supporter_in_options(state)


def legal_supporter_in_options(state: Any) -> bool:
    for option in getattr(state, "options", []) or []:
        name = canonical_name_from_id(card_id_from_option(state, option))
        if option_type(option) == OPT_PLAY and name in SUPPORTER_NAMES:
            return True
    return False


def secret_box_palafin_chain_available(state: Any) -> bool:
    return active_name(state) in {"Finizen", "Palafin"} and bench_has_water_switch_target(state)


def zero_to_hero_combo_ready(state: Any) -> bool:
    return active_name(state) == "Palafin" and bench_has_water_switch_target(state)


def palaking_switch_or_retreat_allowed(state: Any) -> bool:
    active = active_name(state)
    if active == "Palafin":
        return zero_to_hero_combo_ready(state)
    if active == "Palafin ex":
        return palafin_ex_reset_or_recharge_ready(state)
    if active == "Tatsugiri":
        pokemon = active_pokemon(state)
        return bool(pokemon_has_air_balloon_attached(pokemon) and bench_has_ready_attacker(state))
    return False


def palafin_ex_reset_or_recharge_ready(state: Any, resolving_switch: bool = False) -> bool:
    if not palafin_ex_giga_locked(state):
        return False
    if benched_palafin_ex_ready_to_attack(state):
        return True
    if tatsugiri_balloon_reset_pivot_available(state):
        return True
    if resolving_switch:
        return palafin_ex_recharge_target_available(state)
    return palafin_ex_recharge_loop_available(state)


def palafin_ex_giga_locked(state: Any) -> bool:
    try:
        from core.palafin_attack_state import track_giga_impact_lock

        return bool(track_giga_impact_lock(state, None).restriction_applies_now)
    except Exception:
        return False


def active_palafin_ex_can_giga_impact(state: Any) -> bool:
    active = active_pokemon(state)
    if canonical_name_from_id(card_id(active)) != "Palafin ex":
        return False
    if attached_energy_count_any(active) <= 0 or palafin_ex_giga_locked(state):
        return False
    try:
        from core.giga_impact_planner import is_giga_impact_option

        return any(is_giga_impact_option(option) for option in getattr(state, "options", []) or [])
    except Exception:
        return False


def active_palafin_ex_needs_visible_recharge(state: Any) -> bool:
    active = active_pokemon(state)
    if canonical_name_from_id(card_id(active)) != "Palafin ex":
        return False
    if active_palafin_ex_can_giga_impact(state):
        return False
    if attached_energy_count_any(active) <= 0:
        return False
    return bench_has_ready_attacker(state) or tatsugiri_balloon_reset_pivot_available(state) or palafin_ex_recharge_target_available(state)


def palafin_ex_recharge_loop_available(state: Any) -> bool:
    if not palafin_ex_recharge_target_available(state):
        return False
    return available_switch_resource_count(state) >= 1


def tatsugiri_balloon_reset_pivot_available(state: Any) -> bool:
    active = active_pokemon(state)
    if canonical_name_from_id(card_id(active)) != "Palafin ex":
        return False
    if attached_energy_count_any(active) <= 0:
        return False
    for pokemon in bench_pokemon(state):
        if canonical_name_from_id(card_id(pokemon)) == "Tatsugiri" and pokemon_has_air_balloon_attached(pokemon):
            return True
    for option in getattr(state, "options", []) or []:
        if option_type(option) != OPT_ATTACH or card_id_from_option(state, option) != AIR_BALLOON:
            continue
        target = attach_target_from_option(state, option)
        if canonical_name_from_id(card_id(target)) == "Tatsugiri":
            return True
    return False


def palafin_ex_recharge_target_available(state: Any) -> bool:
    if active_name(state) != "Palafin ex" or not palafin_ex_giga_locked(state):
        return False
    if palafin_ex_overloaded_in_hand(state) and not palafin_ex_likely_left_in_deck(state):
        return False
    return any(
        canonical_name_from_id(card_id(pokemon)) == "Palafin" and palafin_can_become_fresh_attacker(state, pokemon)
        for pokemon in bench_pokemon(state)
    )


def palafin_can_become_fresh_attacker(state: Any, pokemon: Any) -> bool:
    if attached_energy_count(pokemon, WATER_ENERGY) >= 1:
        return True
    return not bool(getv(state.current, "energyAttached", False)) and has_in_hand(state, "Basic Water Energy")


def palafin_ex_likely_left_in_deck(state: Any) -> bool:
    total = deck_card_count(PALAFIN_EX)
    if total <= 0:
        return True
    return seen_card_count(state, PALAFIN_EX) < total


def available_switch_resource_count(state: Any) -> int:
    count = 1 if own_stadium_name(state) == "Surfing Beach" else 0
    for option in getattr(state, "options", []) or []:
        typ = option_type(option)
        name = canonical_name_from_id(card_id_from_option(state, option))
        if typ == OPT_PLAY and name in {"Surfing Beach", "Switch", "Kieran"}:
            count += 1
        elif typ == OPT_ATTACH and name == "Air Balloon":
            target_name = canonical_name_from_id(card_id(attach_target_from_option(state, option)))
            if target_name in {"Palafin", "Palafin ex", "Tatsugiri"}:
                count += 1
        elif typ == OPT_ABILITY and name == "Mega Dragonite ex":
            count += 1
        elif typ == OPT_RETREAT and active_name(state) != "Mega Dragonite ex":
            active = active_pokemon(state)
            if active is not None and (attached_energy_count_any(active) == 0 or pokemon_has_air_balloon_attached(active)):
                count += 1
    return count


def missing_switch_engine(state: Any) -> bool:
    if own_stadium_name(state) == "Surfing Beach":
        return False
    return not any(has_in_hand(state, name) for name in ("Surfing Beach", "Switch", "Air Balloon", "Kieran"))


def has_switch_engine_ready(state: Any) -> bool:
    return own_stadium_name(state) == "Surfing Beach" or any(has_in_hand(state, name) for name in ("Switch", "Air Balloon", "Kieran"))


def own_stadium_name(state: Any) -> str:
    stadium = getv(getv(state, "current"), "stadium", []) or getv(state.current, "stadium", [])
    if isinstance(stadium, list) and stadium:
        return canonical_name_from_id(card_id(stadium[0]))
    return ""


def boss_has_prize_value(state: Any) -> bool:
    opponent_prizes = prize_count(state, state.opponent_index)
    return opponent_prizes <= 3


def active_palafin_ex_missing_energy(state: Any) -> bool:
    active = active_pokemon(state)
    return canonical_name_from_id(card_id(active)) == "Palafin ex" and attached_energy_count_any(active) == 0


def low_bench_with_both_engine_roots(state: Any) -> bool:
    if bench_space(state) <= 0:
        return False
    if len(bench_pokemon(state)) >= 3:
        return False
    return palafin_line_count(state) > 0 and dragonite_line_count(state) > 0


def bench_needs_basic_search(state: Any) -> bool:
    if bench_space(state) <= 0:
        return False
    if len(bench_pokemon(state)) <= 2:
        return True
    if palafin_line_count(state) < 2:
        return True
    if count_in_play(state, "Tatsugiri") == 0:
        return True
    return False


def kieran_plus_damage_creates_visible_ko(state: Any) -> bool:
    active = active_pokemon(state)
    if canonical_name_from_id(card_id(active)) != "Palafin ex" or attached_energy_count_any(active) <= 0:
        return False
    opponent = active_pokemon(state, state.opponent_index)
    hp = pokemon_hp(opponent)
    return 250 < hp <= 280


def is_mega_dragonite_source(source: str) -> bool:
    lowered = str(source or "").lower()
    return lowered == "mega dragonite ex" or "sky transport" in lowered


def palafin_ex_reset_pivot_ready(state: Any, target: Any) -> bool:
    if canonical_name_from_id(card_id(target)) != "Tatsugiri":
        return False
    if pokemon_has_air_balloon_attached(target):
        return True
    if attached_energy_count_any(target) > 0:
        return True
    return any(
        canonical_name_from_id(card_id(pokemon)) == "Palafin ex" and attached_energy_count_any(pokemon) >= 1
        for pokemon in bench_pokemon(state)
        if pokemon is not target
    )


def palafin_ex_overloaded_in_hand(state: Any) -> bool:
    return sum(1 for hand_card in hand_cards(state) if card_id(hand_card) == PALAFIN_EX) > 1


def lillie_play_option_legal(state: Any) -> bool:
    return any(option_type(option) == OPT_PLAY and card_id_from_option(state, option) == LILLIE for option in getattr(state, "options", []) or [])


def all_piece_lost(discard_names: Sequence[str], name: str) -> bool:
    needed = {"Finizen": 4, "Dratini": 2}.get(name, 99)
    return sum(1 for item in discard_names if item == name) >= needed


def duplicate_in_hand(state: Any, cid: Optional[int]) -> bool:
    if cid is None:
        return False
    return sum(1 for card in hand_cards(state) if card_id(card) == cid) >= 2


def is_only_critical_copy(state: Any, cid: Optional[int]) -> bool:
    if cid is None:
        return False
    name = canonical_name_from_id(cid)
    if name not in {"Palafin", "Palafin ex", "Dragonair", "Mega Dragonite ex", "Basic Lightning Energy"}:
        return False
    deck_total = deck_card_count(cid)
    if deck_total > 1:
        return False
    seen = sum(1 for card in hand_cards(state) if card_id(card) == cid)
    seen += sum(1 for card in discard_cards(state) if card_id(card) == cid)
    for _, _, pokemon in iter_in_play(state):
        if card_id(pokemon) == cid:
            seen += 1
    return seen <= 1


def deck_card_count(cid: int) -> int:
    try:
        return sum(1 for deck_cid in load_deck_ids() if deck_cid == cid)
    except Exception:
        return 0


def extra_water_discard_safe(state: Any) -> bool:
    if has_in_hand(state, "Energy Retrieval"):
        return True
    water_in_hand = sum(1 for card in hand_cards(state) if card_id(card) == WATER_ENERGY)
    return water_in_hand >= 2 and palafin_has_water_attached(state)
