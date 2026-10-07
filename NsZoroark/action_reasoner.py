from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

from card_db import get_db
from state_eval import (
    AREA_ACTIVE,
    AREA_BENCH,
    AREA_HAND,
    CTX_ACTIVATE,
    CTX_AFFECT_SPECIAL_CONDITION,
    CTX_ATTACK,
    CTX_ATTACH_TO,
    CTX_COIN_HEAD,
    CTX_DAMAGE,
    CTX_DAMAGE_COUNTER,
    CTX_DAMAGE_COUNTER_ANY,
    CTX_DAMAGE_COUNTER_COUNT,
    CTX_DISCARD,
    CTX_DISCARD_CARD_OR_ATTACHED_CARD,
    CTX_DISCARD_ENERGY,
    CTX_DISCARD_ENERGY_CARD,
    CTX_DISCARD_TOOL_CARD,
    CTX_DRAW_COUNT,
    CTX_EFFECT_TARGET,
    CTX_EVOLVE,
    CTX_EVOLVES_FROM,
    CTX_EVOLVES_TO,
    CTX_FIRST_EFFECT,
    CTX_HEAL,
    CTX_IS_FIRST,
    CTX_LOOK,
    CTX_MORE_DEVOLVE,
    CTX_MULLIGAN,
    CTX_NOT_MOVE,
    CTX_RECOVER_SPECIAL_CONDITION,
    CTX_REMOVE_DAMAGE_COUNTER,
    CTX_REMOVE_DAMAGE_COUNTER_COUNT,
    CTX_SETUP_ACTIVE,
    CTX_SETUP_BENCH,
    CTX_SWITCH,
    CTX_TO_ACTIVE,
    CTX_TO_BENCH,
    CTX_TO_DECK,
    CTX_TO_DECK_BOTTOM,
    CTX_TO_FIELD,
    CTX_TO_HAND,
    OPT_ABILITY,
    OPT_ATTACH,
    OPT_ATTACK,
    OPT_CARD,
    OPT_DISCARD,
    OPT_END,
    OPT_ENERGY,
    OPT_ENERGY_CARD,
    OPT_EVOLVE,
    OPT_NO,
    OPT_NUMBER,
    OPT_PLAY,
    OPT_RETREAT,
    OPT_SKILL,
    OPT_SPECIAL_CONDITION,
    OPT_TOOL_CARD,
    OPT_YES,
    active_pokemon,
    attach_target_from_option,
    attached_card_id_from_option,
    bench_space,
    card_id,
    card_id_from_option,
    enum_int,
    get_pokemon_by_area,
    getv,
    int_or,
    option_number,
    option_type,
    pokemon_from_card_option,
)


class ActionClass:
    PLAY_FROM_HAND = "PLAY_FROM_HAND"
    BENCH_BASIC = "BENCH_BASIC"
    PLAY_ITEM = "PLAY_ITEM"
    PLAY_SUPPORTER = "PLAY_SUPPORTER"
    PLAY_STADIUM = "PLAY_STADIUM"
    ATTACH_TOOL = "ATTACH_TOOL"
    ATTACH_ENERGY = "ATTACH_ENERGY"
    EVOLVE = "EVOLVE"
    ABILITY = "ABILITY"
    RETREAT = "RETREAT"
    ATTACK = "ATTACK"
    END_TURN = "END_TURN"
    DISCARD_FROM_PLAY = "DISCARD_FROM_PLAY"
    SELECT_CARD = "SELECT_CARD"
    SETUP_ACTIVE = "SETUP_ACTIVE"
    SETUP_BENCH = "SETUP_BENCH"
    PROMOTE_ACTIVE = "PROMOTE_ACTIVE"
    SWITCH_TARGET = "SWITCH_TARGET"
    SEARCH_TAKE_CARD = "SEARCH_TAKE_CARD"
    DISCARD_COST = "DISCARD_COST"
    DAMAGE_TARGET = "DAMAGE_TARGET"
    HEAL_TARGET = "HEAL_TARGET"
    ATTACH_TARGET = "ATTACH_TARGET"
    COUNT_CHOICE = "COUNT_CHOICE"
    YES_NO = "YES_NO"
    COIN_CALL = "COIN_CALL"
    MULLIGAN_CHOICE = "MULLIGAN_CHOICE"
    GO_FIRST_CHOICE = "GO_FIRST_CHOICE"
    SPECIAL_CONDITION = "SPECIAL_CONDITION"
    SKILL_ORDER = "SKILL_ORDER"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class TurnRules:
    turn: int = 0
    action_count: int = 0
    your_index: int = 0
    opponent_index: int = 1
    first_player: int = -1
    supporter_played: bool = False
    stadium_played: bool = False
    energy_attached: bool = False
    retreated: bool = False
    has_active: bool = False
    bench_space: int = 0

    @property
    def is_first_turn_of_game(self) -> bool:
        return self.turn == 1

    @property
    def is_first_player_first_turn(self) -> bool:
        return self.turn == 1 and self.first_player == self.your_index


