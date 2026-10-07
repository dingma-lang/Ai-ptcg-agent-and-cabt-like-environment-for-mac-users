from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from action_classifier import ActionCategory, classify_legal_option
from card_db import get_db
from state_eval import (
    CTX_ATTACH_TO,
    CTX_DAMAGE,
    CTX_DAMAGE_COUNTER,
    CTX_DAMAGE_COUNTER_ANY,
    CTX_EFFECT_TARGET,
    OPT_ATTACK,
    OPT_PLAY,
    active_pokemon,
    bench_pokemon,
    bench_space,
    card_id,
    card_id_from_option,
    count_card_in_discard,
    getv,
    hand_count,
    option_type,
    pokemon_from_card_option,
    pokemon_hp,
)
from core.danger_evaluator import our_pokemon_knocked_out_last_turn
from core.mega_gengar_planner import score_mega_gengar_option
from core.poffin_planner import should_use_poffin_now
from core.priority_tables import CARD_IDS, canonical_name_from_id, context_source_name, has_in_hand, has_in_play
from core.round_plan import LATE, build_round_plan
from core.toxtricity_engine_planner import score_toxtricity_option
from core.trajectory_lessons import (
    LESSON_FEZ_AFTER_KO,
    LESSON_HYDREIGON_OBSIDIAN_MULTI_PRIZE,
    LESSON_MEGA_GENGAR_ATTACKER,
    LESSON_OPENING_POFFIN,
    LESSON_RECOVER_ENERGY_LATE,
    LESSON_SECRET_BOX_TO_POFFIN,
    LESSON_TOXTRICITY_ENGINE,
)


@dataclass(frozen=True)
class ExpertScore:
    bonus: float = 0.0
    lesson_id: str = ""
    reason: str = ""
    sequence: str = ""


EXPERT_OVERRIDE_ORDER = [
    "immediate win",
    LESSON_HYDREIGON_OBSIDIAN_MULTI_PRIZE["id"],
    LESSON_FEZ_AFTER_KO["id"],
    LESSON_OPENING_POFFIN["id"],
    LESSON_SECRET_BOX_TO_POFFIN["id"],
    LESSON_MEGA_GENGAR_ATTACKER["id"],
    LESSON_TOXTRICITY_ENGINE["id"],
    LESSON_RECOVER_ENERGY_LATE["id"],
    "normal policy",
]


def score_expert_option(state: Any, option: Any, base_score: float = 0.0) -> ExpertScore:
    candidates = [
        score_obsidian_lesson(state, option, base_score),
        score_fez_after_ko(state, option),
        score_opening_poffin(state, option),
        score_secret_box_package(state, option),
        score_mega_gengar_lesson(state, option, base_score),
        score_toxtricity_lesson(state, option, base_score),
        score_late_recovery_lesson(state, option),
        score_expert_effect_selection(state, option),
    ]
    non_zero = [candidate for candidate in candidates if candidate.bonus != 0.0]
    if not non_zero:
        return ExpertScore()
    return max(non_zero, key=lambda item: item.bonus)


def remember_expert_match(state: Any, idx: int, score: ExpertScore) -> None:
    if score.bonus <= 0 or not score.lesson_id:
        return
    try:
        matches = list(getattr(state, "expert_matches", []))
        matches.append(
            {
                "option_index": idx,
                "lesson_id": score.lesson_id,
                "bonus": float(score.bonus),
                "reason": score.reason,
                "sequence": score.sequence,
            }
        )
        setattr(state, "expert_matches", matches)
    except Exception:
        pass


def score_secret_box_package(state: Any, option: Any) -> ExpertScore:
    name = canonical_name_from_id(card_id_from_option(state, option))
    if name != "Secret Box" or option_type(option) != OPT_PLAY:
        return ExpertScore()
    try:
        from core.discard_cost_guard import score_discard_cost_play_safety

        if score_discard_cost_play_safety(state, "Secret Box", 3) <= -4500.0:
            return ExpertScore(-5200.0, "SECRET_BOX_UNSAFE_DISCARD", "Do not use Secret Box when the discard cost would spend useful setup cards.", "")
    except Exception:
        pass
    try:
        from core.setup_recovery_planner import emergency_setup_needed

        emergency = emergency_setup_needed(state)
    except Exception:
        emergency = False
    if not is_opening_weak_board(state) or (has_in_hand(state, "Buddy-Buddy Poffin") and not emergency):
        return ExpertScore()
    return ExpertScore(
        7200.0 if emergency else LESSON_SECRET_BOX_TO_POFFIN["priority"],
        LESSON_SECRET_BOX_TO_POFFIN["id"],
        LESSON_SECRET_BOX_TO_POFFIN["reason"],
        "Opening Secret Box into Poffin package",
    )


