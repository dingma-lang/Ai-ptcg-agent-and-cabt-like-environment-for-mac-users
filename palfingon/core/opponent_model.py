from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List

from card_db import get_db
from state_eval import active_pokemon, bench_pokemon, card_id, discard_cards, getv, hand_count, iter_in_play, pokemon_energy_count, pokemon_hp, prize_count
from core.priority_tables import canonical_name_from_id


@dataclass(frozen=True)
class OpponentThreat:
    max_visible_damage: int = 0
    has_rulebox_attacker: bool = False
    hand_size: int = 0
    can_take_active_ko: bool = False
    can_take_final_prizes: bool = False
    can_boss_benched_ex_for_game: bool = False
    visible_rulebox_count: int = 0
    visible_one_prize_count: int = 0
    likely_ex_heavy: bool = False
    likely_one_prize: bool = False
    revealed_card_names: List[str] = field(default_factory=list)
    reason: str = "No visible next-turn threat."


def infer_opponent_next_turn_threat(state: Any) -> OpponentThreat:
    """Estimate only from public opponent board/logs.

    We assume the opponent may make one normal attachment next turn, but we do
    not peek at hidden hand/deck/prize contents.
    """
    active = active_pokemon(state)
    active_hp = pokemon_hp(active)
    active_prize_value = prize_value(active)
    max_damage = 0
    has_rulebox = False
    visible_rulebox = 0
    visible_one_prize = 0

    for pokemon in [active_pokemon(state, state.opponent_index)] + bench_pokemon(state, state.opponent_index):
        if pokemon is None:
            continue
        cid = card_id(pokemon)
        card = get_db().get_card(cid)
        if not card:
            continue
        rulebox = bool(card.ex or card.prize_value > 1)
        has_rulebox = has_rulebox or rulebox
        if rulebox:
            visible_rulebox += 1
        else:
            visible_one_prize += 1
        energy_available_next_turn = pokemon_energy_count(pokemon) + 1
        for attack in card.attacks:
            if energy_available_next_turn >= len(attack.cost or []):
                max_damage = max(max_damage, estimate_visible_attack_damage(state, attack, state.opponent_index))

    can_ko = bool(active_hp and max_damage >= active_hp)
    opp_prizes_left = prize_count(state, state.opponent_index)
    final_prizes = bool(can_ko and opp_prizes_left <= max(1, active_prize_value))
    boss_game = can_boss_benched_ex_for_game(state)
    names = revealed_opponent_card_names(state)
    reason = "Opponent can threaten Active KO next turn." if can_ko else "Opponent visible damage does not KO Active."
    if final_prizes:
        reason = "Opponent can take final prizes with visible pressure."
    elif boss_game:
        reason = "Opponent can plausibly Boss a Benched ex for game."
    elif has_rulebox and hand_count(state, state.opponent_index) >= 5:
        reason = "Opponent has public attacker pressure and a large hand."

    return OpponentThreat(
        max_visible_damage=max_damage,
        has_rulebox_attacker=has_rulebox,
        hand_size=hand_count(state, state.opponent_index),
        can_take_active_ko=can_ko,
        can_take_final_prizes=final_prizes,
        can_boss_benched_ex_for_game=boss_game,
        visible_rulebox_count=visible_rulebox,
        visible_one_prize_count=visible_one_prize,
        likely_ex_heavy=visible_rulebox >= max(1, visible_one_prize),
        likely_one_prize=visible_one_prize > visible_rulebox and visible_rulebox <= 1,
        revealed_card_names=names,
        reason=reason,
    )


def revealed_opponent_card_names(state: Any) -> List[str]:
    names: List[str] = []
    for pokemon in [active_pokemon(state, state.opponent_index)] + bench_pokemon(state, state.opponent_index):
        cid = card_id(pokemon)
        name = canonical_name_from_id(cid)
        if name:
            names.append(name)
    logs = getv(state.obs, "logs", []) or []
    if isinstance(logs, list):
        for log in logs[-20:]:
            if not isinstance(log, dict):
                continue
            cid = getv(log, "cardId")
            if cid is None:
                cid = getv(log, "id")
            try:
                name = canonical_name_from_id(int(cid)) if cid is not None else ""
            except Exception:
                name = ""
            if name:
                names.append(name)
    return names


def prize_value(pokemon: Any) -> int:
    card = get_db().get_card(card_id(pokemon))
    if not card:
        return 1
    return max(1, int(getattr(card, "prize_value", 1) or 1))


def estimate_visible_attack_damage(state: Any, attack: Any, player_index: int) -> int:
    damage = int(getattr(attack, "damage", 0) or 0)
    text = str(getattr(attack, "text", "") or "").lower()
    if "more damage for each energy card in your discard pile" in text:
        damage += 20 * energy_count_in_discard(state, player_index)
    return damage


def energy_count_in_discard(state: Any, player_index: int) -> int:
    count = 0
    db = get_db()
    for card in discard_cards(state, player_index):
        info = db.get_card(card_id(card))
        if info and "Energy" in info.card_type:
            count += 1
    return count


def can_boss_benched_ex_for_game(state: Any) -> bool:
    opp_prizes_left = prize_count(state, state.opponent_index)
    if opp_prizes_left > 2:
        return False
    for area, _, pokemon in iter_in_play(state):
        del area
        if pokemon is active_pokemon(state):
            continue
        card = get_db().get_card(card_id(pokemon))
        if card and max(1, int(getattr(card, "prize_value", 1) or 1)) >= opp_prizes_left:
            return True
    return False