@dataclass(frozen=True)
class ActionIntent:
    option_index: int
    option_type: int
    context: int
    action_class: str
    card_id: Optional[int] = None
    card_name: str = ""
    card_type: str = ""
    target_id: Optional[int] = None
    target_name: str = ""
    target_area: int = -1
    target_index: int = -1
    number: int = 0
    is_optional: bool = False
    is_mandatory: bool = False
    rule_notes: List[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        parts = [self.action_class]
        if self.card_name:
            parts.append(self.card_name)
        if self.target_name:
            parts.append("-> " + self.target_name)
        if self.number:
            parts.append(str(self.number))
        return " ".join(parts)


def turn_rules(state: Any) -> TurnRules:
    return TurnRules(
        turn=int_or(getv(state.current, "turn", 0), 0),
        action_count=int_or(getv(state.current, "turnActionCount", 0), 0),
        your_index=int_or(getv(state.current, "yourIndex", state.your_index), state.your_index),
        opponent_index=state.opponent_index,
        first_player=int_or(getv(state.current, "firstPlayer", -1), -1),
        supporter_played=bool(getv(state.current, "supporterPlayed", False)),
        stadium_played=bool(getv(state.current, "stadiumPlayed", False)),
        energy_attached=bool(getv(state.current, "energyAttached", False)),
        retreated=bool(getv(state.current, "retreated", False)),
        has_active=active_pokemon(state) is not None,
        bench_space=bench_space(state),
    )


def classify_option(state: Any, option: Any, option_index: int = 0) -> ActionIntent:
    typ = option_type(option)
    context = state.context
    rules = turn_rules(state)
    db = get_db()
    notes: List[str] = []
    cid = card_id_from_option(state, option)
    card = db.get_card(cid)
    attack = db.get_attack(getv(option, "attackId"))
    target = None
    target_id = None
    target_area = enum_int(getv(option, "inPlayArea", getv(option, "area", -1)), -1)
    target_index = int_or(getv(option, "inPlayIndex", getv(option, "index", -1)), -1)

    if typ == OPT_ATTACH:
        target = attach_target_from_option(state, option)
        target_id = card_id(target)
    elif typ in (OPT_CARD, OPT_TOOL_CARD, OPT_ENERGY_CARD, OPT_ENERGY):
        target = pokemon_from_card_option(state, option)
        if target is not None:
            target_id = card_id(target)
        if cid is None and typ in (OPT_TOOL_CARD, OPT_ENERGY_CARD, OPT_ENERGY):
            cid = attached_card_id_from_option(state, option)
            card = db.get_card(cid)
    elif typ == OPT_EVOLVE:
        target = get_pokemon_by_area(state, getv(option, "inPlayArea"), getv(option, "inPlayIndex"), state.your_index)
        target_id = card_id(target)

    action_class = ActionClass.UNKNOWN
    if typ == OPT_PLAY:
        action_class = classify_play_card(card)
    elif typ == OPT_ATTACH:
        action_class = classify_attach_card(card)
    elif typ == OPT_EVOLVE:
        action_class = ActionClass.EVOLVE
    elif typ == OPT_ABILITY:
        action_class = ActionClass.ABILITY
    elif typ == OPT_RETREAT:
        action_class = ActionClass.RETREAT
    elif typ == OPT_ATTACK:
        if attack_is_ability(attack):
            action_class = ActionClass.ABILITY
            if cid is None:
                cid = card_id(active_pokemon(state))
                card = db.get_card(cid)
        else:
            action_class = ActionClass.ATTACK
    elif typ == OPT_END:
        action_class = ActionClass.END_TURN
    elif typ == OPT_DISCARD:
        action_class = ActionClass.DISCARD_FROM_PLAY
    elif typ in (OPT_CARD, OPT_TOOL_CARD, OPT_ENERGY_CARD, OPT_ENERGY):
        action_class = classify_card_context(context)
    elif typ == OPT_NUMBER:
        action_class = ActionClass.COUNT_CHOICE
    elif typ in (OPT_YES, OPT_NO):
        action_class = classify_yes_no_context(context)
    elif typ == OPT_SKILL:
        action_class = ActionClass.SKILL_ORDER
    elif typ == OPT_SPECIAL_CONDITION:
        action_class = ActionClass.SPECIAL_CONDITION

    if action_class == ActionClass.PLAY_SUPPORTER:
        notes.append("one Supporter per turn")
    if action_class == ActionClass.PLAY_STADIUM:
        notes.append("one Stadium play/replacement per turn")
    if action_class == ActionClass.ATTACH_ENERGY:
        notes.append("one manual Energy attachment per turn")
    if action_class == ActionClass.RETREAT:
        notes.append("one retreat per turn and retreat cost applies")
    if action_class == ActionClass.EVOLVE:
        notes.append("evolution timing is enforced by legal options")
        if target is not None and bool(getv(target, "appearThisTurn", False)):
            notes.append("target appeared this turn")
    if action_class == ActionClass.ATTACK:
        notes.append("attack ends the turn after damage/effects and prize checks")
        if rules.is_first_player_first_turn:
            notes.append("first-player first-turn attack restriction is enforced by cabt")
    if action_class in (ActionClass.PROMOTE_ACTIVE, ActionClass.SETUP_ACTIVE):
        notes.append("mandatory Active replacement/setup when minCount requires it")
    if action_class == ActionClass.END_TURN:
        notes.append("pass/end turn is legal when offered")

    return ActionIntent(
        option_index=option_index,
        option_type=typ,
        context=context,
        action_class=action_class,
        card_id=cid,
        card_name=card.name if card else "",
        card_type=card.card_type if card else "",
        target_id=target_id,
        target_name=db.card_name(target_id) if target_id is not None else "",
        target_area=target_area,
        target_index=target_index,
        number=option_number(option),
        is_optional=state.min_count == 0,
        is_mandatory=state.min_count > 0,
        rule_notes=notes,
    )


def classify_play_card(card: Any) -> str:
    if card is None:
        return ActionClass.PLAY_FROM_HAND
    if card.card_type == "Supporter":
        return ActionClass.PLAY_SUPPORTER
    if card.card_type == "Stadium":
        return ActionClass.PLAY_STADIUM
    if card.card_type == "Item":
        return ActionClass.PLAY_ITEM
    if card.card_type == "Tool":
        return ActionClass.ATTACH_TOOL
    if card.card_type == "Pokemon" and card.basic:
        return ActionClass.BENCH_BASIC
    return ActionClass.PLAY_FROM_HAND


def classify_attach_card(card: Any) -> str:
    if card is None:
        return ActionClass.ATTACH_TARGET
    if "Energy" in card.card_type:
        return ActionClass.ATTACH_ENERGY
    if card.card_type == "Tool":
        return ActionClass.ATTACH_TOOL
    return ActionClass.ATTACH_TARGET


def classify_card_context(context: int) -> str:
    if context == CTX_SETUP_ACTIVE:
        return ActionClass.SETUP_ACTIVE
    if context in (CTX_SETUP_BENCH, CTX_TO_BENCH, CTX_TO_FIELD):
        return ActionClass.SETUP_BENCH
    if context == CTX_TO_ACTIVE:
        return ActionClass.PROMOTE_ACTIVE
    if context == CTX_SWITCH:
        return ActionClass.SWITCH_TARGET
    if context in (CTX_TO_HAND, CTX_LOOK, CTX_EVOLVES_FROM, CTX_EVOLVES_TO, CTX_EVOLVE):
        return ActionClass.SEARCH_TAKE_CARD
    if context in (CTX_DISCARD, CTX_DISCARD_CARD_OR_ATTACHED_CARD, CTX_DISCARD_ENERGY_CARD, CTX_DISCARD_TOOL_CARD, CTX_DISCARD_ENERGY):
        return ActionClass.DISCARD_COST
    if context in (CTX_DAMAGE_COUNTER, CTX_DAMAGE_COUNTER_ANY, CTX_DAMAGE, CTX_EFFECT_TARGET):
        return ActionClass.DAMAGE_TARGET
    if context in (CTX_HEAL, CTX_REMOVE_DAMAGE_COUNTER):
        return ActionClass.HEAL_TARGET
    if context == CTX_ATTACH_TO:
        return ActionClass.ATTACH_TARGET
    if context in (CTX_TO_DECK, CTX_TO_DECK_BOTTOM, CTX_NOT_MOVE):
        return ActionClass.SELECT_CARD
    return ActionClass.SELECT_CARD


def attack_is_ability(attack: Any) -> bool:
    name = str(getattr(attack, "name", "") or "")
    text = str(getattr(attack, "text", "") or "")
    combined = f"{name} {text}".lower()
    return name.startswith("[Ability]") or combined.startswith("[ability]") or "once during your turn" in combined


def classify_yes_no_context(context: int) -> str:
    if context == CTX_IS_FIRST:
        return ActionClass.GO_FIRST_CHOICE
    if context == CTX_MULLIGAN:
        return ActionClass.MULLIGAN_CHOICE
    if context == CTX_COIN_HEAD:
        return ActionClass.COIN_CALL
    if context in (CTX_ACTIVATE, CTX_FIRST_EFFECT, CTX_MORE_DEVOLVE):
        return ActionClass.YES_NO
    return ActionClass.YES_NO
