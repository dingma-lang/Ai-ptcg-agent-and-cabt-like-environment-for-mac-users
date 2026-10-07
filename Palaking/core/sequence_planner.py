from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List

from card_db import get_db
from state_eval import OPT_ATTACK, OPT_PLAY, active_pokemon, bench_pokemon, card_id, card_id_from_option, count_card_in_discard, getv, option_type, pokemon_hp, prize_count
from core.danger_evaluator import our_pokemon_knocked_out_last_turn
from core.mega_gengar_planner import score_mega_gengar_option
from core.poffin_planner import should_use_poffin_now
from core.pokepad_planner import should_use_pokepad_now
from core.priority_tables import CARD_IDS, canonical_name_from_id, has_in_hand, has_in_play
from core.toxtricity_engine_planner import score_toxtricity_option


@dataclass(frozen=True)
class SequencePlan:
    name: str
    score: float
    steps: List[str] = field(default_factory=list)
    reason: str = ""


def build_sequence_plans(state: Any) -> List[SequencePlan]:
    plans: List[SequencePlan] = []
    poffin = should_use_poffin_now(state, state.options)
    pokepad = should_use_pokepad_now(state, state.options)
    if has_in_hand(state, "Secret Box") and not has_in_hand(state, "Buddy-Buddy Poffin") and opening_board_is_weak(state):
        plans.append(
            SequencePlan(
                "Opening Secret Box into Poffin package",
                3600.0,
                ["play Secret Box", "take Poffin/Air Balloon/Lillie/Battle Cage", "play Poffin", "bench Deino + Gastly/Toxel"],
                "Human log used Secret Box into Poffin to establish Deino + Gastly.",
            )
        )
    if poffin.should_act:
        plans.append(
            SequencePlan(
                "Opening Poffin line",
                poffin.score,
                ["play Buddy-Buddy Poffin", "bench Deino", "bench Gastly or Toxel"],
                "Expert log used Poffin immediately to establish Deino + Gastly.",
            )
        )
    if pokepad.should_act:
        plans.append(
            SequencePlan(
                "Poké Pad setup line",
                pokepad.score,
                ["play Poké Pad", "take missing non-Rule Box setup Pokemon"],
                "Poké Pad finds non-Rule Box setup pieces before weak actions.",
            )
        )
    if our_pokemon_knocked_out_last_turn(state):
        plans.append(
            SequencePlan(
                "Post-KO Fezandipiti line",
                5000.0,
                ["use Flip the Script", "recover engine pieces", "rebuild attacker", "then Supporter if needed"],
                "Expert log used Fezandipiti immediately after KO to recover.",
            )
        )
    if has_in_play(state, "Haunter") or has_in_play(state, "Mega Gengar ex"):
        plans.append(
            SequencePlan(
                "Mega Gengar attack line",
                4200.0,
                ["evolve Haunter", "attach/accelerate Darkness", "pivot", "Void Gale", "move Energy to future attacker"],
                "Mega Gengar ex is a main attacker and prize-exchange engine.",
            )
        )
    if any(score_toxtricity_option(state, option, 0.0) >= 1800.0 for option in state.options):
        plans.append(
            SequencePlan(
                "Toxtricity Energy engine line",
                4300.0,
                ["use Sinister Surge", "attach Darkness to best Benched Darkness attacker", "retreat/pivot if needed"],
                "Expert log used Toxtricity to power Mega Gengar and later Hydreigon.",
            )
        )
    if obsidian_multi_prize_available(state):
        plans.append(
            SequencePlan(
                "Hydreigon Obsidian closer",
                6000.0 + estimated_obsidian_prizes(state) * 900.0,
                ["use Obsidian", "KO Active if possible", "choose highest-value Bench KO targets", "take multi-prize turn"],
                "Expert log won by taking multi-prize Obsidian turns.",
            )
        )
    if late_rebuild_needed(state):
        plans.append(
            SequencePlan(
                "Late rebuild line",
                3800.0,
                [
                    "use Fezandipiti draw if post-KO",
                    "use Energy Recycler for 3+ key Energy",
                    "use Night Stretcher for exact resource",
                    "Rare Candy rebuild Hydreigon",
                    "use Toxtricity plus manual attachment",
                    "pivot and attack",
                ],
                "Expert log recovered Energy and rebuilt Hydreigon before the final Obsidian.",
            )
        )
    return plans


def opening_board_is_weak(state: Any) -> bool:
    turn = int(getv(state.current, "turn", 0) or 0)
    bench = bench_pokemon(state)
    return turn <= 4 or len(bench) <= 2 or not (has_in_play(state, "Deino") and has_in_play(state, "Gastly"))


def obsidian_multi_prize_available(state: Any) -> bool:
    for option in getattr(state, "options", []) or []:
        if option_type(option) != OPT_ATTACK:
            continue
        attack = get_db().get_attack(getv(option, "attackId"))
        if attack and "obsidian" in str(attack.name or "").lower() and estimated_obsidian_prizes(state) >= 2:
            return True
    return False


def estimated_obsidian_prizes(state: Any) -> int:
    prizes = 0
    active = active_pokemon(state, state.opponent_index)
    if active is not None and pokemon_hp(active) <= 130:
        prizes += prize_value(active)
    bench_kos = sorted((prize_value(pokemon) for pokemon in bench_pokemon(state, state.opponent_index) if pokemon_hp(pokemon) <= 130), reverse=True)
    return prizes + sum(bench_kos[:2])


def prize_value(pokemon: Any) -> int:
    card = get_db().get_card(card_id(pokemon))
    if not card:
        return 1
    return max(1, int(getattr(card, "prize_value", 1) or 1))


def late_rebuild_needed(state: Any) -> bool:
    option_names = {
        canonical_name_from_id(card_id_from_option(state, option))
        for option in getattr(state, "options", []) or []
        if option_type(option) == OPT_PLAY
    }
    recovery_legal = bool(option_names & {"Energy Recycler", "Night Stretcher", "Sacred Ash", "Dawn", "Rare Candy"})
    if not recovery_legal:
        return False
    if our_pokemon_knocked_out_last_turn(state):
        return True
    if prize_count(state) <= 2 or prize_count(state, state.opponent_index) <= 2:
        return discarded_key_energy_count(state) >= 2 or exact_rebuild_resource_in_discard(state)
    return discarded_key_energy_count(state) >= 3 and (has_in_play(state, "Hydreigon ex") or has_in_hand(state, "Rare Candy"))


def discarded_key_energy_count(state: Any) -> int:
    return sum(count_card_in_discard(state, cid) for cid in (CARD_IDS["Basic Darkness Energy"], CARD_IDS["Basic Metal Energy"], CARD_IDS["Basic Psychic Energy"]))


def exact_rebuild_resource_in_discard(state: Any) -> bool:
    return any(
        count_card_in_discard(state, cid) > 0
        for cid in (
            CARD_IDS["Basic Psychic Energy"],
            CARD_IDS["Basic Metal Energy"],
            CARD_IDS["Hydreigon ex"],
            CARD_IDS["Mega Gengar ex"],
            CARD_IDS["Toxtricity"],
        )
    )
