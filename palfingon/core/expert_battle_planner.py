"""Bounded, public-state tactics reviewed from the September expert logs."""
from __future__ import annotations

from collections import Counter
from typing import Any, Optional

from card_db import get_db
from state_eval import (
    CTX_MAIN, OPT_ABILITY, OPT_ATTACH, OPT_ATTACK, OPT_PLAY, OPT_RETREAT,
    active_pokemon, attach_target_from_option, bench_pokemon, card_id,
    card_id_from_option, getv, hand_cards, iter_in_play, option_type,
    pokemon_hp, prize_count,
)
from core.turn_plan import attached_energy_ids, has_air_balloon, target_is_active


def free_manual_retreat(state: Any, pokemon: Any = None) -> bool:
    if getv(state.current, "retreated", False):
        return False
    pokemon = pokemon if pokemon is not None else active_pokemon(state)
    info = get_db().get_card(card_id(pokemon))
    if not info or card_id(pokemon) == 904:
        return False
    return max(0, info.retreat_cost - (2 if has_air_balloon(pokemon) else 0)) == 0


def opening_tatsugiri_route(state: Any) -> bool:
    if card_id(active_pokemon(state)) not in (105, 902) or getv(state.current, "retreated", False):
        return False
    if not any(card_id(p) == 122 for p in bench_pokemon(state)):
        return False
    # Do not leave an evolution/attack route just to speculate on six unseen cards.
    if any(card_id(p) in (106, 107, 904) for _, _, p in iter_in_play(state)):
        return False
    if card_id(active_pokemon(state)) == 902:
        return sum(card_id(p) in (902, 903, 904) for _, _, p in iter_in_play(state)) == 1
    for card in hand_cards(state):
        info = get_db().get_card(card_id(card))
        if info and (info.card_type == "Supporter" or info.card_id == 106):
            return False
    return True


def bench_balloon_pivot(state: Any, target: Any) -> bool:
    if target is None or target_is_active(state, target) or card_id(target) not in (105, 106):
        return False
    if getv(state.current, "retreated", False):
        return False
    active = active_pokemon(state)
    if card_id(active) != 106:
        return False
    # A legal non-retreat move gets the Active out; the pivot saves the one retreat.
    return direct_switch_index(state, target, include_retreat=False) is not None


def direct_switch_index(state: Any, target: Any, include_retreat: bool = True) -> Optional[int]:
    active = active_pokemon(state)
    active_info = get_db().get_card(card_id(active))
    target_info = get_db().get_card(card_id(target))
    choices = []
    for idx, option in enumerate(state.options):
        typ, cid = option_type(option), card_id_from_option(state, option)
        if typ == OPT_ABILITY and cid == 904:
            choices.append((0, idx))
        elif typ in (OPT_ABILITY, OPT_PLAY) and cid == 1262:
            if active_info and target_info and active_info.energy_type == target_info.energy_type == "W":
                choices.append((1, idx))
        elif typ == OPT_RETREAT and include_retreat and free_manual_retreat(state):
            choices.append((2, idx))
        elif typ == OPT_PLAY and cid == 1123:
            choices.append((3, idx))
    return min(choices)[1] if choices else None


def attack_energy_ready(pokemon: Any, attack: Any, extra_energy: Optional[int] = None) -> bool:
    ids = attached_energy_ids(pokemon) + ([extra_energy] if extra_energy is not None else [])
    types = Counter(get_db().get_card(cid).energy_type for cid in ids if get_db().get_card(cid))
    costs = Counter(attack.cost)
    generic = costs.pop("C", 0)
    for energy, needed in costs.items():
        if types[energy] < needed:
            return False
        types[energy] -= needed
    return sum(types.values()) >= generic


def switch_progress_score(state: Any, target: Any) -> float:
    """Destination value shared by move initiation and required target prompts."""
    from core.palafin_attack_state import track_giga_impact_lock
    from core.turn_plan import palafin_ex_deck_available

    if target is None or target_is_active(state, target):
        return 0.0
    active = active_pokemon(state)
    opponent = active_pokemon(state, state.opponent_index)
    current_damage = ko_damage(state, active, opponent)
    target_damage = ko_damage(state, target, opponent)
    hp = pokemon_hp(opponent)
    if 0 < hp <= current_damage:
        return 0.0
    if 0 < hp <= target_damage:
        return 14000.0
    if current_damage == 0 and target_damage >= 100:
        return 12000.0
    active_id = card_id(active)
    locked = track_giga_impact_lock(state).restriction_applies_now
    if current_damage > 0 or active_id == 106:
        return 0.0
    if card_id(target) == 122:
        if locked and free_manual_retreat(state, target):
            return 10500.0
        if active_id not in (106, 107, 122):
            return 7800.0 if has_air_balloon(target) else 5500.0
    if card_id(target) == 106 and palafin_ex_deck_available(state):
        if active_id not in (106, 107) or locked:
            return 8500.0 if free_manual_retreat(state, target) else 6500.0
    return 0.0


def progress_move_score(state: Any, source: str) -> float:
    if source == "Retreat" and not free_manual_retreat(state):
        return 0.0
    active_info = get_db().get_card(card_id(active_pokemon(state)))
    best = 0.0
    for target in bench_pokemon(state):
        info = get_db().get_card(card_id(target))
        if source == "Surfing Beach" and not (
            active_info and info and active_info.energy_type == info.energy_type == "W"
        ):
            continue
        best = max(best, switch_progress_score(state, target))
    return best


def best_progress_move(state: Any) -> tuple[Optional[int], float]:
    best_index, best_score = None, 0.0
    for target in bench_pokemon(state):
        idx = direct_switch_index(state, target)
        score = switch_progress_score(state, target)
        if idx is not None and score > best_score:
            best_index, best_score = idx, score
    return best_index, best_score