def score_opening_poffin(state: Any, option: Any) -> ExpertScore:
    decision = should_use_poffin_now(state, state.options)
    if not decision.should_act:
        return ExpertScore()
    name = canonical_name_from_id(card_id_from_option(state, option))
    if name == "Buddy-Buddy Poffin" and option_type(option) == OPT_PLAY:
        return ExpertScore(
            max(float(LESSON_OPENING_POFFIN["priority"]), decision.score),
            LESSON_OPENING_POFFIN["id"],
            LESSON_OPENING_POFFIN["reason"],
            "Opening Poffin line",
        )
    if option_type(option) == OPT_ATTACK and base_is_weak_attack(state, option):
        return ExpertScore(-2500.0, "LESSON_OPENING_POFFIN_PENALTY", "Override: Poffin beats weak attack and random Supporter.", "")
    return ExpertScore()


def score_fez_after_ko(state: Any, option: Any) -> ExpertScore:
    if not our_pokemon_knocked_out_last_turn(state):
        return ExpertScore()
    action = classify_legal_option(state, option, 0)
    if action.category == ActionCategory.USE_ABILITY and (action.card_id == CARD_IDS["Fezandipiti ex"] or action.card_name == "Fezandipiti ex"):
        return ExpertScore(
            LESSON_FEZ_AFTER_KO["priority"],
            LESSON_FEZ_AFTER_KO["id"],
            LESSON_FEZ_AFTER_KO["reason"],
            "Post-KO Fezandipiti line",
        )
    name = canonical_name_from_id(card_id_from_option(state, option))
    attack = get_db().get_attack(getv(option, "attackId"))
    attack_name = str(getattr(attack, "name", "") or "")
    if action.card_id == CARD_IDS["Fezandipiti ex"] or name == "Fezandipiti ex":
        return ExpertScore(
            5400.0,
            LESSON_FEZ_AFTER_KO["id"],
            "After a KO, bench or search Fezandipiti ex so Flip the Script becomes available.",
            "Post-KO Fezandipiti line",
        )
    needs_fez = bench_space(state) > 0 and not has_in_play(state, "Fezandipiti ex") and not has_in_hand(state, "Fezandipiti ex")
    if needs_fez and name in {"Dawn", "Ultra Ball"}:
        return ExpertScore(
            5000.0,
            LESSON_FEZ_AFTER_KO["id"],
            f"Use {name} after a KO to find Fezandipiti ex.",
            "Post-KO Fezandipiti line",
        )
    if needs_fez and canonical_name_from_id(card_id(active_pokemon(state))) == "Toxel" and "call for family" in attack_name.lower():
        return ExpertScore(
            4800.0,
            LESSON_FEZ_AFTER_KO["id"],
            "Use Toxel Call for Family after a KO to put Fezandipiti ex onto the Bench.",
            "Post-KO Fezandipiti line",
        )
    return ExpertScore()


def score_mega_gengar_lesson(state: Any, option: Any, base_score: float) -> ExpertScore:
    bonus = score_mega_gengar_option(state, option, base_score)
    if bonus < 1800.0:
        return ExpertScore()
    return ExpertScore(
        max(float(LESSON_MEGA_GENGAR_ATTACKER["priority"]), bonus),
        LESSON_MEGA_GENGAR_ATTACKER["id"],
        LESSON_MEGA_GENGAR_ATTACKER["reason"],
        "Mega Gengar attack line",
    )


def score_toxtricity_lesson(state: Any, option: Any, base_score: float) -> ExpertScore:
    bonus = score_toxtricity_option(state, option, base_score)
    if bonus < 1800.0:
        return ExpertScore()
    return ExpertScore(
        max(float(LESSON_TOXTRICITY_ENGINE["priority"]), bonus),
        LESSON_TOXTRICITY_ENGINE["id"],
        LESSON_TOXTRICITY_ENGINE["reason"],
        "Toxtricity Energy engine line",
    )


def score_obsidian_lesson(state: Any, option: Any, base_score: float) -> ExpertScore:
    if option_type(option) != OPT_ATTACK:
        return ExpertScore()
    attack = get_db().get_attack(getv(option, "attackId"))
    if not attack or "obsidian" not in str(attack.name or "").lower():
        return ExpertScore()
    prizes = estimated_obsidian_prizes(state)
    if prizes < 2:
        return ExpertScore()
    return ExpertScore(
        float(LESSON_HYDREIGON_OBSIDIAN_MULTI_PRIZE["priority"]) + prizes * 900.0,
        LESSON_HYDREIGON_OBSIDIAN_MULTI_PRIZE["id"],
        LESSON_HYDREIGON_OBSIDIAN_MULTI_PRIZE["reason"],
        "Hydreigon Obsidian closer",
    )


