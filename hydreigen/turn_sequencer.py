from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Sequence, Tuple

from action_classifier import ActionCategory, ClassifiedAction, classify_legal_option
from card_db import get_db
from deck_profile import list_value, load_profile
from core.strategy_scope import use_hydreigon_gengar_strategy
from state_eval import (
    active_pokemon,
    bench_pokemon,
    card_id,
    deck_count,
    discard_cards,
    getv,
    hand_count,
    int_or,
    iter_in_play,
    player_has_condition,
    pokemon_energy_count,
    pokemon_hp,
    pokemon_max_hp,
    prize_count,
)


WINNING_SCORE_THRESHOLD = 30000.0
KO_SCORE_THRESHOLD = 10000.0


MANDATORY_CATEGORIES = {
    ActionCategory.SETUP_CHOOSE_ACTIVE,
    ActionCategory.SETUP_CHOOSE_BENCH,
    ActionCategory.PROMOTE_AFTER_KO,
    ActionCategory.PRIZE_SELECTION,
    ActionCategory.DISCARD_COST,
    ActionCategory.COUNT_SELECTION,
    ActionCategory.SPECIAL_CONDITION_CHECK,
    ActionCategory.MULLIGAN_DECISION,
    ActionCategory.GO_FIRST_SECOND_DECISION,
}


@dataclass(frozen=True)
class SequencingContext:
    turn: int
    action_count: int
    our_prizes_left: int
    opponent_prizes_left: int
    our_deck_count: int
    opponent_hand_count: int
    early_game: bool
    late_game: bool
    deckout_risk: bool
    active_stuck: bool
    active_damaged: bool
    opponent_near_win: bool
    deino_in_play: int


def apply_turn_sequence(state: Any, raw_scores: Sequence[float]) -> Tuple[List[float], List[ClassifiedAction]]:
    options = state.options
    classified = [classify_legal_option(state, option, idx) for idx, option in enumerate(options)]
    ctx = sequencing_context(state)
    scores = []
    for raw_score, action in zip(raw_scores, classified):
        scores.append(raw_score + sequencing_bonus(state, action, raw_score, ctx))
    return scores, classified


def sequencing_context(state: Any) -> SequencingContext:
    active = active_pokemon(state)
    active_id = card_id(active)
    active_info = get_db().get_card(active_id)
    active_energy = pokemon_energy_count(active)
    can_attack = False
    if active_info:
        can_attack = any(active_energy >= len(attack.cost) for attack in active_info.attacks)
    condition_stuck = player_has_condition(state, "asleep") or player_has_condition(state, "paralyzed")
    damaged = bool(active and pokemon_hp(active) <= max(40, pokemon_max_hp(active) * 0.25))
    turn = int_or(getv(state.current, "turn", 0), 0)
    our_prizes = prize_count(state)
    opponent_prizes = prize_count(state, state.opponent_index)
    weak_board = len(bench_pokemon(state)) <= 1
    return SequencingContext(
        turn=turn,
        action_count=int_or(getv(state.current, "turnActionCount", 0), 0),
        our_prizes_left=our_prizes,
        opponent_prizes_left=opponent_prizes,
        our_deck_count=deck_count(state),
        opponent_hand_count=hand_count(state, state.opponent_index),
        early_game=weak_board or turn <= 4 or our_prizes >= 6,
        late_game=False if weak_board else our_prizes <= 2 or opponent_prizes <= 2,
        deckout_risk=deck_count(state) <= 3,
        active_stuck=bool(active and (condition_stuck or not can_attack)),
        active_damaged=damaged,
        opponent_near_win=False if weak_board else opponent_prizes <= 2,
        deino_in_play=count_in_play(state, 227) if use_hydreigon_gengar_strategy(state) else 0,
    )


