from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

from card_db import get_db
from state_eval import active_pokemon, bench_pokemon, card_id, discard_cards, pokemon_damage, pokemon_energy_count, pokemon_hp
from core.damage_math_planner import calculate_zoroark_damage
from core.target_board import DARMANITAN, DARUMAKA, RESHIRAM, ZEKROM, ZOROARK_EX, opponent_bench, pokemon_name, ready_zoroarks


@dataclass(frozen=True)
class CopyChoice:
    source_pokemon: Any = None
    copied_attack_name: str = ""
    expected_damage: int = 0
    base_damage: int = 0
    modifiers: List[str] = field(default_factory=list)
    drawback: str = ""
    ko_value: float = 0.0
    prize_value: int = 1
    next_turn_cost: float = 0.0
    score: float = 0.0
    reason: str = ""


def choose_best_benched_n_attack_to_copy(state: Any, opponent_model: Any = None) -> CopyChoice:
    del opponent_model
    best = CopyChoice(score=-99999.0, reason="No Benched N's copy source.")
    opponent = active_pokemon(state, getattr(state, "opponent_index", 1))
    target_hp = pokemon_hp(opponent)
    for source in bench_pokemon(state):
        name = pokemon_name(source)
        choices = choices_for_source(state, source, name, target_hp)
        for choice in choices:
            if choice.score > best.score:
                best = choice
    return best


def choices_for_source(state: Any, source: Any, name: str, target_hp: int) -> List[CopyChoice]:
    if name == ZEKROM:
        return [zekrom_rampaging_thunder_choice(state, source, target_hp)]
    if name == RESHIRAM:
        return [reshiram_powerful_rage_choice(state, source, target_hp), reshiram_virtuous_flame_choice(state, source, target_hp)]
    if name == DARMANITAN:
        return [darmanitan_back_draft_choice(state, source, target_hp), darmanitan_flamebody_choice(state, source, target_hp)]
    if name == DARUMAKA:
        return [low_value_choice(state, source, "Flare", 50, target_hp)]
    return []


def zekrom_rampaging_thunder_choice(state: Any, source: Any, target_hp: int) -> CopyChoice:
    damage = 250
    math = calculate_zoroark_damage(state, CopyChoice(expected_damage=damage), {}, None)
    ko = math.is_ko
    prize = math.prize_value
    backup_ready = len(ready_zoroarks(state)) >= 2
    score = 5200.0
    if ko:
        score += 8500.0 + prize * 900.0
    if prize >= 2 and ko:
        score += 900.0
    if backup_ready:
        score += 900.0
    else:
        score -= 450.0
    if target_hp and damage < target_hp:
        score -= 500.0
    return CopyChoice(
        source_pokemon=source,
        copied_attack_name="Rampaging Thunder",
        expected_damage=damage,
        base_damage=damage,
        drawback="attacking Zoroark may be unable to attack next turn",
        ko_value=9000.0 if ko else 0.0,
        prize_value=prize,
        next_turn_cost=700.0 if not backup_ready else 150.0,
        score=score,
        reason="Copy N's Zekrom because Rampaging Thunder is the main 250-damage line." + (" It takes a KO." if ko else ""),
    )


def reshiram_powerful_rage_choice(state: Any, source: Any, target_hp: int) -> CopyChoice:
    active = active_pokemon(state)
    counters = pokemon_damage(active) // 10 if active is not None else 0
    damage = counters * 20
    math = calculate_zoroark_damage(state, CopyChoice(expected_damage=damage), {}, None)
    score = 1600.0 + counters * 240.0
    if math.is_ko:
        score += 8500.0 + math.prize_value * 900.0
    elif damage < 120:
        score -= 1100.0
    if damage >= 250:
        score += 900.0
    return CopyChoice(
        source_pokemon=source,
        copied_attack_name="Powerful Rage",
        expected_damage=damage,
        base_damage=damage,
        drawback="scales with damage counters on attacking Zoroark",
        ko_value=8500.0 if math.is_ko else 0.0,
        prize_value=math.prize_value,
        score=score,
        reason=f"Copy N's Reshiram Powerful Rage for {damage} based on damage counters on Zoroark.",
    )


def reshiram_virtuous_flame_choice(state: Any, source: Any, target_hp: int) -> CopyChoice:
    damage = 170
    math = calculate_zoroark_damage(state, CopyChoice(expected_damage=damage), {}, None)
    score = 3200.0
    if math.is_ko:
        score += 7600.0 + math.prize_value * 800.0
    elif target_hp and damage < target_hp:
        score -= 250.0
    return CopyChoice(
        source_pokemon=source,
        copied_attack_name="Virtuous Flame",
        expected_damage=damage,
        base_damage=damage,
        drawback="none",
        ko_value=7600.0 if math.is_ko else 0.0,
        prize_value=math.prize_value,
        score=score,
        reason="Copy N's Reshiram Virtuous Flame for stable 170 damage.",
    )


