"""Board-dependent corrections from the battle 24 human review."""
from collections import Counter
from itertools import combinations

from card_db import get_db
from state_eval import (
    CTX_DISCARD, CTX_MAIN, CTX_TO_HAND, OPT_ABILITY, OPT_ATTACK, OPT_PLAY,
    active_pokemon, bench_pokemon, card_id, card_id_from_option, getv,
    hand_cards, iter_in_play, option_type,
)
from core.turn_plan import attached_energy_ids, has_air_balloon


def observe_search_deck(state, previous):
    """Retain confirmed own search cards only, never omniscient player.deck."""
    known = dict(previous)
    for event in getv(state.obs, "logs", []) or []:
        if getv(event, "playerIndex") != state.your_index:
            continue
        typ, serial = getv(event, "type"), getv(event, "serial")
        if typ == 4 or (typ == 6 and getv(event, "fromArea") == 1):
            if serial is None:
                known.clear()
            else:
                known.pop(str(serial), None)
        elif typ == 6 and getv(event, "toArea") == 1:
            cid = getv(event, "cardId")
            if serial is not None and cid is not None:
                known[str(serial)] = cid
    deck = getv(state.select, "deck")
    if isinstance(deck, list):
        known = {str(getv(c, "serial")): card_id(c) for c in deck
                 if getv(c, "serial") is not None and card_id(c) is not None
                 and getv(c, "playerIndex", state.your_index) == state.your_index}
    return known


def confirmed_deck_counts(state):
    deck = getv(state.select, "deck")
    if isinstance(deck, list):
        return Counter(card_id(c) for c in deck
                       if getv(c, "playerIndex", state.your_index) == state.your_index)
    return Counter(getattr(state, "confirmed_search_cards", {}).values())


def box_discard_plan(state):
    """Evaluate the cost as a bundle: recovery capacity cannot be spent twice."""
    cache = getattr(state, "decision_score_cache", None)
    if cache is not None and "review_box_plan" in cache:
        return cache["review_box_plan"]
    from core.palafin_planner import score_discard_selection, score_recovery_play, score_surfing_beach_play
    from core.priority_tables import canonical_name_from_id

    hand = hand_cards(state)
    deck = confirmed_deck_counts(state)
    board = Counter(card_id(p) for _, _, p in iter_in_play(state))
    candidates = []
    for index, card in enumerate(hand):
        cid = card_id(card)
        if cid == 1092:
            continue
        score = score_discard_selection(state, cid)
        # A spare Mega may be relinquished while its Stage 1 is not yet in play.
        if cid == 904 and not board[903] and (deck[904] or board[904]):
            score = max(score, 850.0)
        if cid in (902, 903) and board[904] and board[cid] == 0:
            score = max(score, 700.0)
        if cid in (3, 4):
            score = max(score, 600.0)
        info = get_db().get_card(cid)
        replacement = None
        if (info and info.card_type == "Supporter" and getv(state.current, "supporterPlayed", False)
                and any(get_db().get_card(c) and get_db().get_card(c).card_type == "Supporter"
                        for c in deck)):
            score = max(score, 200.0)
        # Exchange low-impact Trainers only when Box can actually return that category.
        replaceable = (
            (cid == 1262 and score_surfing_beach_play(state) < 0)
            or (cid in (1118, 1097) and score_recovery_play(state, canonical_name_from_id(cid)) <= 0)
        )
        if (score < 0 and info and replaceable
                and any(get_db().get_card(c) and get_db().get_card(c).card_type == info.card_type
                        for c in deck if c != 1092)):
            score, replacement = 150.0, info.card_type
        candidates.append((score, index, cid, replacement))
    candidates.sort(key=lambda item: (-item[0], item[1]))
    best, result = float("-inf"), ()
    for group in combinations(candidates[:12], 3):
        if min(c[0] for c in group) < 0:
            continue
        discarded = {c[1] for c in group}
        remaining = Counter(card_id(c) for i, c in enumerate(hand) if i not in discarded)
        energy_cost = sum(c[2] in (3, 4) for c in group)
        # Retrieval returns two; each Stretcher only one. Recovery itself must survive.
        hand_recovery = 2 * remaining[1118] + remaining[1097]
        deck_recovery = 2 if deck[1118] else 1 if deck[1097] else 0
        recovery = hand_recovery + deck_recovery
        if energy_cost > recovery:
            continue
        replacements = Counter(c[3] for c in group if c[3])
        if any(count > 1 for count in replacements.values()):
            continue
        if energy_cost > hand_recovery and replacements["Item"]:
            continue
        if any(c[2] in (902, 903) and board[904] == 0 for c in group):
            continue
        value = sum(c[0] for c in group)
        if value > best:
            best, result = value, tuple(c[1] for c in group)
    if cache is not None:
        cache["review_box_plan"] = result
    return result


def balloon_reset_piece(state):
    if card_id(active_pokemon(state)) != 107 or getv(state.current, "retreated", False):
        return False
    if not any(card_id(p) == 106 and not has_air_balloon(p) for p in bench_pokemon(state)):
        return False
    # Beach moves the Water Active out; Balloon preserves the single free return.
    return any(card_id(c) == 1262 for c in hand_cards(state)) and not any(
        card_id(c) == 1174 for c in hand_cards(state))