def sequencing_bonus(state: Any, action: ClassifiedAction, raw_score: float, ctx: SequencingContext) -> float:
    category = action.category
    bonus = 0.0
    deck_specific = use_hydreigon_gengar_strategy(state)

    # 1. Mandatory game prompts.
    if is_mandatory_window(state, action):
        bonus += 5000.0
        if category == ActionCategory.PRIZE_SELECTION:
            bonus += 8000.0
        if category == ActionCategory.PROMOTE_AFTER_KO:
            bonus += 5000.0
        return bonus

    # 2. Immediate win / prize-taking check.
    if raw_score >= WINNING_SCORE_THRESHOLD:
        return bonus + 60000.0
    if category == ActionCategory.PRIZE_SELECTION:
        return bonus + 50000.0

    # 3. Avoid immediate loss.
    if ctx.deckout_risk and action_draws_or_searches(action):
        bonus -= 6000.0
    if ctx.active_stuck and category in (ActionCategory.SWITCH_ACTIVE, ActionCategory.RETREAT):
        bonus += 700.0
    if ctx.active_damaged and category in (ActionCategory.SWITCH_ACTIVE, ActionCategory.RETREAT):
        bonus += 250.0
    if ctx.opponent_near_win:
        if category == ActionCategory.ATTACK and raw_score >= KO_SCORE_THRESHOLD:
            bonus += 900.0
        if category in (ActionCategory.PLAY_SUPPORTER, ActionCategory.PLAY_ITEM, ActionCategory.DRAW_OR_SEARCH) and is_disruption_action(action):
            bonus += 550.0

    # 4. Prize-map check.
    if category == ActionCategory.ATTACK and raw_score >= KO_SCORE_THRESHOLD:
        bonus += 1200.0
        if ctx.our_prizes_left <= 2:
            bonus += 700.0
    if category in (ActionCategory.PLAY_BASIC_TO_BENCH, ActionCategory.SETUP_CHOOSE_BENCH):
        if action.card_id in list_value("avoid_benching"):
            bonus -= 750.0
        if action.card_id in high_risk_liabilities():
            bonus -= 350.0

    # 5. Setup engine.
    if ctx.early_game:
        if category in (ActionCategory.PLAY_BASIC_TO_BENCH, ActionCategory.SETUP_CHOOSE_BENCH):
            if deck_specific and action.card_id == 227:
                bonus += 750.0 if ctx.deino_in_play < 2 else 125.0
            elif action.card_id in list_value("setup_pokemon"):
                bonus += 350.0
        if category == ActionCategory.DRAW_OR_SEARCH:
            if action.card_id in (1086, 1121, 1152, 1227):
                bonus += 450.0
            if action.card_id in list_value("setup_priority"):
                bonus += 350.0
        if category == ActionCategory.RARE_CANDY_EVOLVE:
            bonus += 350.0
        if category == ActionCategory.PLAY_SUPPORTER and action.card_id in (1227, 1231, 1219):
            bonus += 250.0
    if deck_specific:
        try:
            from core.setup_recovery_planner import emergency_setup_needed

            if emergency_setup_needed(state):
                if category == ActionCategory.DRAW_OR_SEARCH and action.card_id in (1086, 1092, 1121, 1152):
                    bonus += 3200.0
                if category == ActionCategory.PLAY_SUPPORTER and action.card_id in (1227, 1231, 1219):
                    bonus += 3000.0
                if category == ActionCategory.ATTACK:
                    bonus -= 2200.0
        except Exception:
            pass

    # 6. Energy plan.
    if category == ActionCategory.ATTACH_ENERGY:
        if action.card_id in list_value("protected_energy_ids"):
            bonus -= 80.0
        if action.target_id in list_value("primary_attackers"):
            bonus += 450.0
        elif action.target_id in list_value("secondary_attackers"):
            bonus += 250.0
    if category in (ActionCategory.PLAY_SUPPORTER, ActionCategory.DRAW_OR_SEARCH) and action.card_name.lower() == "crispin":
        bonus += 300.0

    # 7. Board development.
    if category in (ActionCategory.EVOLVE, ActionCategory.RARE_CANDY_EVOLVE):
        if action.card_id in list_value("primary_attackers") or (deck_specific and "hydreigon" in action.card_name.lower()):
            bonus += 800.0
        elif action.card_id in list_value("secondary_attackers"):
            bonus += 275.0 if not ctx.early_game else 50.0
    if category == ActionCategory.PLAY_BASIC_TO_BENCH and action.card_id in list_value("support_pokemon"):
        try:
            from core.setup_recovery_planner import weak_board_ignores_prize_liability

            if not weak_board_ignores_prize_liability(state):
                bonus -= 600.0 if ctx.early_game else 250.0
        except Exception:
            bonus -= 600.0 if ctx.early_game else 250.0

    # 8. Disruption.
    if is_disruption_action(action):
        if ctx.early_game and useful_setup_actions_likely(state):
            bonus -= 250.0
        if ctx.opponent_hand_count >= 6 or ctx.opponent_near_win:
            bonus += 450.0
        if ctx.late_game:
            bonus += 250.0

    # 9. Attack decision.
    if category == ActionCategory.ATTACK:
        if raw_score >= KO_SCORE_THRESHOLD:
            bonus += 1800.0
        elif useful_pre_attack_actions_exist(state):
            bonus -= 350.0
        else:
            bonus += 125.0

    # 10. End/pass.
    if category == ActionCategory.END_TURN:
        if useful_non_end_actions_exist(state):
            bonus -= 1800.0
        else:
            bonus += 150.0

    return bonus + mistake_guardrail_bonus(state, action, raw_score, ctx)