def darmanitan_back_draft_choice(state: Any, source: Any, target_hp: int) -> CopyChoice:
    energy = opponent_basic_energy_discard_count(state)
    damage = 30 * energy
    math = calculate_zoroark_damage(state, CopyChoice(expected_damage=damage), {}, None)
    ko = math.is_ko
    score = 2100.0 + energy * 260.0
    if ko:
        score += 8500.0 + math.prize_value * 900.0
    if damage >= 250:
        score += 1500.0
    if target_hp and damage < max(120, target_hp * 0.45):
        score -= 900.0
    return CopyChoice(
        source_pokemon=source,
        copied_attack_name="Back Draft",
        expected_damage=damage,
        base_damage=damage,
        drawback="none",
        ko_value=9000.0 if ko else 0.0,
        prize_value=math.prize_value,
        next_turn_cost=0.0,
        score=score,
        reason=f"Copy N's Darmanitan Back Draft for {damage} from opponent Basic Energy in discard.",
    )


def darmanitan_flamebody_choice(state: Any, source: Any, target_hp: int) -> CopyChoice:
    bench_value = flamebody_bench_value(state)
    math = calculate_zoroark_damage(state, CopyChoice(expected_damage=90), {}, None)
    ko = math.is_ko
    score = 500.0 + bench_value
    if ko:
        score += 3000.0 + math.prize_value * 700.0
    if bench_value >= 6000.0:
        score += 8500.0
    else:
        score -= 6000.0
    return CopyChoice(
        source_pokemon=source,
        copied_attack_name="Flamebody Cannon",
        expected_damage=90,
        base_damage=90,
        drawback="discard all Energy from attacking Zoroark",
        ko_value=8500.0 if bench_value >= 6000.0 else 0.0,
        prize_value=math.prize_value,
        next_turn_cost=3000.0,
        score=score,
        reason="Copy Flamebody Cannon only because Bench damage has prize value." if bench_value >= 6000.0 else "Avoid Flamebody Cannon because it discards all Zoroark Energy without enough Bench value.",
    )


def low_value_choice(state: Any, source: Any, attack_name: str, damage: int, target_hp: int) -> CopyChoice:
    math = calculate_zoroark_damage(state, CopyChoice(expected_damage=damage), {}, None)
    score = 300.0 + damage
    if math.is_ko:
        score += 6000.0 + math.prize_value * 600.0
    elif target_hp and damage < target_hp:
        score -= 800.0
    return CopyChoice(
        source_pokemon=source,
        copied_attack_name=attack_name,
        expected_damage=damage,
        base_damage=damage,
        drawback="low damage",
        ko_value=6000.0 if math.is_ko else 0.0,
        prize_value=math.prize_value,
        score=score,
        reason=f"Low-value copy of {attack_name}; use only if it is the best legal attack.",
    )


def score_copy_selection_zoroark(state: Any, cid: Optional[int]) -> float:
    name = canonical_name_for_copy_id(cid)
    choice = choose_best_benched_n_attack_to_copy(state)
    if not name:
        return 0.0
    chosen_source = pokemon_name(choice.source_pokemon) if choice.source_pokemon is not None else ""
    if name == chosen_source:
        return choice.score + 1200.0
    if name == ZEKROM:
        return 5200.0
    if name == RESHIRAM:
        return 4800.0
    if name == DARMANITAN:
        return max(1500.0, darmanitan_back_draft_choice(state, None, pokemon_hp(active_pokemon(state, getattr(state, "opponent_index", 1)))).score)
    if name == DARUMAKA:
        return 400.0
    return -2500.0


def opponent_basic_energy_discard_count(state: Any) -> int:
    basic_ids = set(range(1, 10))
    return sum(1 for card in discard_cards(state, getattr(state, "opponent_index", 1)) if card_id(card) in basic_ids)


def flamebody_bench_value(state: Any) -> float:
    value = 0.0
    for pokemon in opponent_bench(state):
        hp = pokemon_hp(pokemon)
        info = get_db().get_card(card_id(pokemon))
        if hp and hp <= 90:
            value += 2500.0 + (info.prize_value if info else 1) * 1000.0
        elif hp and hp <= 180:
            value += 850.0
    return value


def canonical_name_for_copy_id(cid: Optional[int]) -> str:
    if cid is None:
        return ""
    try:
        from core.priority_tables import canonical_name_from_id

        return canonical_name_from_id(cid)
    except Exception:
        return ""


def zoroark_has_copy_source(state: Any) -> bool:
    return any(pokemon_name(pokemon) in {ZEKROM, RESHIRAM, DARMANITAN, DARUMAKA} for pokemon in bench_pokemon(state))