def score_late_recovery_lesson(state: Any, option: Any) -> ExpertScore:
    name = canonical_name_from_id(card_id_from_option(state, option))
    if name not in {"Energy Recycler", "Night Stretcher", "Sacred Ash", "Dawn"}:
        return ExpertScore()
    plan = build_round_plan(state, None, None)
    late_or_rebuild = plan.game_stage == LATE or our_pokemon_knocked_out_last_turn(state)
    if not late_or_rebuild:
        return ExpertScore()
    if name == "Energy Recycler" and discarded_energy_count(state) >= 4:
        return ExpertScore(3800.0, LESSON_RECOVER_ENERGY_LATE["id"], LESSON_RECOVER_ENERGY_LATE["reason"], "Late rebuild line")
    if name == "Night Stretcher" and key_exact_resource_in_discard(state):
        return ExpertScore(3600.0, LESSON_RECOVER_ENERGY_LATE["id"], LESSON_RECOVER_ENERGY_LATE["reason"], "Late rebuild line")
    if name == "Sacred Ash" and engine_or_attacker_piece_in_discard(state):
        return ExpertScore(3300.0, LESSON_RECOVER_ENERGY_LATE["id"], "Expert log recovered lost Pokemon engine pieces before rebuilding.", "Late rebuild line")
    if name == "Dawn" and hand_count(state) <= 4:
        return ExpertScore(1200.0, LESSON_RECOVER_ENERGY_LATE["id"], "Dawn can help rebuild after board loss.", "Late rebuild line")
    return ExpertScore()


def score_expert_effect_selection(state: Any, option: Any) -> ExpertScore:
    source = context_source_name(state)
    cid = card_id_from_option(state, option)
    name = canonical_name_from_id(cid)

    if source == "Secret Box":
        try:
            from core.setup_recovery_planner import poffin_trainer_target_score

            poffin_score = poffin_trainer_target_score(state)
        except Exception:
            poffin_score = 0.0
        package_scores = {
            "Buddy-Buddy Poffin": 9200.0 if poffin_score >= 5000.0 else 0.0,
            "Air Balloon": 3600.0,
            "Lillie's Determination": 3400.0,
            "Battle Cage": 3000.0,
        }
        if name in package_scores and package_scores[name] > 0.0:
            return ExpertScore(
                package_scores[name],
                LESSON_SECRET_BOX_TO_POFFIN["id"],
                "Human log used Secret Box into Poffin to establish Deino + Gastly.",
                "Opening Secret Box into Poffin package",
            )

    if source == "Team Rocket's Petrel":
        if name == "Buddy-Buddy Poffin":
            try:
                from core.setup_recovery_planner import poffin_trainer_target_score

                poffin_score = poffin_trainer_target_score(state)
            except Exception:
                poffin_score = 0.0
            if poffin_score >= 5000.0:
                return ExpertScore(9200.0, LESSON_OPENING_POFFIN["id"], "Petrel should find Buddy-Buddy Poffin when Bench is weak.", "Emergency Poffin line")
            return ExpertScore()
        if name in {"Poke Pad", "Ultra Ball", "Secret Box"}:
            return ExpertScore(5200.0, LESSON_OPENING_POFFIN["id"], "If Poffin is unavailable, take a setup search Trainer.", "Emergency setup line")

    if source == "Dawn" and name in {"Fezandipiti ex", "Deino", "Gastly", "Toxel", "Toxtricity", "Hydreigon ex", "Mega Gengar ex"}:
        try:
            from core.setup_recovery_planner import whole_team_setup_score

            return ExpertScore(whole_team_setup_score(state, cid), LESSON_FEZ_AFTER_KO["id"], "Dawn should assemble the whole setup team.", "Whole-team Dawn line")
        except Exception:
            pass

    if source == "Toxtricity":
        pokemon = pokemon_from_card_option(state, option)
        target_name = canonical_name_from_id(card_id(pokemon))
        if target_name in {"Toxel", "Toxtricity", "Pecharunt ex", "Fezandipiti ex"}:
            return ExpertScore(-6500.0, LESSON_TOXTRICITY_ENGINE["id"], "Do not spend Sinister Surge Energy on support Pokémon.", "Toxtricity Energy engine line")
        if target_name == "Mega Gengar ex":
            return ExpertScore(4300.0, LESSON_TOXTRICITY_ENGINE["id"], LESSON_TOXTRICITY_ENGINE["reason"], "Toxtricity Energy engine line")
        if target_name == "Hydreigon ex":
            return ExpertScore(3900.0, LESSON_TOXTRICITY_ENGINE["id"], LESSON_TOXTRICITY_ENGINE["reason"], "Toxtricity Energy engine line")
        if target_name in {"Haunter", "Gastly", "Deino", "Zweilous"}:
            return ExpertScore(2600.0, LESSON_TOXTRICITY_ENGINE["id"], LESSON_TOXTRICITY_ENGINE["reason"], "Toxtricity Energy engine line")

    if source == "Mega Gengar ex" and state.context == CTX_ATTACH_TO:
        pokemon = pokemon_from_card_option(state, option)
        target_name = canonical_name_from_id(card_id(pokemon))
        if target_name == "Hydreigon ex":
            return ExpertScore(3200.0, LESSON_MEGA_GENGAR_ATTACKER["id"], "Void Gale should move Energy to the next Hydreigon attacker.", "Mega Gengar attack line")
        if target_name == "Zweilous":
            return ExpertScore(3000.0, LESSON_MEGA_GENGAR_ATTACKER["id"], "Void Gale should seed the evolved Hydreigon line before the next attack.", "Mega Gengar attack line")
        if target_name == "Deino":
            return ExpertScore(2600.0, LESSON_MEGA_GENGAR_ATTACKER["id"], "Void Gale should start the next Deino/Hydreigon attacker.", "Mega Gengar attack line")

    if state.context in (CTX_DAMAGE, CTX_DAMAGE_COUNTER, CTX_DAMAGE_COUNTER_ANY, CTX_EFFECT_TARGET):
        pokemon = pokemon_from_card_option(state, option)
        player_index = int(getv(option, "playerIndex", state.opponent_index) or state.opponent_index)
        if player_index == state.opponent_index and pokemon_hp(pokemon) <= 130:
            return ExpertScore(2600.0 + prize_value_for_pokemon(pokemon) * 400.0, LESSON_HYDREIGON_OBSIDIAN_MULTI_PRIZE["id"], "Choose Bench targets that can be KO'd or set up final prizes.", "Hydreigon Obsidian closer")

    if source == "Night Stretcher" and name in {"Basic Psychic Energy", "Basic Metal Energy"}:
        return ExpertScore(3300.0, LESSON_RECOVER_ENERGY_LATE["id"], "Night Stretcher can recover exact Hydreigon Energy.", "Late rebuild line")

    return ExpertScore()