def petrel_review_score(state, name):
    if name == "Air Balloon" and balloon_reset_piece(state):
        return 20000.0
    if name == "Secret Box" and not any(card_id(c) == 1092 for c in hand_cards(state)):
        deck = confirmed_deck_counts(state)
        categories = {get_db().get_card(cid).card_type for cid in deck
                      if get_db().get_card(cid) and cid != 1092}
        from core.palafin_planner import secret_box_petrel_package_score

        if (box_discard_plan(state) and {"Item", "Tool", "Supporter", "Stadium"} <= categories
                and secret_box_petrel_package_score(state) >= 7600.0):
            return 22000.0
    return None


def guidance_bridge(state):
    if any(card_id(c) == 903 for c in hand_cards(state)):
        return False
    return (any(card_id(p) == 902 and attached_energy_ids(p)
                and not getv(p, "appearThisTurn", False) for _, _, p in iter_in_play(state))
            and any(card_id(p) == 105 and not getv(p, "appearThisTurn", False)
                    for _, _, p in iter_in_play(state))
            and not any(card_id(c) == 106 for c in hand_cards(state)))


def second_palafin_pivot(state, target):
    from core.expert_battle_planner import free_manual_retreat
    from core.turn_plan import palafin_ex_deck_available

    if card_id(active_pokemon(state)) != 107 or card_id(target) != 106:
        return False
    if not palafin_ex_deck_available(state):
        return False
    # At a committed switch prompt, count only an independently usable return.
    # A Stadium on the board alone does not prove its ability is still unused.
    return (free_manual_retreat(state, target)
            or any(card_id(c) == 1123 for c in hand_cards(state)))


def promotion_score(state, target):
    from core.expert_battle_planner import ko_damage
    from core.turn_plan import palafin_ex_deck_available

    if target is None:
        return 0.0
    cid = card_id(target)
    opponent = active_pokemon(state, state.opponent_index)
    if cid in (51, 107, 904) and ko_damage(state, target, opponent) > 0:
        return 40000.0 + ko_damage(state, target, opponent)
    if cid == 106 and palafin_ex_deck_available(state):
        return 30000.0 + (1000.0 if 3 in attached_energy_ids(target) else 0.0)
    if cid == 105:
        return 26000.0 + (1000.0 if 106 in [card_id(c) for c in hand_cards(state)] else 0.0)
    if cid == 122:
        return 8000.0 if has_air_balloon(target) else 3000.0
    return -2000.0 if cid in (902, 903, 904) else 0.0


def before_commit_choice(state, scores):
    from policy import palaking_pre_attack_checklist_choice
    from core.palafin_planner import score_palaking_option

    if getv(state.select, "context") != CTX_MAIN:
        return None
    for idx, option in enumerate(state.options):
        if (card_id(active_pokemon(state)) == 122 and option_type(option) == OPT_ABILITY
                and card_id_from_option(state, option) == 122
                and not getv(state.current, "supporterPlayed", False)):
            state.expert_battle_reason = "Use the Active's legal Supporter-search ability before retreat or paid draw."
            return idx
        if (option_type(option) == OPT_ABILITY and card_id_from_option(state, option) == 903
                and score_palaking_option(state, option, scores[idx], idx) >= 6500.0
                and any(option_type(o) == OPT_PLAY and card_id_from_option(state, o) == 1092
                        for o in state.options)):
            state.expert_battle_reason = "Use productive Guidance before evaluating Secret Box's three-card cost."
            return idx
    if not any(option_type(o) == OPT_ATTACK for o in state.options):
        return None
    idx = palaking_pre_attack_checklist_choice(state, scores)
    if idx is not None:
        state.expert_battle_reason = "Finish useful preparation before the attack; re-check after this action resolves."
    return idx


def constrain_reviewed_scores(state, scores):
    from core.palafin_planner import score_hilda_play, score_surfing_beach_play
    from core.priority_tables import canonical_name_from_id

    result = list(scores)
    source = card_id(getv(state.select, "effect")) or getv(state.select, "sourceCardId")
    context = getv(state.select, "context")
    for idx, option in enumerate(state.options):
        cid, typ = card_id_from_option(state, option), option_type(option)
        if typ == OPT_PLAY and cid == 1262 and score_surfing_beach_play(state) < 0:
            result[idx] = -100000.0
        if typ == OPT_PLAY and cid == 1225 and score_hilda_play(state) < 0:
            result[idx] = -10000.0
        if context == CTX_TO_HAND and source == 1219:
            reviewed = petrel_review_score(state, canonical_name_from_id(cid))
            if reviewed is not None:
                result[idx] = max(result[idx], 50000.0 + reviewed)
        if context == CTX_TO_HAND and source == 1152 and cid == 903 and guidance_bridge(state):
            result[idx] = max(result[idx], 50000.0)
        if context == CTX_DISCARD and source == 1092:
            plan = box_discard_plan(state)
            if plan:
                # Official discard options address the hand by index.
                chosen = getv(option, "index") in plan and getv(option, "area") == 2
                if chosen:
                    result[idx] = 50000.0
    return result