def mistake_guardrail_bonus(state: Any, action: ClassifiedAction, raw_score: float, ctx: SequencingContext) -> float:
    category = action.category
    penalty = 0.0

    if category == ActionCategory.PLAY_SUPPORTER and free_draw_or_search_ability_exists(state):
        penalty -= 650.0

    if category == ActionCategory.ATTACH_ENERGY and draw_or_search_action_exists(state):
        if not attachment_enables_attack_now(state, action):
            penalty -= 500.0

    if category in (ActionCategory.PLAY_BASIC_TO_BENCH, ActionCategory.SETUP_CHOOSE_BENCH):
        try:
            from core.setup_recovery_planner import weak_board_ignores_prize_liability

            ignore_prize_liability = weak_board_ignores_prize_liability(state) if use_hydreigon_gengar_strategy(state) else False
        except Exception:
            ignore_prize_liability = False
        if action.card_id in list_value("support_pokemon") and not ignore_prize_liability:
            penalty -= 900.0
        if action.card_id in high_risk_liabilities() and not support_bench_reason_exists(state, action) and not ignore_prize_liability:
            penalty -= 650.0

    if category == ActionCategory.DISCARD_COST:
        if action.card_id in list_value("protected_cards"):
            penalty -= 1200.0
        protected_specific = {229, 227, 1079} if deck_specific else set()
        if action.card_id in (protected_specific | set(list_value("protected_energy_ids"))):
            penalty -= 2500.0

    if is_boss_action(action) and not boss_has_clear_payoff(state, raw_score, ctx):
        penalty -= 1600.0

    if is_recovery_action(action) and not recovery_needed(state, action, ctx):
        penalty -= 1200.0

    if is_energy_recycler_action(action) and not energy_recycler_needed(state, ctx):
        penalty -= 1600.0

    if category == ActionCategory.PLAY_STADIUM and own_useful_stadium_in_play(state, action):
        penalty -= 900.0

    if category == ActionCategory.RETREAT and not retreat_improves_position(state):
        penalty -= 1000.0

    if category == ActionCategory.END_TURN and safe_useful_attachment_exists(state):
        penalty -= 2500.0

    return penalty


def is_mandatory_window(state: Any, action: ClassifiedAction) -> bool:
    min_count = int_or(getv(state.select, "minCount", 0), 0)
    if min_count <= 0:
        return False
    if action.category in MANDATORY_CATEGORIES:
        return True
    return False


def count_in_play(state: Any, wanted_id: int) -> int:
    return sum(1 for _, _, pokemon in iter_in_play(state) if card_id(pokemon) == wanted_id)


def high_risk_liabilities() -> set:
    mapping = load_profile().get("prize_mapping", {}) or {}
    return set(mapping.get("high_risk_liabilities", []))


