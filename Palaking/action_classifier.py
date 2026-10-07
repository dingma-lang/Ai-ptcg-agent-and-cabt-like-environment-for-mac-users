from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from card_db import get_db
from state_eval import (
    AREA_ACTIVE,
    AREA_BENCH,
    AREA_DISCARD,
    AREA_HAND,
    AREA_PRIZE,
    AREA_STADIUM,
    CTX_ACTIVATE,
    CTX_AFFECT_SPECIAL_CONDITION,
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
    CTX_TO_PRIZE,
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
    card_id,
    card_id_from_option,
    enum_int,
    get_card_from_area,
    get_pokemon_by_area,
    getv,
    int_or,
    normalize_state,
    option_number,
    option_type,
    pokemon_from_card_option,
)


ACTION_CATEGORIES = [
    "SETUP_CHOOSE_ACTIVE",
    "SETUP_CHOOSE_BENCH",
    "MULLIGAN_DECISION",
    "GO_FIRST_SECOND_DECISION",
    "DRAW_OR_SEARCH",
    "PLAY_BASIC_TO_BENCH",
    "EVOLVE",
    "RARE_CANDY_EVOLVE",
    "ATTACH_ENERGY",
    "PLAY_ITEM",
    "PLAY_SUPPORTER",
    "PLAY_STADIUM",
    "USE_ABILITY",
    "RETREAT",
    "SWITCH_ACTIVE",
    "ATTACK",
    "CHOOSE_ATTACK_TARGET",
    "CHOOSE_EFFECT_TARGET",
    "DISCARD_COST",
    "RECOVER_FROM_DISCARD",
    "SHUFFLE_INTO_DECK",
    "PRIZE_SELECTION",
    "PROMOTE_AFTER_KO",
    "SPECIAL_CONDITION_CHECK",
    "YES_NO_DECISION",
    "COUNT_SELECTION",
    "END_TURN",
    "UNKNOWN",
]


class ActionCategory:
    SETUP_CHOOSE_ACTIVE = "SETUP_CHOOSE_ACTIVE"
    SETUP_CHOOSE_BENCH = "SETUP_CHOOSE_BENCH"
    MULLIGAN_DECISION = "MULLIGAN_DECISION"
    GO_FIRST_SECOND_DECISION = "GO_FIRST_SECOND_DECISION"
    DRAW_OR_SEARCH = "DRAW_OR_SEARCH"
    PLAY_BASIC_TO_BENCH = "PLAY_BASIC_TO_BENCH"
    EVOLVE = "EVOLVE"
    RARE_CANDY_EVOLVE = "RARE_CANDY_EVOLVE"
    ATTACH_ENERGY = "ATTACH_ENERGY"
    PLAY_ITEM = "PLAY_ITEM"
    PLAY_SUPPORTER = "PLAY_SUPPORTER"
    PLAY_STADIUM = "PLAY_STADIUM"
    USE_ABILITY = "USE_ABILITY"
    RETREAT = "RETREAT"
    SWITCH_ACTIVE = "SWITCH_ACTIVE"
    ATTACK = "ATTACK"
    CHOOSE_ATTACK_TARGET = "CHOOSE_ATTACK_TARGET"
    CHOOSE_EFFECT_TARGET = "CHOOSE_EFFECT_TARGET"
    DISCARD_COST = "DISCARD_COST"
    RECOVER_FROM_DISCARD = "RECOVER_FROM_DISCARD"
    SHUFFLE_INTO_DECK = "SHUFFLE_INTO_DECK"
    PRIZE_SELECTION = "PRIZE_SELECTION"
    PROMOTE_AFTER_KO = "PROMOTE_AFTER_KO"
    SPECIAL_CONDITION_CHECK = "SPECIAL_CONDITION_CHECK"
    YES_NO_DECISION = "YES_NO_DECISION"
    COUNT_SELECTION = "COUNT_SELECTION"
    END_TURN = "END_TURN"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ClassifiedAction:
    index: int
    category: str
    option_type: int
    select_context: int
    card_id: Optional[int] = None
    card_name: str = ""
    card_type: str = ""
    attack_id: Optional[int] = None
    attack_name: str = ""
    target_id: Optional[int] = None
    target_name: str = ""
    source_area: int = -1
    source_index: int = -1
    target_area: int = -1
    target_index: int = -1
    number: int = 0
    option_text: str = ""
    evidence: List[str] = field(default_factory=list)

    def as_log_dict(self, score: Optional[float] = None, reason: str = "") -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "index": self.index,
            "category": self.category,
            "option_type": self.option_type,
            "context": self.select_context,
        }
        if self.card_id is not None:
            data["card_id"] = self.card_id
            data["card_name"] = self.card_name
        if self.attack_id is not None:
            data["attack_id"] = self.attack_id
            data["attack_name"] = self.attack_name
        if self.target_id is not None:
            data["target_id"] = self.target_id
            data["target_name"] = self.target_name
        if self.number:
            data["number"] = self.number
        if score is not None:
            data["score"] = round(float(score), 3)
        if reason:
            data["reason"] = reason
        return data


