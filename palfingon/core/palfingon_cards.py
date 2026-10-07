from __future__ import annotations

from typing import Any, Optional

from card_db import get_db
from state_eval import (active_pokemon, attach_target_from_option, attached_card_ids,
                        bench_pokemon, bench_space, card_id, card_id_from_option,
                        deck_count, discard_cards, getv, hand_cards, hand_count,
                        iter_in_play, pokemon_hp, prize_count)

VANGUARD = 51
JUDGE = 1213
BATTLE_CAGE = 1264
NIGHT_STRETCHER = 1097


def refresh_in_hand(state: Any) -> bool:
    return not getv(state.current, "supporterPlayed", False) and any(
        card_id(c) in {1227, JUDGE} for c in hand_cards(state))


def score_judge(state: Any) -> float:
    from core.lillie_guard import hand_is_stalled, useful_action_before_lillie

    if getv(state.current, "supporterPlayed", False):
        return -12000.0
    if useful_action_before_lillie(state).should_wait:
        return -6000.0
    own = hand_count(state)
    # Judge returns the remaining hand before drawing, so count those cards too.
    if deck_count(state) + max(0, own - 1) <= 4:
        return -12000.0
    opponent = hand_count(state, state.opponent_index)
    stranded = sum(card_id(c) == 107 for c in hand_cards(state))
    if own <= 3 or (stranded >= 2 and len(bench_pokemon(state)) <= 1):
        return 6200.0
    if hand_is_stalled(state):
        return 5200.0
    if opponent >= 7 and own <= 5:
        return 5000.0
    return -1600.0


def visible_counter_threat(state: Any) -> bool:
    for _, _, pokemon in iter_in_play(state, state.opponent_index):
        info = get_db().get_card(card_id(pokemon))
        if info is None:
            continue
        effects = [info.text] + [a.text for a in info.attacks] + [s.text for s in info.skills]
        if any("damage counter" in str(text).lower() and any(
            verb in str(text).lower() for verb in ("put", "place", "move")) for text in effects):
            return True
    return False


def score_battle_cage(state: Any) -> float:
    from core.turn_plan import locked_palafin_reset_ready, own_stadium_name, zero_to_hero_route

    stadium = own_stadium_name(state)
    if stadium == "Battle Cage":
        return -10000.0
    if stadium == "Surfing Beach" and (
        zero_to_hero_route(state).can_start or locked_palafin_reset_ready(state)):
        return -7000.0
    if bench_pokemon(state) and visible_counter_threat(state):
        return 3800.0
    return -1400.0


def vanguard_recoil(pokemon: Any) -> int:
    info = get_db().get_card(VANGUARD)
    maximum = int(getv(pokemon, "maxHp", info.hp if info else 150) or 150)
    return max(0, maximum - pokemon_hp(pokemon))


def score_vanguard_attack(state: Any, option: Any) -> float:
    from policy import estimate_attack_damage

    attack = get_db().get_attack(getv(option, "attackId"))
    if attack is None or attack.name != "Vanguard Punch":
        return 0.0
    active = active_pokemon(state)
    target = active_pokemon(state, state.opponent_index)
    damage = estimate_attack_damage(state, attack, active, target)
    ko = target is not None and 0 < pokemon_hp(target) <= damage
    target_info = get_db().get_card(card_id(target))
    wins = ko and target_info is not None and prize_count(state) <= target_info.prize_value
    if vanguard_recoil(active) >= pokemon_hp(active) and not wins:
        return -1000000.0
    return 5000.0 if ko else 1600.0


def score_vanguard_piece(state: Any, target: Any = None) -> float:
    from core.priority_tables import has_in_hand

    finizen = [p for _, _, p in iter_in_play(state) if card_id(p) == 105]
    if not finizen:
        return -3000.0
    opponent = active_pokemon(state, state.opponent_index)
    candidate = target if target is not None else active_pokemon(state)
    # One-prize attacker is useful when it takes a clean small-target KO now.
    if candidate in finizen and candidate is active_pokemon(state):
        water = 3 in attached_card_ids(candidate, "energyCards") or 3 in attached_card_ids(candidate, "energies")
        ready = water or (has_in_hand(state, 3) and not getv(state.current, "energyAttached", False))
        if ready and opponent is not None and 0 < pokemon_hp(opponent) <= 130:
            return 8200.0
    return 1800.0 if any(card_id(p) == 107 for _, _, p in iter_in_play(state)) else 500.0


def stretcher_target_score(state: Any, cid: Optional[int]) -> float:
    from core.palafin_planner import score_energy_attachment
    from core.priority_tables import count_in_play, has_in_hand

    if cid is None:
        return -2000.0
    if cid == 107:
        return 2000.0 if refresh_in_hand(state) else -6000.0
    if cid in {3, 4}:
        if has_in_hand(state, cid):
            return -700.0
        productive = any(score_energy_attachment(state, cid, p) > 0 for _, _, p in iter_in_play(state))
        return 4800.0 if productive and not getv(state.current, "energyAttached", False) else 300.0
    if cid in {105, 902, 122}:
        return 4400.0 if bench_space(state) > 0 and count_in_play(state, cid) == 0 else 600.0
    prerequisites = {106: 105, VANGUARD: 105, 903: 902, 904: 903}
    if cid in prerequisites:
        return 5000.0 if count_in_play(state, prerequisites[cid]) and not has_in_hand(state, cid) else 100.0
    return 0.0


def score_stretcher(state: Any) -> float:
    scores = [stretcher_target_score(state, card_id(c)) for c in discard_cards(state)]
    best = max(scores, default=-1200.0)
    return best if best >= 2000.0 else -1200.0