def is_disruption_action(action: ClassifiedAction) -> bool:
    text = (action.card_name + " " + action.option_text).lower()
    return any(term in text for term in ("red card", "petrel", "boss", "orders", "opponent", "shuffle", "discard", "hand"))


def is_boss_action(action: ClassifiedAction) -> bool:
    return "boss" in (action.card_name + " " + action.option_text).lower()


def is_recovery_action(action: ClassifiedAction) -> bool:
    text = (action.card_name + " " + action.option_text).lower()
    return any(term in text for term in ("night stretcher", "sacred ash", "energy recycler", "from your discard pile", "shuffle up to"))


def is_energy_recycler_action(action: ClassifiedAction) -> bool:
    return "energy recycler" in (action.card_name + " " + action.option_text).lower()


def action_draws_or_searches(action: ClassifiedAction) -> bool:
    text = (action.card_name + " " + action.option_text).lower()
    return action.category == ActionCategory.DRAW_OR_SEARCH or any(
        term in text for term in ("draw", "search your deck", "look at the top", "put it into your hand")
    )


def free_draw_or_search_ability_exists(state: Any) -> bool:
    for idx, option in enumerate(state.options):
        action = classify_legal_option(state, option, idx)
        if action.category != ActionCategory.USE_ABILITY:
            continue
        text = action.option_text.lower()
        if any(term in text for term in ("draw", "search your deck", "look at the top", "put it into your hand")):
            if not any(cost in text for cost in ("discard", "put damage", "knock out", "as a cost")):
                return True
    return False


def draw_or_search_action_exists(state: Any) -> bool:
    for idx, option in enumerate(state.options):
        action = classify_legal_option(state, option, idx)
        if action_draws_or_searches(action) and action.category != ActionCategory.ATTACH_ENERGY:
            return True
    return False


def attachment_enables_attack_now(state: Any, action: ClassifiedAction) -> bool:
    target_id = action.target_id
    if target_id is None:
        return False
    target = None
    for _, _, pokemon in iter_in_play(state):
        if card_id(pokemon) == target_id:
            target = pokemon
            break
    if target is None:
        return False
    card = get_db().get_card(target_id)
    if not card:
        return False
    after_energy = pokemon_energy_count(target) + 1
    return any(after_energy >= len(attack.cost) and int(getattr(attack, "damage", 0) or 0) > 0 for attack in card.attacks)


def support_bench_reason_exists(state: Any, action: ClassifiedAction) -> bool:
    if action.category == ActionCategory.SETUP_CHOOSE_BENCH:
        return True
    if not bench_pokemon(state):
        return False
    text = action.option_text.lower()
    return any(term in text for term in ("draw", "search", "switch", "attach"))


def boss_has_clear_payoff(state: Any, raw_score: float, ctx: SequencingContext) -> bool:
    if raw_score >= KO_SCORE_THRESHOLD or ctx.opponent_near_win or ctx.late_game:
        return True
    active = active_pokemon(state)
    card = get_db().get_card(card_id(active))
    if not active or not card:
        return False
    energy = pokemon_energy_count(active)
    for target in bench_pokemon(state, state.opponent_index):
        target_info = get_db().get_card(card_id(target))
        if not target_info or target_info.prize_value <= 1:
            continue
        for attack in card.attacks:
            if energy >= len(attack.cost) and attack.damage >= pokemon_hp(target):
                return True
    return False


def recovery_needed(state: Any, action: ClassifiedAction, ctx: SequencingContext) -> bool:
    discard_ids = {card_id(card) for card in discard_cards(state) if card_id(card) is not None}
    important = set(list_value("primary_attackers")) | set(list_value("secondary_attackers")) | set(list_value("setup_pokemon")) | set(list_value("protected_energy_ids"))
    if discard_ids & important:
        return True
    if ctx.our_deck_count <= 5:
        return True
    return False


def energy_recycler_needed(state: Any, ctx: SequencingContext) -> bool:
    energy_ids = set(list_value("energy_ids"))
    discarded_energy = sum(1 for card in discard_cards(state) if card_id(card) in energy_ids)
    if discarded_energy >= 3:
        return True
    if ctx.our_deck_count <= 5 and discarded_energy >= 1:
        return True
    return False