def classify_legal_option(obs_or_state: Any, option: Any, option_index: int = 0) -> ClassifiedAction:
    try:
        state = obs_or_state if hasattr(obs_or_state, "select") else normalize_state(obs_or_state)
        return _classify(state, option, option_index)
    except Exception:
        return ClassifiedAction(
            index=option_index,
            category=ActionCategory.UNKNOWN,
            option_type=option_type(option),
            select_context=-1,
            evidence=["classifier fallback"],
        )


def classify_legal_options(obs_or_state: Any) -> List[ClassifiedAction]:
    state = obs_or_state if hasattr(obs_or_state, "select") else normalize_state(obs_or_state)
    options = getattr(state, "options", []) or []
    return [classify_legal_option(state, option, index) for index, option in enumerate(options)]


def _classify(state: Any, option: Any, option_index: int) -> ClassifiedAction:
    db = get_db()
    typ = option_type(option)
    context = int_or(getv(state.select, "context", -1), -1)
    evidence: List[str] = []
    cid = card_id_from_option(state, option)
    card = db.get_card(cid)
    attack_id = getv(option, "attackId")
    attack_id_int = int_or(attack_id, -1) if attack_id is not None else None
    attack = db.get_attack(attack_id_int)
    source_area = enum_int(getv(option, "area", AREA_HAND if typ in (OPT_PLAY, OPT_ATTACH, OPT_EVOLVE) else -1), -1)
    source_index = int_or(getv(option, "index", -1), -1)
    target_area = enum_int(getv(option, "inPlayArea", getv(option, "area", -1)), -1)
    target_index = int_or(getv(option, "inPlayIndex", getv(option, "index", -1)), -1)
    target_id = _target_card_id(state, option, typ, context)
    target_card = db.get_card(target_id)
    text = _option_text(option, card, attack)
    lower_text = text.lower()

    category = ActionCategory.UNKNOWN
    if context == CTX_SETUP_ACTIVE:
        category = ActionCategory.SETUP_CHOOSE_ACTIVE
        evidence.append("select context is setup active")
    elif context == CTX_SETUP_BENCH:
        category = ActionCategory.SETUP_CHOOSE_BENCH
        evidence.append("select context is setup bench")
    elif context == CTX_MULLIGAN:
        category = ActionCategory.MULLIGAN_DECISION
        evidence.append("select context is mulligan")
    elif context == CTX_IS_FIRST:
        category = ActionCategory.GO_FIRST_SECOND_DECISION
        evidence.append("select context is first/second decision")
    elif typ == OPT_END:
        category = ActionCategory.END_TURN
        evidence.append("option type is END")
    elif typ == OPT_ATTACK:
        if _attack_is_ability(attack):
            if cid is None:
                cid = card_id(active_pokemon(state))
                card = db.get_card(cid)
            category = ActionCategory.USE_ABILITY
            evidence.append("attack-shaped option is an Ability")
        else:
            category = ActionCategory.ATTACK if context != CTX_DAMAGE else ActionCategory.CHOOSE_ATTACK_TARGET
            evidence.append("option type is ATTACK")
    elif typ == OPT_RETREAT:
        category = ActionCategory.RETREAT
        evidence.append("option type is RETREAT")
    elif typ == OPT_ABILITY:
        category = ActionCategory.USE_ABILITY
        evidence.append("option type is ABILITY")
    elif typ == OPT_EVOLVE:
        category = ActionCategory.EVOLVE
        evidence.append("option type is EVOLVE")
    elif typ == OPT_ATTACH:
        if card and "Energy" in card.card_type:
            category = ActionCategory.ATTACH_ENERGY
            evidence.append("attached card metadata is Energy")
        else:
            category = ActionCategory.PLAY_ITEM
            evidence.append("attach option for non-Energy card")
    elif typ == OPT_PLAY:
        category = _classify_play(card, lower_text, evidence)
    elif typ == OPT_DISCARD:
        category = ActionCategory.DISCARD_COST
        evidence.append("option type is DISCARD")
    elif typ in (OPT_CARD, OPT_TOOL_CARD, OPT_ENERGY_CARD, OPT_ENERGY):
        if cid is None and typ in (OPT_TOOL_CARD, OPT_ENERGY_CARD, OPT_ENERGY):
            cid = attached_card_id_from_option(state, option)
            card = db.get_card(cid)
        category = _classify_card_selection(state, option, context, source_area, evidence, lower_text)
    elif typ == OPT_NUMBER:
        category = ActionCategory.COUNT_SELECTION
        evidence.append("option type is NUMBER")
    elif typ in (OPT_YES, OPT_NO):
        category = _classify_yes_no(context, evidence)
    elif typ in (OPT_SKILL, OPT_SPECIAL_CONDITION):
        category = ActionCategory.SPECIAL_CONDITION_CHECK if typ == OPT_SPECIAL_CONDITION else ActionCategory.CHOOSE_EFFECT_TARGET
        evidence.append("skill/special-condition option")

    return ClassifiedAction(
        index=option_index,
        category=category if category in ACTION_CATEGORIES else ActionCategory.UNKNOWN,
        option_type=typ,
        select_context=context,
        card_id=cid,
        card_name=card.name if card else "",
        card_type=card.card_type if card else "",
        attack_id=attack_id_int,
        attack_name=attack.name if attack else "",
        target_id=target_id,
        target_name=target_card.name if target_card else "",
        source_area=source_area,
        source_index=source_index,
        target_area=target_area,
        target_index=target_index,
        number=option_number(option),
        option_text=text,
        evidence=evidence,
    )