def is_opening_weak_board(state: Any) -> bool:
    turn = int(getv(state.current, "turn", 0) or 0)
    return turn <= 4 or len(bench_pokemon(state)) <= 2 or not (has_in_play(state, "Deino") and has_in_play(state, "Gastly"))


def base_is_weak_attack(state: Any, option: Any) -> bool:
    attack = get_db().get_attack(getv(option, "attackId"))
    return not attack or int(getattr(attack, "damage", 0) or 0) < 120


def estimated_obsidian_prizes(state: Any) -> int:
    prizes = 0
    opponent_active = active_pokemon(state, state.opponent_index)
    if opponent_active is not None and pokemon_hp(opponent_active) <= 130:
        prizes += prize_value_for_pokemon(opponent_active)
    bench_kos = sorted(
        [prize_value_for_pokemon(pokemon) for pokemon in bench_pokemon(state, state.opponent_index) if pokemon_hp(pokemon) <= 130],
        reverse=True,
    )
    prizes += sum(bench_kos[:2])
    return prizes


def prize_value_for_pokemon(pokemon: Any) -> int:
    card = get_db().get_card(card_id(pokemon))
    if not card:
        return 1
    return max(1, int(getattr(card, "prize_value", 1) or 1))


def discarded_energy_count(state: Any) -> int:
    return sum(1 for cid in (CARD_IDS["Basic Darkness Energy"], CARD_IDS["Basic Metal Energy"], CARD_IDS["Basic Psychic Energy"]) for _ in range(count_card_in_discard(state, cid)))


def key_exact_resource_in_discard(state: Any) -> bool:
    return any(count_card_in_discard(state, cid) > 0 for cid in (CARD_IDS["Basic Psychic Energy"], CARD_IDS["Basic Metal Energy"], CARD_IDS["Hydreigon ex"], CARD_IDS["Mega Gengar ex"]))


def engine_or_attacker_piece_in_discard(state: Any) -> bool:
    return any(count_card_in_discard(state, cid) > 0 for cid in (CARD_IDS["Toxel"], CARD_IDS["Toxtricity"], CARD_IDS["Deino"], CARD_IDS["Zweilous"], CARD_IDS["Hydreigon ex"], CARD_IDS["Gastly"], CARD_IDS["Haunter"], CARD_IDS["Mega Gengar ex"]))