def own_useful_stadium_in_play(state: Any, action: ClassifiedAction) -> bool:
    stadium = getv(state.current, "stadium", []) or []
    if not isinstance(stadium, list) or not stadium:
        return False
    db = get_db()
    for stadium_card in stadium:
        owner = int_or(getv(stadium_card, "playerIndex", state.your_index), state.your_index)
        if owner != state.your_index:
            return False
        current = db.get_card(card_id(stadium_card))
        if not current:
            continue
        if current.name == action.card_name:
            return True
        if use_hydreigon_gengar_strategy(state) and current.card_id == 1264:
            return True
    return False


def retreat_improves_position(state: Any) -> bool:
    for pokemon in bench_pokemon(state):
        pid = card_id(pokemon)
        card = get_db().get_card(pid)
        if not card:
            continue
        energy = pokemon_energy_count(pokemon)
        if any(energy >= len(attack.cost) for attack in card.attacks):
            return True
        if card.retreat_cost == 0 and pokemon_hp(pokemon) > max(30, pokemon_max_hp(pokemon) * 0.25):
            return True
    return False


def safe_useful_attachment_exists(state: Any) -> bool:
    if bool(getv(state.current, "energyAttached", False)):
        return False
    for idx, option in enumerate(state.options):
        action = classify_legal_option(state, option, idx)
        if action.category != ActionCategory.ATTACH_ENERGY:
            continue
        if action.card_id in list_value("protected_energy_ids") and action.target_id not in list_value("primary_attackers"):
            continue
        if action.target_id in list_value("energy_attachment_priorities"):
            return True
    return False


def useful_setup_actions_likely(state: Any) -> bool:
    for idx, option in enumerate(state.options):
        action = classify_legal_option(state, option, idx)
        if action.category in (
            ActionCategory.DRAW_OR_SEARCH,
            ActionCategory.PLAY_BASIC_TO_BENCH,
            ActionCategory.SETUP_CHOOSE_BENCH,
            ActionCategory.RARE_CANDY_EVOLVE,
            ActionCategory.EVOLVE,
            ActionCategory.ATTACH_ENERGY,
        ):
            if not is_disruption_action(action):
                return True
    return False


def useful_pre_attack_actions_exist(state: Any) -> bool:
    for idx, option in enumerate(state.options):
        action = classify_legal_option(state, option, idx)
        if action.category == ActionCategory.RETREAT and not retreat_improves_position(state):
            continue
        if action.category in (
            ActionCategory.DRAW_OR_SEARCH,
            ActionCategory.PLAY_BASIC_TO_BENCH,
            ActionCategory.EVOLVE,
            ActionCategory.RARE_CANDY_EVOLVE,
            ActionCategory.ATTACH_ENERGY,
            ActionCategory.SWITCH_ACTIVE,
            ActionCategory.RETREAT,
            ActionCategory.PLAY_ITEM,
            ActionCategory.PLAY_SUPPORTER,
        ):
            if action.category != ActionCategory.ATTACK:
                return True
    return False


def useful_non_end_actions_exist(state: Any) -> bool:
    for idx, option in enumerate(state.options):
        action = classify_legal_option(state, option, idx)
        if action.category == ActionCategory.RETREAT and not retreat_improves_position(state):
            continue
        if action.category in (
            ActionCategory.ATTACK,
            ActionCategory.DRAW_OR_SEARCH,
            ActionCategory.PLAY_BASIC_TO_BENCH,
            ActionCategory.EVOLVE,
            ActionCategory.RARE_CANDY_EVOLVE,
            ActionCategory.ATTACH_ENERGY,
            ActionCategory.USE_ABILITY,
            ActionCategory.SWITCH_ACTIVE,
            ActionCategory.RETREAT,
            ActionCategory.PLAY_ITEM,
            ActionCategory.PLAY_SUPPORTER,
            ActionCategory.PLAY_STADIUM,
        ):
            return True
    return False