def _classify_play(card: Any, lower_text: str, evidence: List[str]) -> str:
    if card is None:
        evidence.append("missing card metadata for PLAY")
        return ActionCategory.UNKNOWN
    if "evolve" in lower_text and "stage 2" in lower_text:
        evidence.append("evolution shortcut text")
        return ActionCategory.RARE_CANDY_EVOLVE
    if card.card_type == "Pokemon" and card.basic:
        evidence.append("Basic Pokemon played from hand")
        return ActionCategory.PLAY_BASIC_TO_BENCH
    if card.card_type == "Supporter":
        evidence.append("Supporter metadata")
        return ActionCategory.PLAY_SUPPORTER
    if card.card_type == "Stadium":
        evidence.append("Stadium metadata")
        return ActionCategory.PLAY_STADIUM
    if card.card_type in ("Item", "Tool"):
        if _is_draw_or_search_text(lower_text):
            evidence.append("Item/Tool has draw/search text")
            return ActionCategory.DRAW_OR_SEARCH
        evidence.append("Item/Tool metadata")
        return ActionCategory.PLAY_ITEM
    if _is_draw_or_search_text(lower_text):
        evidence.append("card text has draw/search text")
        return ActionCategory.DRAW_OR_SEARCH
    evidence.append("PLAY fallback")
    return ActionCategory.UNKNOWN


def _attack_is_ability(attack: Any) -> bool:
    name = str(getattr(attack, "name", "") or "")
    text = str(getattr(attack, "text", "") or "")
    combined = f"{name} {text}".lower()
    return name.startswith("[Ability]") or combined.startswith("[ability]") or "once during your turn" in combined