def ability_damage_blocked(attacker: Any, defender: Any, attack: Any = None) -> bool:
    a, d = get_db().get_card(card_id(attacker)), get_db().get_card(card_id(defender))
    if not a or not d or not a.skills or getv(defender, "abilityDisabled", False):
        return False
    text = str(getattr(attack, "text", "") or "").lower().replace("\u2019", "'")
    if "any effects on your opponent" in text and "isn't affected" in text:
        return False
    return any("prevent all damage from attacks" in s.text.lower() and "have an ability" in s.text.lower()
               for s in d.skills)


def ko_damage(state: Any, attacker: Any, defender: Any, extra_energy: Optional[int] = None) -> int:
    cache = getattr(state, "decision_score_cache", None)
    key = ("ko_damage", id(attacker), id(defender), extra_energy)
    if cache is None:
        return _ko_damage(state, attacker, defender, extra_energy)
    if key not in cache:
        cache[key] = _ko_damage(state, attacker, defender, extra_energy)
    return cache[key]


def _ko_damage(state: Any, attacker: Any, defender: Any, extra_energy: Optional[int]) -> int:
    from policy import estimate_attack_damage
    from core.palafin_attack_state import track_giga_impact_lock

    info = get_db().get_card(card_id(attacker))
    if not info or info.card_id not in (51, 107, 904):
        return 0
    if target_is_active(state, attacker) and (
        getv(attacker, "cannotAttack", False) or track_giga_impact_lock(state).restriction_applies_now
    ):
        return 0
    best = 0
    for attack in info.attacks:
        if (target_is_active(state, attacker) and extra_energy is None
                and getv(state.select, "context") == CTX_MAIN
                and not any(option_type(o) == OPT_ATTACK
                            and getattr(get_db().get_attack(getv(o, "attackId")), "name", "") == attack.name
                            for o in state.options)):
            continue
        if not attack_energy_ready(attacker, attack, extra_energy):
            continue
        if info.card_id == 51 and pokemon_hp(attacker) <= info.hp - pokemon_hp(attacker):
            continue
        best = max(best, estimate_attack_damage(state, attack, attacker, defender))
    return best


def final_prize_target(state: Any, attacker: Any, target: Any, extra_energy: Optional[int] = None) -> bool:
    info = get_db().get_card(card_id(target))
    return bool(info and 0 < prize_count(state) <= info.prize_value
                and 0 < pokemon_hp(target) <= ko_damage(state, attacker, target, extra_energy))


def gust_target_score(state: Any, target: Any) -> float:
    info = get_db().get_card(card_id(target))
    if not info:
        return 0.0
    best = -2000.0
    for _, _, attacker in iter_in_play(state):
        damage = ko_damage(state, attacker, target)
        if target_is_active(state, attacker):
            reachable = True
        else:
            reachable = direct_switch_index(state, attacker) is not None
        if damage <= 0:
            continue
        if damage >= pokemon_hp(target) > 0:
            score = 9000.0 + info.prize_value * 1000.0
            if prize_count(state) <= info.prize_value:
                score += 20000.0
            # A forced target prompt may omit main-phase moves. Prefer immediate KOs.
            best = max(best, score if reachable else damage)
        else:
            best = max(best, damage)
    return best


def finishing_action(state: Any) -> tuple[Optional[int], str]:
    active = active_pokemon(state)
    opponent = active_pokemon(state, state.opponent_index)
    from policy import estimate_attack_damage

    for idx, option in enumerate(state.options):
        if option_type(option) == OPT_ATTACK:
            attack = get_db().get_attack(getv(option, "attackId"))
            if attack and final_prize_target(state, active, opponent):
                if estimate_attack_damage(state, attack, active, opponent) >= pokemon_hp(opponent):
                    return idx, "Take the final prizes with the legal attack."
    boss = next((i for i, o in enumerate(state.options)
                 if option_type(o) == OPT_PLAY and card_id_from_option(state, o) == 1182), None)
    for _, _, attacker in iter_in_play(state):
        own_active = target_is_active(state, attacker)
        move = None if own_active else direct_switch_index(state, attacker)
        if not own_active and move is None:
            continue
        if final_prize_target(state, attacker, opponent) and not own_active:
            return move, "Bring the powered finisher Active for the final-prize KO."
        if boss is not None and any(final_prize_target(state, attacker, p)
                                    for p in bench_pokemon(state, state.opponent_index)):
            return boss, "Gust a target the ready attacker can KO for the final prizes."
        # One legal attachment, then a visible move. No invented future draw/search.
        if card_id(attacker) == 904:
            for idx, option in enumerate(state.options):
                if option_type(option) != OPT_ATTACH or attach_target_from_option(state, option) is not attacker:
                    continue
                energy = card_id_from_option(state, option)
                ids = attached_energy_ids(attacker)
                if energy not in (3, 4) or len(ids) >= 3 or ids.count(energy) >= (1 if energy == 3 else 2):
                    continue
                targets = [opponent] + (bench_pokemon(state, state.opponent_index) if boss is not None else [])
                if any(final_prize_target(state, attacker, p, energy) for p in targets):
                    return idx, "Complete Water/Lightning/Lightning for a visible finishing KO."
    return None, ""


def redundant_attacker_discard(state: Any, cid: Optional[int]) -> bool:
    # Recovery to hand is not recovery to deck. Never assume Night Stretcher restores Zero to Hero.
    board = [p for _, _, p in iter_in_play(state)]
    if cid == 107:
        return sum(card_id(p) == 107 and attached_energy_ids(p) == [3] for p in board) >= 2
    if cid == 904:
        return any(card_id(p) == 904 for p in board) and not any(card_id(p) == 903 for p in board)
    return False