def _classify_card_selection(state: Any, option: Any, context: int, source_area: int, evidence: List[str], lower_text: str) -> str:
    if context == CTX_TO_ACTIVE:
        evidence.append("select context is to active")
        return ActionCategory.PROMOTE_AFTER_KO
    if context == CTX_SWITCH:
        evidence.append("select context is switch")
        return ActionCategory.SWITCH_ACTIVE
    if context == CTX_TO_PRIZE or source_area == AREA_PRIZE:
        evidence.append("select context/zone is prize")
        return ActionCategory.PRIZE_SELECTION
    if context in (CTX_TO_HAND, CTX_LOOK, CTX_TO_BENCH, CTX_TO_FIELD, CTX_EVOLVES_FROM, CTX_EVOLVES_TO, CTX_EVOLVE):
        evidence.append("select context takes/sees card")
        return ActionCategory.DRAW_OR_SEARCH
    if context in (CTX_DISCARD, CTX_DISCARD_CARD_OR_ATTACHED_CARD, CTX_DISCARD_ENERGY, CTX_DISCARD_ENERGY_CARD, CTX_DISCARD_TOOL_CARD):
        evidence.append("select context is discard/cost")
        return ActionCategory.DISCARD_COST
    if context in (CTX_TO_DECK, CTX_TO_DECK_BOTTOM, CTX_NOT_MOVE):
        evidence.append("select context moves card to deck")
        return ActionCategory.SHUFFLE_INTO_DECK
    if context in (CTX_DAMAGE_COUNTER, CTX_DAMAGE_COUNTER_ANY, CTX_DAMAGE):
        evidence.append("select context is damage target")
        return ActionCategory.CHOOSE_ATTACK_TARGET
    if context in (CTX_EFFECT_TARGET, CTX_ATTACH_TO):
        evidence.append("select context is effect target")
        return ActionCategory.CHOOSE_EFFECT_TARGET
    if context in (CTX_HEAL, CTX_REMOVE_DAMAGE_COUNTER):
        evidence.append("select context is recovery/heal")
        return ActionCategory.RECOVER_FROM_DISCARD
    if source_area == AREA_DISCARD:
        evidence.append("source zone is discard")
        return ActionCategory.RECOVER_FROM_DISCARD
    if _is_draw_or_search_text(lower_text):
        evidence.append("option/card text has draw/search")
        return ActionCategory.DRAW_OR_SEARCH
    evidence.append("card selection fallback")
    return ActionCategory.UNKNOWN


def _classify_yes_no(context: int, evidence: List[str]) -> str:
    if context == CTX_MULLIGAN:
        evidence.append("yes/no mulligan context")
        return ActionCategory.MULLIGAN_DECISION
    if context == CTX_IS_FIRST:
        evidence.append("yes/no first/second context")
        return ActionCategory.GO_FIRST_SECOND_DECISION
    if context in (CTX_AFFECT_SPECIAL_CONDITION, CTX_RECOVER_SPECIAL_CONDITION, CTX_COIN_HEAD):
        evidence.append("yes/no special-condition or coin context")
        return ActionCategory.SPECIAL_CONDITION_CHECK
    if context in (CTX_ACTIVATE, CTX_FIRST_EFFECT, CTX_MORE_DEVOLVE):
        evidence.append("yes/no effect activation context")
        return ActionCategory.YES_NO_DECISION
    evidence.append("yes/no fallback")
    return ActionCategory.YES_NO_DECISION


def _target_card_id(state: Any, option: Any, typ: int, context: int) -> Optional[int]:
    if typ == OPT_ATTACH:
        return card_id(attach_target_from_option(state, option))
    if typ == OPT_EVOLVE:
        target = get_pokemon_by_area(state, getv(option, "inPlayArea"), getv(option, "inPlayIndex"), state.your_index)
        return card_id(target)
    if typ in (OPT_CARD, OPT_TOOL_CARD, OPT_ENERGY_CARD, OPT_ENERGY):
        target = pokemon_from_card_option(state, option)
        if target is not None:
            return card_id(target)
        card = get_card_from_area(
            state,
            getv(option, "area"),
            getv(option, "index"),
            int_or(getv(option, "playerIndex", state.your_index), state.your_index),
        )
        return card_id(card)
    return None


def _option_text(option: Any, card: Any, attack: Any) -> str:
    pieces: List[str] = []
    explicit = getv(option, "text") or getv(option, "label") or getv(option, "name")
    if explicit:
        pieces.append(str(explicit))
    if card:
        pieces.append(card.name)
        pieces.append(getattr(card, "text", "") or "")
        pieces.extend(skill.text for skill in getattr(card, "skills", []) if getattr(skill, "text", ""))
    if attack:
        pieces.append(attack.name)
        pieces.append(attack.text or "")
    return " ".join(piece for piece in pieces if piece)


def _is_draw_or_search_text(text: str) -> bool:
    return any(word in text for word in ("draw", "search your deck", "look at the top", "put it into your hand"))
