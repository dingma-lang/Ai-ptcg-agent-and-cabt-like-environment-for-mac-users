from __future__ import annotations

import json
import hashlib
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from .replay_review import REVIEW_CSS, REVIEW_JS, selection_contract
from .ui_theme import decorate_page


AREA_NAMES = {
    1: "Deck", 2: "Hand", 3: "Discard", 4: "Active", 5: "Bench", 6: "Prize",
    7: "Stadium", 8: "Energy", 9: "Tool", 10: "Pre-evolution", 11: "Player", 12: "Looking",
}
OPTION_NAMES = {
    0: "Number", 1: "Yes", 2: "No", 3: "Card", 4: "ToolCard", 5: "EnergyCard",
    6: "Energy", 7: "Play", 8: "Attach", 9: "Evolve", 10: "Ability", 11: "Discard",
    12: "Retreat", 13: "Attack", 14: "End", 15: "Skill", 16: "SpecialCondition",
}
CONTEXT_NAMES = {
    0: "Main", 1: "SetupActivePokemon", 2: "SetupBenchPokemon", 3: "Switch", 4: "ToActive",
    5: "ToBench", 6: "ToField", 7: "ToHand", 8: "Discard", 9: "ToDeck", 10: "ToDeckBottom",
    11: "ToPrize", 12: "NotMove", 13: "DamageCounter", 14: "DamageCounterAny", 15: "Damage",
    16: "RemoveDamageCounter", 17: "Heal", 18: "EvolvesFrom", 19: "EvolvesTo", 20: "Devolve",
    21: "AttachFrom", 22: "AttachTo", 23: "DetachFrom", 24: "Look", 25: "EffectTarget",
    26: "DiscardEnergyCard", 27: "DiscardToolCard", 28: "SwitchEnergyCard",
    29: "DiscardCardOrAttachedCard", 30: "DiscardEnergy", 31: "ToHandEnergy", 32: "ToDeckEnergy",
    33: "SwitchEnergy", 34: "SkillOrder", 35: "Attack", 36: "DisableAttack", 37: "Evolve",
    38: "DrawCount", 39: "DamageCounterCount", 40: "RemoveDamageCounterCount", 41: "IsFirst",
    42: "Mulligan", 43: "Activate", 44: "FirstEffect", 45: "MoreDevolve", 46: "CoinHead",
    47: "AffectSpecialCondition", 48: "RecoverSpecialCondition",
}
LOG_NAMES = {
    0: "Shuffle", 1: "HasBasicPokemon", 2: "TurnStart", 3: "TurnEnd", 4: "Draw",
    5: "DrawReverse", 6: "MoveCard", 7: "MoveCardReverse", 8: "Switch", 9: "Change",
    10: "Play", 11: "Attach", 12: "Evolve", 13: "Devolve", 14: "MoveAttached",
    15: "Attack", 16: "HpChange", 17: "Poisoned", 18: "Burned", 19: "Asleep",
    20: "Paralyzed", 21: "Confused", 22: "Coin", 23: "Result",
}


def write_official_replay(path: Path, visualizer_text: str) -> None:
    """Turn official VisualizeData into a turn-oriented, standalone review page."""
    try:
        frames = json.loads(visualizer_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"official VisualizeData was not valid JSON: {exc}") from exc
    if not isinstance(frames, list):
        raise ValueError("official VisualizeData must be a JSON array")
    page = render_official_replay(path, frames)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(page, encoding="utf-8")


def render_official_replay(path: Path, frames: list[Any]) -> str:
    card_metadata = load_replay_card_metadata(path)
    names = collect_card_names(frames, card_metadata)
    traces = load_replay_decision_traces(path)
    observations = load_replay_observations(path)
    turns = build_turn_procedures(frames, names, card_metadata, traces, observations)
    page = OFFICIAL_REPLAY_HTML
    page = page.replace("__REPLAY_DATA__", embed_json(frames))
    page = page.replace("__TURN_DATA__", embed_json(turns))
    page = page.replace("__CARD_DATA__", embed_json(card_metadata))
    identity = hashlib.sha256(embed_json(frames).encode("utf-8")).hexdigest()
    page = page.replace("__REVIEW_META__", embed_json({"id": identity, "name": path.stem, "schema_version": 1}))
    page = page.replace("__REVIEW_CSS__", REVIEW_CSS).replace("__REVIEW_JS__", REVIEW_JS)
    return page


class ReplayDataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.active = False
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "script":
            self.active = dict(attrs).get("id") == "replay-data"

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self.active = False

    def handle_data(self, data: str) -> None:
        if self.active:
            self.parts.append(data)


def refresh_replay_html(path: Path, text: str) -> str:
    """Upgrade older generated pages when served, without rewriting the recording."""
    parser = ReplayDataParser()
    parser.feed(text)
    if not parser.parts:
        return text
    try:
        frames = json.loads("".join(parser.parts))
    except json.JSONDecodeError:
        return text
    return render_official_replay(path, frames) if isinstance(frames, list) else text


def load_replay_observations(path: Path) -> dict[int, dict[str, Any]]:
    episode = path.parent.parent / "episodes" / f"{path.stem}.jsonl"
    if not episode.is_file():
        return {}
    try:
        lines = episode.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError):
        return {}
    observations = {}
    for fallback, line in enumerate(lines):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and isinstance(row.get("observation"), dict):
            observations[int_or(row.get("decision_index"), fallback)] = row["observation"]
    return observations


def embed_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":")).replace("</", "<\\/")


def load_replay_decision_traces(replay_path: Path) -> dict[int, dict[str, Any]]:
    episode_path = replay_path.parent.parent / "episodes" / f"{replay_path.stem}.jsonl"
    if not episode_path.is_file():
        return {}
    traces: dict[int, dict[str, Any]] = {}
    try:
        lines = episode_path.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return {}
    for fallback_index, line in enumerate(lines):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict) or not isinstance(row.get("agent_trace"), dict):
            continue
        index = int_or(row.get("decision_index"), fallback_index)
        trace = dict(row["agent_trace"])
        trace["agent_id"] = row.get("agent_id", "")
        trace["player"] = row.get("player")
        traces[index] = trace
    return traces


def load_replay_card_metadata(replay_path: Path) -> dict[str, dict[str, Any]]:
    catalog_path = replay_path.parent.parent / "catalog" / "cards.json"
    if not catalog_path.is_file():
        return {}
    try:
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    rows = payload.get("cards", []) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return {}
    cards: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        card_id = row.get("card_id")
        if not isinstance(card_id, int):
            continue
        raw = row.get("raw") if isinstance(row.get("raw"), dict) else {}
        key = str(card_id)
        card = cards.setdefault(
            key,
            {
                "id": card_id,
                "name": row.get("name") or raw.get("Card Name") or f"Card {card_id}",
                "type": row.get("card_type") or raw.get("Type") or "",
                "hp": row.get("hp"),
                "set": row.get("set_name") or raw.get("Expansion") or "",
                "number": row.get("collector_number") or raw.get("Collection No.") or "",
                "stage": raw.get("Stage (Pokemon)/Type (Energy and Trainer)")
                or raw.get("Stage (Pokémon)/Type (Energy and Trainer)")
                or "",
                "previous_stage": raw.get("Previous stage") or "",
                "rule": raw.get("Rule") or "",
                "weakness": raw.get("Weakness") or "",
                "resistance": raw.get("Resistance (Type)") or "",
                "retreat": raw.get("Retreat") or "",
                "moves": [],
            },
        )
        move_name = str(raw.get("Move Name") or "").strip()
        if move_name and move_name.lower() != "n/a":
            move = {
                "name": move_name,
                "cost": raw.get("Cost") or "",
                "damage": raw.get("Damage") or "",
                "effect": raw.get("Effect Explanation") or "",
            }
            if move not in card["moves"]:
                card["moves"].append(move)
    return cards


def collect_card_names(frames: list[Any], metadata: dict[str, dict[str, Any]]) -> dict[int, str]:
    names = {int(card_id): str(card.get("name") or f"Card {card_id}") for card_id, card in metadata.items()}

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            card_id = value.get("id")
            name = value.get("name")
            if isinstance(card_id, int) and isinstance(name, str) and name:
                names[card_id] = name
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(frames)
    return names


def build_turn_procedures(
    frames: list[dict[str, Any]],
    names: dict[int, str] | None = None,
    metadata: dict[str, dict[str, Any]] | None = None,
    traces: dict[int, dict[str, Any]] | None = None,
    observations: dict[int, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    names = names or collect_card_names(frames, metadata or {})
    metadata = metadata or {}
    traces = traces or {}
    groups: list[dict[str, Any]] = []
    by_key: dict[tuple[Any, ...], dict[str, Any]] = {}
    for source_index in range(max(0, len(frames) - 1)):
        source = frames[source_index] if isinstance(frames[source_index], dict) else {}
        result = frames[source_index + 1] if isinstance(frames[source_index + 1], dict) else {}
        selected = result.get("selected")
        if selected is None:
            continue
        current = source.get("current") if isinstance(source.get("current"), dict) else {}
        turn_number = int_or(current.get("turn"), 0)
        actor = int_or(current.get("yourIndex"), 0)
        key = ("setup",) if turn_number == 0 else (turn_number, actor)
        group = by_key.get(key)
        if group is None:
            is_response = turn_number > 0 and any(item["turn"] == turn_number for item in groups)
            group = {
                "key": "setup" if turn_number == 0 else f"turn-{turn_number}-player-{actor + 1}",
                "turn": turn_number,
                "actor": None if turn_number == 0 else actor,
                "moment": "setup" if turn_number == 0 else "response" if is_response else "turn",
                "label": "Setup" if turn_number == 0 else (
                    f"Turn {turn_number} - Player {actor + 1} response"
                    if is_response else f"Turn {turn_number} - Player {actor + 1}"
                ),
                "start_frame": source_index,
                "result_frame": source_index + 1,
                "start_hands": snapshot_hands(current),
                "end_hands": snapshot_hands(current),
                "start_notes": turn_start_notes(source.get("logs") or [], names),
                "actions": [],
                "changes": [],
                "start_current": current,
            }
            by_key[key] = group
            groups.append(group)
        result_current = result.get("current") if isinstance(result.get("current"), dict) else current
        if turn_number == 0 and not any(group["start_hands"]):
            opening_hands = snapshot_hands(result_current)
            if any(opening_hands):
                group["start_hands"] = opening_hands
                group["start_frame"] = source_index + 1
        group["actions"].append(
            summarize_decision(source, result, selected, source_index, names, metadata, traces.get(source_index),
                               (observations or {}).get(source_index))
        )
        group["result_frame"] = source_index + 1
        group["end_hands"] = snapshot_hands(current)
        group["changes"] = summarize_turn_changes(group["start_current"], result_current, names)

    for group in groups:
        group.pop("start_current", None)
        for number, action in enumerate(group["actions"], start=1):
            action["number"] = number
    return groups


def summarize_decision(
    source: dict[str, Any],
    result: dict[str, Any],
    selected: Any,
    frame_index: int,
    names: dict[int, str],
    metadata: dict[str, dict[str, Any]],
    trace: dict[str, Any] | None = None,
    observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current = source.get("current") if isinstance(source.get("current"), dict) else {}
    select = source.get("select") if isinstance(source.get("select"), dict) else {}
    actor = int_or(current.get("yourIndex"), 0)
    indexes = selected if isinstance(selected, list) else []
    options = select.get("option") if isinstance(select.get("option"), list) else []
    chosen = [options[index] for index in indexes if isinstance(index, int) and 0 <= index < len(options)]
    context = enum_name(select.get("context"), CONTEXT_NAMES, "Unknown")
    resolved = [resolve_option_card(current, option, actor, names, select) for option in chosen]
    resolved = [card for card in resolved if card]
    title = (
        skipped_decision_title(context)
        if not indexes
        else decision_title(current, context, chosen, resolved, actor, names, metadata)
    )
    result_current = result.get("current") if isinstance(result.get("current"), dict) else {}
    crossed_turn = int_or(result_current.get("turn"), 0) != int_or(current.get("turn"), 0)
    details = summarize_engine_logs(result.get("logs") or [], names, metadata, stop_at_turn_start=crossed_turn)
    return {
        "number": 0,
        "frame": frame_index,
        "result_frame": frame_index + 1,
        "actor": actor,
        "context": context,
        "title": title,
        "cards": unique_cards(resolved),
        "details": details,
        "selected": indexes,
        "thought": normalize_decision_trace(trace, indexes),
        "review": build_review_choice(source, observation, indexes, names, metadata),
        "option_types": [enum_name(option.get("type"), OPTION_NAMES, "Unknown") for option in chosen if isinstance(option, dict)],
    }


def build_review_choice(source: dict[str, Any], observation: dict[str, Any] | None,
                        selected: list[int], names: dict[int, str], metadata: dict[str, dict[str, Any]]) -> dict[str, Any]:
    # Agent-visible observations take precedence over the omniscient visualizer.
    visible = observation if isinstance(observation, dict) else source
    select = visible.get("select") if isinstance(visible.get("select"), dict) else {}
    current = visible.get("current") if isinstance(visible.get("current"), dict) else {}
    actor = int_or(current.get("yourIndex"), 0)
    context = enum_name(select.get("context"), CONTEXT_NAMES, "Unknown")
    contract = selection_contract(select)
    if observation is not None and not matching_review_prompt(source, observation):
        contract["editable"] = False
        contract["unavailable_reason"] = "Observation and replay prompts do not match. Comment only."
    effect = card_stub(select.get("effect") or select.get("contextCard"), names)
    choices = []
    options = select.get("option") if isinstance(select.get("option"), list) else []
    for index, option in enumerate(options):
        card = resolve_option_card(current, option, actor, names, select)
        area = enum_name(option.get("area"), AREA_NAMES, "") if isinstance(option, dict) else ""
        kind = enum_name(option.get("type"), OPTION_NAMES, "Unknown") if isinstance(option, dict) else "Unknown"
        # Without the observing player's record, face-down zones are not identifiable.
        if observation is None and area in {"Prize", "Deck"} and not (area == "Deck" and select.get("deck")):
            card = None
        if not card and area in {"Prize", "Deck", "Hand"}:
            label = f"Hidden {area.lower()} card"
        else:
            label = decision_title(current, context, [option], [card] if card else [], actor, names, metadata)
        if kind == "Attack" and isinstance(option, dict):
            label += f" (attack ID {option.get('attackId', '?')})"
        if kind in {"ToolCard", "EnergyCard", "Energy", "Skill", "SpecialCondition", "Unknown"}:
            label = f"{kind}: {card['name'] if card else json.dumps(option, ensure_ascii=True)}"
        location = []
        if isinstance(option, dict):
            if area:
                location.append(f"P{int_or(option.get('playerIndex'), actor) + 1} {area}")
            if type(option.get("index")) is int:
                location.append(f"slot {option['index'] + 1}")
            if option.get("inPlayArea") is not None:
                location.append(f"target {enum_name(option['inPlayArea'], AREA_NAMES, '?')} {int_or(option.get('inPlayIndex'), 0) + 1}")
        if card and card.get("serial") is not None:
            location.append(f"copy {card['serial']}")
        info = metadata.get(str(card["id"]), {}) if card else {}
        for key in ("stage", "hp"):
            if info.get(key) not in (None, "", "n/a"):
                location.append(f"{info[key]} HP" if key == "hp" else str(info[key]))
        choices.append({"index": index, "label": label, "detail": " | ".join(location), "card": card, "option": option})
    players = current.get("players") or []
    player = players[actor] if 0 <= actor < len(players) and isinstance(players[actor], dict) else {}
    facts = {key: current[key] for key in ("supporterPlayed", "energyAttached", "retreated", "stadiumPlayed") if key in current}
    facts["bench_spaces"] = max(0, int_or(player.get("benchMax"), 5) - len(player.get("bench") or []))
    return {**contract, "options": choices, "original": selected, "effect": effect,
            "facts": facts, "visibility": "agent_observation" if observation is not None else "replay_fallback",
            "remaining_energy_cost": select.get("remainEnergyCost"),
            "remaining_damage_counters": select.get("remainDamageCounter")}


def matching_review_prompt(source: dict[str, Any], observation: dict[str, Any]) -> bool:
    def identity(value: dict[str, Any]) -> tuple[Any, ...]:
        current = value.get("current") if isinstance(value.get("current"), dict) else {}
        select = value.get("select") if isinstance(value.get("select"), dict) else {}
        options = select.get("option") if isinstance(select.get("option"), list) else []
        normalized = [{**option, "type": enum_name(option.get("type"), OPTION_NAMES, "Unknown")}
                      if isinstance(option, dict) else option for option in options]
        return (current.get("turn"), current.get("yourIndex"),
                enum_name(select.get("context"), CONTEXT_NAMES, "Unknown"),
                select.get("minCount"), select.get("maxCount"), normalized)
    return identity(source) == identity(observation)


def normalize_decision_trace(trace: dict[str, Any] | None, selected: list[int]) -> dict[str, Any] | None:
    if not isinstance(trace, dict):
        return None
    rows = trace.get("legal_options") if isinstance(trace.get("legal_options"), list) else []
    options = []
    for fallback_index, raw in enumerate(rows):
        if not isinstance(raw, dict):
            continue
        try:
            score = float(raw.get("score", 0.0) or 0.0)
        except (TypeError, ValueError):
            score = 0.0
        options.append(
            {
                "index": int_or(raw.get("index"), fallback_index),
                "category": str(raw.get("category") or "UNKNOWN"),
                "card_name": str(raw.get("card_name") or ""),
                "attack_name": str(raw.get("attack_name") or ""),
                "target_name": str(raw.get("target_name") or ""),
                "score": round(score, 3),
                "reason": str(raw.get("reason") or ""),
                "evidence": [str(item) for item in (raw.get("evidence") or []) if item],
            }
        )
    selected_set = {int(value) for value in selected if isinstance(value, int)}
    return {
        "reason": str(trace.get("reason") or "No explanation was emitted."),
        "moment_type": str(trace.get("moment_type") or ""),
        "agent_id": str(trace.get("agent_id") or ""),
        "selected": sorted(selected_set),
        "options": options,
        "expert_lesson": str(trace.get("expert_sequence") or trace.get("expert_lesson_matched") or ""),
        "expert_reason": str(trace.get("expert_override_reason") or ""),
    }


def skipped_decision_title(context: str) -> str:
    titles = {
        "SetupBenchPokemon": "Finish choosing setup Bench Pokemon",
        "AttachTo": "Attach no additional Energy",
        "ToHand": "Take no card",
        "ToBench": "Put no additional Pokemon onto the Bench",
        "Discard": "Discard no card",
    }
    return titles.get(context, f"Skip optional {split_words(context)}")


def decision_title(
    current: dict[str, Any],
    context: str,
    options: list[Any],
    cards: list[dict[str, Any]],
    actor: int,
    names: dict[int, str],
    metadata: dict[str, dict[str, Any]],
) -> str:
    option_types = [enum_name(option.get("type"), OPTION_NAMES, "Unknown") for option in options if isinstance(option, dict)]
    card_names = [str(card.get("name") or "Unknown card") for card in cards]
    joined = ", ".join(card_names) or "card"
    first = option_types[0] if option_types else "Unknown"
    if first == "Play":
        return f"Play {joined}"
    if first == "Attach":
        option = options[0]
        target = resolve_in_play_card(current, option.get("inPlayArea"), option.get("inPlayIndex"), actor, names)
        return f"Attach {joined} to {target.get('name', 'Pokemon') if target else 'Pokemon'}"
    if first == "Evolve":
        option = options[0]
        target = resolve_in_play_card(current, option.get("inPlayArea"), option.get("inPlayIndex"), actor, names)
        return f"Evolve {target.get('name', 'Pokemon') if target else 'Pokemon'} into {joined}"
    if first == "Ability":
        return f"Use ability of {joined}"
    if first == "Retreat":
        active = player_zone(current, actor, "active")
        return f"Retreat {card_name(active[0], names) if active else 'Active Pokemon'}"
    if first == "Attack":
        active = player_zone(current, actor, "active")
        attacker = card_stub(active[0], names) if active else None
        attack_name = likely_attack_name(attacker, metadata)
        return f"{attacker['name'] if attacker else 'Active Pokemon'} uses {attack_name or 'an attack'}"
    if first == "End":
        return "End turn"
    if first in {"Yes", "No"}:
        if context == "IsFirst":
            return "Choose to go first" if first == "Yes" else "Choose to go second"
        return f"Choose {first} for {split_words(context)}"
    if first == "Number":
        numbers = [str(option.get("number")) for option in options if isinstance(option, dict)]
        return f"Choose {', '.join(numbers)} for {split_words(context)}"
    context_actions = {
        "SetupActivePokemon": "Choose Active Pokemon",
        "SetupBenchPokemon": "Choose setup Bench Pokemon",
        "Switch": "Choose new Active Pokemon",
        "ToActive": "Promote to the Active Spot",
        "ToBench": "Put onto the Bench",
        "ToField": "Put into play",
        "ToHand": "Take into hand",
        "Discard": "Discard",
        "ToDeck": "Shuffle into the deck",
        "ToDeckBottom": "Put on the bottom of the deck",
        "ToPrize": "Choose Prize card",
        "DamageCounter": "Place damage counters on",
        "DamageCounterAny": "Place damage counters on",
        "Damage": "Deal damage to",
        "Heal": "Heal",
        "EvolvesFrom": "Choose Pokemon to evolve",
        "EvolvesTo": "Choose Evolution Pokemon",
        "EffectTarget": "Choose effect target",
        "Attack": "Choose attack",
    }
    action = context_actions.get(context, f"Resolve {split_words(context)}")
    return f"{action}: {joined}" if cards else action


def summarize_engine_logs(
    logs: Any,
    names: dict[int, str],
    metadata: dict[str, dict[str, Any]],
    stop_at_turn_start: bool = False,
) -> list[dict[str, Any]]:
    values = [log for log in logs if isinstance(log, dict)] if isinstance(logs, list) else []
    summaries: list[dict[str, Any]] = []
    index = 0
    while index < len(values):
        log = values[index]
        kind = enum_name(log.get("type"), LOG_NAMES, "Unknown")
        if stop_at_turn_start and kind == "TurnStart":
            break
        if kind in {"Draw", "DrawReverse"}:
            player = int_or(log.get("playerIndex"), 0)
            grouped = []
            while index < len(values):
                item = values[index]
                if enum_name(item.get("type"), LOG_NAMES, "Unknown") != kind or int_or(item.get("playerIndex"), 0) != player:
                    break
                grouped.append(item)
                index += 1
            cards = [card_from_id(item.get("cardId"), names) for item in grouped if isinstance(item.get("cardId"), int)]
            text = f"Player {player + 1} drew {len(grouped)} card{'s' if len(grouped) != 1 else ''}"
            summaries.append({"text": text, "cards": unique_cards(cards), "kind": "draw"})
            continue
        if kind in {"MoveCard", "MoveCardReverse"}:
            player = int_or(log.get("playerIndex"), 0)
            from_area = enum_name(log.get("fromArea"), AREA_NAMES, "Unknown area")
            to_area = enum_name(log.get("toArea"), AREA_NAMES, "Unknown area")
            grouped = []
            while index < len(values):
                item = values[index]
                if (
                    enum_name(item.get("type"), LOG_NAMES, "Unknown") != kind
                    or int_or(item.get("playerIndex"), 0) != player
                    or enum_name(item.get("fromArea"), AREA_NAMES, "Unknown area") != from_area
                    or enum_name(item.get("toArea"), AREA_NAMES, "Unknown area") != to_area
                ):
                    break
                grouped.append(item)
                index += 1
            hidden_prize = to_area == "Prize"
            cards = [] if hidden_prize else [
                card_from_id(item.get("cardId"), names) for item in grouped if isinstance(item.get("cardId"), int)
            ]
            verb = "Set" if hidden_prize else "Moved"
            text = f"{verb} {len(grouped)} card{'s' if len(grouped) != 1 else ''}: {from_area} to {to_area}"
            summaries.append({"text": text, "cards": unique_cards(cards), "kind": "move"})
            continue
        summary = summarize_single_log(log, kind, names, metadata)
        if summary:
            summaries.append(summary)
        index += 1
    return summaries


def summarize_single_log(
    log: dict[str, Any],
    kind: str,
    names: dict[int, str],
    metadata: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    player = int_or(log.get("playerIndex"), 0)
    card = card_from_id(log.get("cardId"), names) if isinstance(log.get("cardId"), int) else None
    cards = [card] if card else []
    if kind == "Shuffle":
        text = f"Player {player + 1} shuffled the deck"
    elif kind == "TurnStart":
        text = f"Player {player + 1} started the turn"
    elif kind == "TurnEnd":
        text = f"Player {player + 1} ended the turn"
    elif kind == "Play":
        text = f"Played {card['name'] if card else 'a card'}"
    elif kind == "Attach":
        target = card_from_id(log.get("cardIdTarget"), names)
        if target:
            cards.append(target)
        text = f"Attached {card['name'] if card else 'a card'} to {target['name'] if target else 'a Pokemon'}"
    elif kind == "Evolve":
        target = card_from_id(log.get("cardIdTarget"), names)
        if target:
            cards.append(target)
        text = f"Evolved {target['name'] if target else 'a Pokemon'} into {card['name'] if card else 'an Evolution Pokemon'}"
    elif kind == "Devolve":
        text = f"Devolved {card['name'] if card else 'a Pokemon'}"
    elif kind == "Switch":
        old_card = card_from_id(log.get("cardIdActive"), names)
        new_card = card_from_id(log.get("cardIdBench"), names)
        cards = unique_cards([old_card, new_card])
        text = f"Switched {old_card['name'] if old_card else 'Active Pokemon'} with {new_card['name'] if new_card else 'Bench Pokemon'}"
    elif kind == "Change":
        old_card = card_from_id(log.get("cardIdBefore"), names)
        new_card = card_from_id(log.get("cardIdAfter"), names)
        cards = unique_cards([old_card, new_card])
        text = f"Changed {old_card['name'] if old_card else 'Pokemon'} into {new_card['name'] if new_card else 'Pokemon'}"
    elif kind == "Attack":
        attack_name = likely_attack_name(card, metadata)
        text = f"{card['name'] if card else 'Active Pokemon'} used {attack_name or 'an attack'}"
    elif kind == "HpChange":
        value = int_or(log.get("value"), 0)
        text = f"{card['name'] if card else 'Pokemon'} {'recovered' if value > 0 else 'lost'} {abs(value)} HP"
    elif kind in {"Poisoned", "Burned", "Asleep", "Paralyzed", "Confused"}:
        text = f"{card['name'] if card else 'Pokemon'} {'recovered from' if log.get('isRecover') else 'became'} {kind.lower()}"
    elif kind == "Coin":
        text = f"Coin flip: {'heads' if log.get('head') else 'tails'}"
    elif kind == "Result":
        result = int_or(log.get("result"), 2)
        reason = {1: "all Prize cards taken", 2: "deck out", 3: "no Active Pokemon", 4: "card effect"}.get(int_or(log.get("reason"), 0), "engine result")
        text = f"{'Draw' if result == 2 else f'Player {result + 1} won'} by {reason}"
    elif kind == "HasBasicPokemon":
        text = f"Player {player + 1} {'has' if log.get('hasBasicPokemon') else 'does not have'} a Basic Pokemon"
    else:
        return None
    return {"text": text, "cards": unique_cards(cards), "kind": kind.lower()}


def turn_start_notes(logs: Any, names: dict[int, str]) -> list[dict[str, Any]]:
    values = [log for log in logs if isinstance(log, dict)] if isinstance(logs, list) else []
    starts = [index for index, log in enumerate(values) if enum_name(log.get("type"), LOG_NAMES, "") == "TurnStart"]
    if not starts:
        return []
    return summarize_engine_logs(values[starts[-1] + 1 :], names, {}, stop_at_turn_start=False)


def summarize_turn_changes(before: dict[str, Any], after: dict[str, Any], names: dict[int, str]) -> list[str]:
    changes: list[str] = []
    before_players = before.get("players") if isinstance(before.get("players"), list) else []
    after_players = after.get("players") if isinstance(after.get("players"), list) else []
    for index in range(max(len(before_players), len(after_players))):
        old = before_players[index] if index < len(before_players) and isinstance(before_players[index], dict) else {}
        new = after_players[index] if index < len(after_players) and isinstance(after_players[index], dict) else {}
        metrics = [
            ("Hand", old.get("handCount", 0), new.get("handCount", 0)),
            ("Deck", old.get("deckCount", 0), new.get("deckCount", 0)),
            ("Bench", len(old.get("bench") or []), len(new.get("bench") or [])),
            ("Prizes", len(old.get("prize") or []), len(new.get("prize") or [])),
            ("Discard", len(old.get("discard") or []), len(new.get("discard") or [])),
        ]
        changed = [f"{label} {left} to {right}" for label, left, right in metrics if left != right]
        old_active = card_name((old.get("active") or [None])[0], names) if old.get("active") else "Empty"
        new_active = card_name((new.get("active") or [None])[0], names) if new.get("active") else "Empty"
        if old_active != new_active:
            changed.append(f"Active {old_active} to {new_active}")
        if changed:
            changes.append(f"Player {index + 1}: " + "; ".join(changed))
    old_stadium = card_name((before.get("stadium") or [None])[0], names) if before.get("stadium") else "None"
    new_stadium = card_name((after.get("stadium") or [None])[0], names) if after.get("stadium") else "None"
    if old_stadium != new_stadium:
        changes.append(f"Stadium: {old_stadium} to {new_stadium}")
    return changes or ["No public board-count changes"]


def snapshot_hands(current: dict[str, Any]) -> list[list[dict[str, Any]]]:
    players = current.get("players") if isinstance(current.get("players"), list) else []
    return [
        unique_cards([card_stub(card, {}) for card in (player.get("hand") or []) if isinstance(card, dict)], by_serial=True)
        if isinstance(player, dict) else []
        for player in players
    ]


def resolve_option_card(current: dict[str, Any], option: Any, actor: int, names: dict[int, str],
                        select: dict[str, Any] | None = None) -> dict[str, Any] | None:
    if not isinstance(option, dict):
        return None
    option_type = enum_name(option.get("type"), OPTION_NAMES, "Unknown")
    area = enum_name(option.get("area"), AREA_NAMES, "")
    index = option.get("index")
    if area == "Deck":
        deck = (select or {}).get("deck")
        return card_stub(deck[index], names) if isinstance(deck, list) and type(index) is int and 0 <= index < len(deck) else None
    if area == "Looking":
        looking = current.get("looking")
        return card_stub(looking[index], names) if isinstance(looking, list) and type(index) is int and 0 <= index < len(looking) else None
    if option_type in {"ToolCard", "EnergyCard", "Energy"}:
        zone = player_zone(current, int_or(option.get("playerIndex"), actor), {"Active": "active", "Bench": "bench"}.get(area, ""))
        pokemon = zone[index] if type(index) is int and 0 <= index < len(zone) else {}
        attached = pokemon.get("tools" if option_type == "ToolCard" else "energyCards", []) if isinstance(pokemon, dict) else []
        attached_index = option.get("toolIndex" if option_type == "ToolCard" else "energyIndex")
        return card_stub(attached[attached_index], names) if type(attached_index) is int and 0 <= attached_index < len(attached) else None
    if option_type == "Skill":
        return card_stub({"id": option.get("cardId"), "serial": option.get("serial")}, names)
    if option_type in {"Play", "Attach", "Evolve"}:
        return resolve_area_card(current, option.get("area", 2), option.get("index"), actor, names)
    if option_type in {"Card", "Ability", "Discard"}:
        return resolve_area_card(current, option.get("area"), option.get("index"), int_or(option.get("playerIndex"), actor), names)
    if option_type == "Attack":
        active = player_zone(current, actor, "active")
        return card_stub(active[0], names) if active else None
    return None


def resolve_in_play_card(current: dict[str, Any], area: Any, index: Any, player: int, names: dict[int, str]) -> dict[str, Any] | None:
    return resolve_area_card(current, area, index, player, names)


def resolve_area_card(current: dict[str, Any], area: Any, index: Any, player: int, names: dict[int, str]) -> dict[str, Any] | None:
    area_name = enum_name(area, AREA_NAMES, "")
    if area_name == "Stadium" and isinstance(index, int):
        stadium = current.get("stadium") if isinstance(current.get("stadium"), list) else []
        return card_stub(stadium[index], names) if 0 <= index < len(stadium) else None
    zone_name = {
        "Deck": "deck", "Hand": "hand", "Discard": "discard", "Active": "active", "Bench": "bench",
        "Prize": "prize", "Energy": "energyCards", "Tool": "tools", "Pre-evolution": "preEvolution",
    }.get(area_name)
    if not zone_name or not isinstance(index, int):
        return None
    zone = player_zone(current, player, zone_name)
    return card_stub(zone[index], names) if 0 <= index < len(zone) and isinstance(zone[index], dict) else None


def player_zone(current: dict[str, Any], player: int, zone: str) -> list[Any]:
    players = current.get("players") if isinstance(current.get("players"), list) else []
    if not (0 <= player < len(players)) or not isinstance(players[player], dict):
        return []
    value = players[player].get(zone)
    return value if isinstance(value, list) else []


def card_stub(card: Any, names: dict[int, str]) -> dict[str, Any] | None:
    if not isinstance(card, dict):
        return None
    card_id = card.get("id")
    if not isinstance(card_id, int):
        return None
    return {
        "id": card_id,
        "serial": card.get("serial"),
        "name": card.get("name") or names.get(card_id) or f"Card {card_id}",
    }


def card_from_id(card_id: Any, names: dict[int, str]) -> dict[str, Any] | None:
    return {"id": card_id, "name": names.get(card_id, f"Card {card_id}")} if isinstance(card_id, int) else None


def card_name(card: Any, names: dict[int, str]) -> str:
    stub = card_stub(card, names)
    return str(stub.get("name")) if stub else "Unknown card"


def unique_cards(cards: list[Any], by_serial: bool = False) -> list[dict[str, Any]]:
    result = []
    seen = set()
    for card in cards:
        if not isinstance(card, dict) or not isinstance(card.get("id"), int):
            continue
        key = (card.get("id"), card.get("serial")) if by_serial else card.get("id")
        if key in seen:
            continue
        seen.add(key)
        result.append(card)
    return result


def likely_attack_name(card: dict[str, Any] | None, metadata: dict[str, dict[str, Any]]) -> str:
    if not card:
        return ""
    moves = (metadata.get(str(card.get("id"))) or {}).get("moves") or []
    attacks = [move for move in moves if not str(move.get("name") or "").startswith("[Ability]")]
    return str(attacks[0].get("name") or "") if len(attacks) == 1 else ""


def enum_name(value: Any, mapping: dict[int, str], default: str) -> str:
    if isinstance(value, str):
        return value
    return mapping.get(value, default) if isinstance(value, int) else default


def split_words(value: str) -> str:
    output = ""
    for char in value:
        if char.isupper() and output:
            output += " "
        output += char.lower()
    return output or "selection"


def int_or(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


OFFICIAL_REPLAY_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Battle Lab | Battle Replay</title>
  <style>
    :root {
      color-scheme:light;
      --ink:#19242c; --muted:#5c6b75; --line:#cbd5dc; --soft:#f4f7f8; --white:#fff;
      --active:#08769a; --active-soft:#eaf7fb; --action:#a05b00; --action-soft:#fff7e8;
      --good:#247348; --bad:#aa3939; --purple:#68518a; --medium:#946200; --low:#61717b;
    }
    * { box-sizing:border-box; }
    body { margin:0; color:var(--ink); background:var(--white); font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
    button,input { font:inherit; }
    button { cursor:pointer; color:var(--ink); }
    header {
      position:sticky; top:0; z-index:10; min-height:58px; display:flex; align-items:center;
      justify-content:space-between; gap:16px; padding:10px 16px; border-bottom:1px solid var(--line); background:#edf4f5;
    }
    h1 { margin:0; font-size:18px; letter-spacing:0; }
    h2 { margin:0; font-size:16px; letter-spacing:0; }
    h3 { margin:0; font-size:13px; letter-spacing:0; }
    .controls { display:flex; align-items:center; flex-wrap:wrap; gap:7px; }
    .icon-button { width:38px; height:36px; border:1px solid var(--line); border-radius:6px; background:white; font-weight:800; }
    .icon-button:hover { border-color:var(--active); background:var(--active-soft); }
    .status, .tag { display:inline-flex; align-items:center; min-height:28px; border:1px solid var(--line); border-radius:6px; background:white; padding:4px 8px; font-size:12px; font-weight:700; }
    .tag { color:var(--ink); text-decoration:none; }
    .status.winner { color:var(--good); border-color:#9bcdb1; background:#eff9f3; }
    .switch { display:flex; gap:7px; align-items:center; font-size:12px; font-weight:700; color:var(--muted); }
    main { display:grid; grid-template-columns:210px minmax(420px,1fr) 350px; min-height:calc(100vh - 58px); }
    nav { border-right:1px solid var(--line); background:var(--soft); padding:12px; overflow:auto; }
    .turn-list { display:grid; gap:5px; }
    .turn-button { width:100%; min-height:42px; border:1px solid transparent; border-radius:6px; background:transparent; padding:7px 9px; text-align:left; display:grid; gap:2px; }
    .turn-button:hover { background:white; border-color:var(--line); }
    .turn-button.current { color:#075e7b; background:white; border-color:#83bdcf; }
    .turn-button strong { font-size:12px; }
    .turn-button span { color:var(--muted); font-size:11px; }
    .procedure { padding:18px; min-width:0; }
    .turn-heading { display:flex; align-items:flex-start; justify-content:space-between; gap:12px; padding-bottom:14px; border-bottom:1px solid var(--line); }
    .turn-heading p { margin:5px 0 0; color:var(--muted); font-size:12px; }
    .section { padding:15px 0; border-bottom:1px solid var(--line); }
    .section:last-child { border-bottom:0; }
    .section-title { display:flex; align-items:center; justify-content:space-between; gap:8px; margin-bottom:9px; }
    .hand-block { display:grid; gap:7px; margin-top:9px; }
    .hand-label { color:var(--muted); font-size:11px; font-weight:800; text-transform:uppercase; }
    .chips { display:flex; flex-wrap:wrap; gap:5px; }
    .card-chip { min-height:28px; max-width:100%; border:1px solid var(--line); border-radius:5px; background:white; padding:4px 7px; font-size:12px; font-weight:650; overflow-wrap:anywhere; }
    .card-chip:hover, .card-chip.selected { color:#075e7b; border-color:#74b2c7; background:var(--active-soft); }
    .empty { color:var(--muted); font-size:12px; }
    .start-notes, .changes { margin:9px 0 0; padding-left:20px; color:var(--muted); font-size:12px; line-height:1.5; }
    .actions { list-style:none; padding:0; margin:0; display:grid; }
    .action { display:grid; grid-template-columns:34px minmax(0,1fr); gap:10px; padding:12px 0; border-bottom:1px solid #e4eaee; }
    .action:last-child { border-bottom:0; }
    .action-number { width:30px; height:30px; display:grid; place-items:center; border-radius:50%; background:#e8eef1; color:#45545e; font-size:12px; font-weight:800; }
    .action.current .action-number { color:white; background:var(--active); }
    .action-main { min-width:0; display:grid; gap:7px; }
    .action-jump { width:100%; min-height:30px; border:0; background:transparent; padding:0; text-align:left; font-weight:800; }
    .action-jump:hover { color:var(--active); }
    .action-context { color:var(--muted); font-size:11px; }
    .effects { display:grid; gap:4px; }
    .effect { display:grid; grid-template-columns:8px minmax(0,1fr); gap:7px; color:#4b5963; font-size:12px; line-height:1.45; }
    .effect::before { content:""; width:6px; height:6px; border-radius:50%; margin-top:6px; background:#d08a2f; }
    .score-guide { display:flex; flex-wrap:wrap; gap:5px; margin:0 0 8px; color:var(--muted); font-size:10px; }
    .score-band { display:inline-flex; align-items:center; min-height:22px; padding:2px 6px; border:1px solid var(--line); border-radius:5px; background:white; font-size:10px; font-weight:800; white-space:nowrap; }
    .score-band.critical { color:#7f2331; border-color:#d9a4ad; background:#fff2f4; }
    .score-band.high { color:var(--good); border-color:#a8cdb8; background:#eff9f3; }
    .score-band.medium { color:var(--medium); border-color:#dfc58d; background:#fff8e9; }
    .score-band.low { color:var(--low); background:#f3f6f7; }
    .score-band.blocked { color:var(--bad); border-color:#deb0b0; background:#fff3f3; }
    .thought { display:grid; gap:7px; padding:9px 10px; border-left:3px solid var(--active); background:#f3f8fa; }
    .thought-head { display:flex; align-items:center; flex-wrap:wrap; gap:6px; }
    .thought-head strong { font-size:12px; }
    .thought p { margin:0; color:#42515b; font-size:12px; line-height:1.45; }
    .override-note { color:var(--medium) !important; font-weight:700; }
    .score-scroll { margin-top:7px; overflow-x:auto; }
    .score-table { min-width:650px; display:grid; border:1px solid var(--line); border-radius:5px; overflow:hidden; background:white; }
    .score-row { display:grid; grid-template-columns:42px 100px minmax(130px,.8fr) 86px minmax(210px,1.6fr); align-items:start; border-top:1px solid #e4eaee; }
    .score-row:first-child { border-top:0; }
    .score-row.heading { color:var(--muted); background:#f3f6f7; font-size:10px; font-weight:800; text-transform:uppercase; }
    .score-row.chosen { background:#edf8fb; box-shadow:inset 3px 0 var(--active); }
    .score-cell { min-width:0; padding:6px; font-size:10px; line-height:1.35; overflow-wrap:anywhere; }
    .score-value { font-variant-numeric:tabular-nums; font-weight:800; text-align:right; }
    details { color:var(--muted); font-size:11px; }
    summary { cursor:pointer; font-weight:700; }
    pre { margin:7px 0 0; max-height:220px; overflow:auto; white-space:pre-wrap; overflow-wrap:anywhere; font:10px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace; background:#f7f9fa; padding:8px; border:1px solid var(--line); border-radius:5px; }
    aside { border-left:1px solid var(--line); background:#fafbfc; padding:14px; overflow:auto; display:grid; gap:14px; align-content:start; }
    .context-section { display:grid; gap:9px; padding-bottom:13px; border-bottom:1px solid var(--line); }
    .context-section:last-child { border-bottom:0; }
    .board-player { display:grid; gap:8px; padding:9px; border:1px solid var(--line); border-radius:7px; background:white; }
    .board-player.acting { border-color:#79b8cd; }
    .board-player-head { display:flex; justify-content:space-between; gap:8px; align-items:center; }
    .stats { color:var(--muted); font-size:10px; }
    .zone { display:grid; gap:5px; }
    .zone-label { color:var(--muted); font-size:10px; font-weight:800; text-transform:uppercase; }
    .pokemon { width:100%; min-height:54px; border:1px solid var(--line); border-radius:6px; background:white; padding:7px; text-align:left; display:grid; gap:4px; }
    .pokemon:hover { border-color:var(--active); }
    .pokemon strong { font-size:12px; }
    .pokemon span { color:var(--muted); font-size:10px; overflow-wrap:anywhere; }
    .hp { height:5px; border-radius:3px; background:#dfe5e8; overflow:hidden; }
    .hp i { display:block; height:100%; background:var(--good); }
    .hp i.low { background:var(--bad); }
    .bench { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:5px; }
    .card-detail { display:grid; gap:8px; }
    .card-detail dl { display:grid; grid-template-columns:82px 1fr; gap:5px 8px; margin:0; font-size:11px; }
    .card-detail dt { color:var(--muted); }
    .card-detail dd { margin:0; overflow-wrap:anywhere; }
    .move { padding:8px 0; border-top:1px solid var(--line); display:grid; gap:4px; }
    .move strong { font-size:12px; }
    .move span, .move p { margin:0; color:var(--muted); font-size:11px; line-height:1.4; }
    .zone-controls { display:flex; flex-wrap:wrap; align-items:center; gap:10px; margin-bottom:10px; }
    .snapshot-modes { display:flex; flex-wrap:wrap; gap:8px 14px; margin:0; padding:0; border:0; font-size:12px; }
    .snapshot-modes label { display:flex; gap:5px; align-items:center; }
    .snapshot-modes input { margin:0; accent-color:var(--active); }
    .zone-tabs { display:flex; border-bottom:1px solid var(--line); margin:10px 0; }
    .zone-tab { flex:1; min-width:0; min-height:36px; padding:7px; border:0; border-bottom:2px solid transparent; background:transparent; font-size:12px; font-weight:700; }
    .zone-tab[aria-selected="true"] { color:var(--active); border-bottom-color:var(--active); background:var(--active-soft); }
    .zone-players { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; }
    .zone-player { min-width:0; }
    .zone-player-head { display:flex; justify-content:space-between; flex-wrap:wrap; gap:5px; margin-bottom:5px; }
    .zone-totals { color:var(--muted); font-size:11px; line-height:1.5; margin:0 0 8px; }
    .zone-inventory { list-style:none; padding:0; margin:0; max-height:250px; overflow:auto; border-block:1px solid var(--line); }
    .zone-row { display:grid; grid-template-columns:minmax(0,1fr) auto; align-items:center; gap:8px; padding:7px 2px; border-bottom:1px solid #e4eaee; font-size:12px; }
    .zone-row:last-child { border-bottom:0; }
    .zone-row button { min-width:0; max-width:100%; text-align:left; border:0; background:transparent; padding:0; color:var(--active); font-size:12px; overflow-wrap:anywhere; }
    .zone-row span { overflow-wrap:anywhere; }
    .zone-quantity { color:var(--muted); font-variant-numeric:tabular-nums; white-space:nowrap; }
    .zone-timing, .zone-visibility, .zone-missing { font-size:11px; line-height:1.5; margin:6px 0; color:var(--muted); overflow-wrap:anywhere; }
    .zone-visibility { color:var(--action); }
    .zone-filter { width:100%; min-width:0; min-height:34px; font:inherit; font-size:12px; padding:7px; border:1px solid var(--line); border-radius:5px; }
    @media (max-width:720px) { .zone-players { grid-template-columns:1fr; gap:14px; } }
    __REVIEW_CSS__
    @media (max-width:1050px) { main { grid-template-columns:180px minmax(380px,1fr); } aside { grid-column:1 / -1; border-left:0; border-top:1px solid var(--line); grid-template-columns:repeat(2,minmax(0,1fr)); } }
    @media (max-width:720px) { header { position:static; align-items:flex-start; flex-direction:column; } main { grid-template-columns:1fr; } nav { border-right:0; border-bottom:1px solid var(--line); max-height:180px; } .procedure { padding:14px; } aside { grid-column:auto; grid-template-columns:1fr; } .bench { grid-template-columns:1fr; } }
  </style>
</head>
<body>
  <header class="app-header">
    <a class="brand" href="/" title="Back to simulator"><span class="brand-mark">__ICON_layers__</span><span><strong>Battle Lab</strong><small>Battle replay</small></span></a>
    <span id="matchStatus" class="status"></span>
    <div class="controls">
      <button id="prevTurn" class="icon-button" title="Previous turn" aria-label="Previous turn">__ICON_chevron-left__</button>
      <button id="play" class="icon-button" title="Play actions" aria-label="Play actions">__ICON_play__</button>
      <button id="nextTurn" class="icon-button" title="Next turn" aria-label="Next turn">__ICON_chevron-right__</button>
      <span id="position" class="status"></span>
      <select id="playbackSpeed" aria-label="Playback speed" title="Playback speed"><option value="1500">0.5x</option><option value="750" selected>1x</option><option value="375">2x</option></select>
      <label class="switch"><input id="showBothHands" type="checkbox"> Both hands</label>
    </div>
  </header>
  <main>
    <nav aria-label="Battle turns"><p class="eyebrow">Turn timeline</p><div id="turnList" class="turn-list"></div></nav>
    <section class="procedure">
      <div class="turn-heading">
        <div><h2 id="turnTitle"></h2><p id="turnSubtitle"></p></div>
        <span id="framePosition" class="tag"></span>
      </div>
      <div class="review-toolbar">
        <label for="reviewFormat">Review output</label>
        <select id="reviewFormat"><option value="txt">Text log</option><option value="json">JSON log</option></select>
        <button class="review-command primary" id="exportReview" disabled>__ICON_download__ Export review</button>
        <button class="review-command" id="clearReview" disabled>Clear reviews</button>
        <span id="reviewStatus" class="review-status" role="status"></span>
        <p id="reviewNotice" class="review-notice"></p>
      </div>
      <div class="section">
        <div class="section-title"><h3 id="startTitle">Start of turn</h3><span id="startTag" class="tag">After draw</span></div>
        <div id="startNotes"></div>
        <div id="startHands"></div>
      </div>
      <div class="section">
        <div class="section-title"><h3>Actions in order</h3><span id="actionCount" class="tag"></span></div>
        <details class="fold"><summary>Score guide</summary><div class="score-guide"><span class="score-band critical">Critical 10,000+</span><span class="score-band high">High 2,500+</span><span class="score-band medium">Medium 500+</span><span class="score-band low">Low 0-499</span><span class="score-band blocked">Blocked below 0</span></div></details>
        <ol id="actions" class="actions"></ol>
      </div>
      <div class="section">
        <div class="section-title"><h3>Before turn ends</h3></div>
        <div id="endHands"></div>
      </div>
      <details class="fold" id="cardZones"><summary>__ICON_layers__ Card zones <span id="zoneFrame" class="tag"></span></summary><div class="fold-body">
        <div class="zone-controls">
          <fieldset class="snapshot-modes" aria-label="Snapshot timing">
            <label><input type="radio" name="snapshotMoment" value="start"> Turn start</label>
            <label><input type="radio" name="snapshotMoment" value="action" checked> Selected action</label>
            <label><input type="radio" name="snapshotMoment" value="end"> After final action</label>
          </fieldset>
          <label class="switch"><input id="revealZones" type="checkbox" checked> Reveal recorded deck / Prizes</label>
        </div>
        <p id="zoneTiming" class="zone-timing"></p>
        <p id="zoneVisibility" class="zone-visibility"></p>
        <div class="zone-tabs" role="tablist" aria-label="Card zone">
          <button id="zone-deck" class="zone-tab" role="tab" aria-selected="true" aria-controls="zonePlayers" data-zone-tab="deck">Deck</button>
          <button id="zone-prize" class="zone-tab" role="tab" aria-selected="false" aria-controls="zonePlayers" tabindex="-1" data-zone-tab="prize">Prizes</button>
          <button id="zone-discard" class="zone-tab" role="tab" aria-selected="false" aria-controls="zonePlayers" tabindex="-1" data-zone-tab="discard">Discard</button>
        </div>
        <input id="zoneFilter" class="zone-filter" type="search" aria-label="Filter zone cards" placeholder="Filter cards">
        <div id="zonePlayers" class="zone-players" role="tabpanel" aria-labelledby="zone-deck"></div>
      </div></details>
      <div class="section">
        <div class="section-title"><h3>Turn changes</h3></div>
        <ul id="changes" class="changes"></ul>
      </div>
    </section>
    <aside>
      <div class="context-section"><div class="section-title"><h3>Board at snapshot</h3></div><div id="board"></div><div class="zone"><span class="zone-label">Stadium</span><div id="stadium" class="chips"></div></div></div>
      <div class="context-section"><div class="section-title"><h3>Card information</h3><a class="tag" href="../catalog/cards.json" target="_blank" title="Open local card catalog">Competition list</a></div><div id="cardDetail" class="card-detail"><span class="empty">Select a card name.</span></div></div>
    </aside>
  </main>
  <script id="replay-data" type="application/json">__REPLAY_DATA__</script>
  <script id="turn-data" type="application/json">__TURN_DATA__</script>
  <script id="card-data" type="application/json">__CARD_DATA__</script>
  <script id="review-meta" type="application/json">__REVIEW_META__</script>
  <script>
    const frames = JSON.parse(document.getElementById("replay-data").textContent);
    const turns = JSON.parse(document.getElementById("turn-data").textContent);
    const cardData = JSON.parse(document.getElementById("card-data").textContent);
    const $ = (id) => document.getElementById(id);
    let turnCursor = 0;
    let actionCursor = -1;
    let selectedCardId = null;
    let timer = null;
    let snapshotMoment = 'action';
    let selectedZone = 'deck';

    function esc(value) {
      return String(value == null ? "" : value).replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
    }
    function cardName(card) { return card && (card.name || (cardData[String(card.id)] || {}).name || `Card ${card.id}`); }
    function cardButton(card, compact=true) {
      if (!card) return "";
      const selected = Number(card.id) === Number(selectedCardId) ? " selected" : "";
      return `<button class="card-chip${selected}" data-card-id="${Number(card.id)}" title="Show card information">${esc(cardName(card))}</button>`;
    }
    function cardsLine(cards) {
      return cards && cards.length ? `<div class="chips">${cards.map((card) => cardButton(card)).join("")}</div>` : "";
    }
    function handPanels(hands, group) {
      const both = $("showBothHands").checked || group.actor === null;
      const indexes = both ? hands.map((_, index) => index) : [Number(group.actor || 0)];
      return indexes.map((index) => {
        const cards = hands[index] || [];
        return `<div class="hand-block"><span class="hand-label">Player ${index + 1} hand (${cards.length})</span>${cards.length ? cardsLine(cards) : `<span class="empty">Empty</span>`}</div>`;
      }).join("");
    }
    function eventDetails(details) {
      return (details || []).map((detail) => `<div class="effect"><div><span>${esc(detail.text)}</span>${cardsLine(detail.cards || [])}</div></div>`).join("");
    }
    function scoreBand(score) {
      const value = Number(score || 0);
      if (value >= 10000) return {label:"Critical", cls:"critical"};
      if (value >= 2500) return {label:"High", cls:"high"};
      if (value >= 500) return {label:"Medium", cls:"medium"};
      if (value >= 0) return {label:"Low", cls:"low"};
      return {label:"Blocked", cls:"blocked"};
    }
    function scoreText(score) {
      return Number(score || 0).toLocaleString(undefined, {maximumFractionDigits:1});
    }
    function scoreOptionName(option) {
      const source = option.attack_name || option.card_name || option.category || "Option";
      return option.target_name ? `${source} to ${option.target_name}` : source;
    }
    function thoughtPanel(action) {
      const thought = action.thought;
      if (!thought) return "";
      const chosen = new Set((action.selected || []).map(Number));
      const rows = (thought.options || []).slice().sort((a, b) => Number(b.score) - Number(a.score) || Number(a.index) - Number(b.index));
      const chosenRows = rows.filter((row) => chosen.has(Number(row.index)));
      const chosenScore = chosenRows.length ? Math.max(...chosenRows.map((row) => Number(row.score))) : null;
      const bestScore = rows.length ? Math.max(...rows.map((row) => Number(row.score))) : null;
      const band = scoreBand(chosenScore);
      const selectionText = chosenScore === null ? "Optional choice declined" : `Selected score ${scoreText(chosenScore)}`;
      const override = chosenScore !== null && bestScore !== null && chosenScore + 0.001 < bestScore
        ? `<p class="override-note">Sequencing override: another legal option had a higher numeric score (${scoreText(bestScore)}), but the state machine selected this action.</p>` : "";
      const expert = thought.expert_lesson ? `<p><strong>Expert rule:</strong> ${esc(thought.expert_lesson)}${thought.expert_reason ? `: ${esc(thought.expert_reason)}` : ""}</p>` : "";
      const tableRows = rows.map((row) => {
        const rowBand = scoreBand(row.score);
        const evidence = (row.evidence || []).length ? ` Evidence: ${(row.evidence || []).join("; ")}` : "";
        return `<div class="score-row ${chosen.has(Number(row.index)) ? "chosen" : ""}"><span class="score-cell">${row.index}${chosen.has(Number(row.index)) ? " *" : ""}</span><span class="score-cell">${esc(row.category)}</span><span class="score-cell">${esc(scoreOptionName(row))}</span><span class="score-cell score-value"><span class="score-band ${rowBand.cls}">${esc(scoreText(row.score))}</span></span><span class="score-cell">${esc((row.reason || "No reason emitted") + evidence)}</span></div>`;
      }).join("");
      return `<div class="thought"><div class="thought-head"><strong>Agent reasoning</strong><span class="score-band ${band.cls}">${esc(selectionText)}${chosenScore === null ? "" : ` | ${band.label}`}</span></div><p>${esc(thought.reason)}</p>${expert}${override}<details><summary>Compare all ${rows.length} legal-option scores</summary><div class="score-scroll"><div class="score-table"><div class="score-row heading"><span class="score-cell">Index</span><span class="score-cell">Category</span><span class="score-cell">Option</span><span class="score-cell score-value">Score</span><span class="score-cell">Why high or low</span></div>${tableRows}</div></div></details></div>`;
    }
    function engineDetails(action) {
      const source = frames[action.frame] || {};
      const result = frames[action.result_frame] || {};
      return esc(JSON.stringify({ selection: source.select || {}, selected_indexes: result.selected || [], result_logs: result.logs || [] }, null, 2));
    }
    function renderTurnList() {
      $("turnList").innerHTML = turns.map((turn, index) => `<button class="turn-button ${index === turnCursor ? "current" : ""}" data-turn-index="${index}"><strong>${esc(turn.label)}</strong><span>${turn.actions.length} actions</span></button>`).join("");
    }
    function renderProcedure() {
      const group = turns[turnCursor];
      if (!group) {
        $("turnTitle").textContent = "No turn data";
        $("actions").innerHTML = "";
        return;
      }
      $("turnTitle").textContent = group.label;
      $("turnSubtitle").textContent = group.moment === "setup" ? "Opening choices and board setup" : group.moment === "response" ? `Forced response by Player ${Number(group.actor) + 1}` : `Player ${Number(group.actor) + 1} procedure`;
      $("startTitle").textContent = group.actor === null ? "Opening hands" : "Start of turn";
      $("startTag").textContent = group.actor === null ? "After opening draw" : "After draw";
      $("position").textContent = `${turnCursor + 1} / ${turns.length} turns`;
      $("actionCount").textContent = `${group.actions.length} actions`;
      $("startNotes").innerHTML = group.start_notes.length ? `<ul class="start-notes">${group.start_notes.map((note) => `<li>${esc(note.text)}${cardsLine(note.cards || [])}</li>`).join("")}</ul>` : "";
      $("startHands").innerHTML = handPanels(group.start_hands || [], group);
      $("endHands").innerHTML = handPanels(group.end_hands || [], group);
      $("changes").innerHTML = (group.changes || []).map((change) => `<li>${esc(change)}</li>`).join("");
      $("actions").innerHTML = group.actions.map((action, index) => `
        <li class="action ${index === actionCursor ? "current" : ""}">
          <span class="action-number">${action.number}</span>
          <div class="action-main">
            <button class="action-jump" data-action-index="${index}">${esc(action.title)}</button>
            <span class="action-context">Player ${Number(action.actor) + 1} | ${esc(action.context)}</span>
            ${cardsLine(action.cards || [])}
            ${thoughtPanel(action)}
            <div class="effects">${eventDetails(action.details)}</div>
            ${reviewPanel(action)}
            <details><summary>Engine details</summary><pre>${engineDetails(action)}</pre></details>
          </div>
        </li>`).join("") || `<li class="empty">No recorded actions.</li>`;
      syncReviewPanels();
    }
    function pokemonCard(card) {
      if (!card) return "";
      const maxHp = Number(card.maxHp || 0);
      const hp = Number(card.hp || 0);
      const ratio = maxHp ? Math.max(0, Math.min(100, 100 * hp / maxHp)) : 100;
      const energy = (card.energyCards || []).map(cardName);
      const tools = (card.tools || []).map(cardName);
      const attached = [energy.length ? `Energy: ${energy.join(", ")}` : "", tools.length ? `Tool: ${tools.join(", ")}` : ""].filter(Boolean).join(" | ");
      return `<button class="pokemon" data-card-id="${Number(card.id)}"><strong>${esc(cardName(card))}</strong><span>${hp}/${maxHp} HP</span><span class="hp"><i class="${ratio <= 35 ? "low" : ""}" style="width:${ratio}%"></i></span>${attached ? `<span>${esc(attached)}</span>` : ""}</button>`;
    }
    function boardPlayer(player, index, actor) {
      const active = player.active || [];
      const bench = player.bench || [];
      return `<div class="board-player ${index === actor ? "acting" : ""}">
        <div class="board-player-head"><h3>Player ${index + 1}</h3><span class="stats">Hand ${player.handCount || 0} | Deck ${player.deckCount || 0} | Prizes ${(player.prize || []).length}</span></div>
        <div class="zone"><span class="zone-label">Active</span>${active.length ? active.map(pokemonCard).join("") : `<span class="empty">Empty</span>`}</div>
        <div class="zone"><span class="zone-label">Bench</span><div class="bench">${bench.length ? bench.map(pokemonCard).join("") : `<span class="empty">Empty</span>`}</div></div>
      </div>`;
    }
    function selectedFrameIndex() {
      const group = turns[turnCursor] || {};
      if (snapshotMoment === 'start') return Number(group.start_frame || 0);
      if (snapshotMoment === 'end') return Number(group.result_frame || group.start_frame || 0);
      const action = (group.actions || [])[actionCursor];
      return action ? Number(action.result_frame) : Number(group.start_frame || 0);
    }
    function zoneSnapshot(player, zone) {
      const source = player && Array.isArray(player[zone]) ? player[zone] : null;
      const rawCount = player && player[`${zone}Count`];
      const count = Number.isInteger(rawCount) && rawCount >= 0 ? rawCount : source ? source.length : null;
      const entries = (source || []).map(card => {
        if (!card || typeof card !== 'object') return null;
        const id = Number.isInteger(card.id) && card.id > 0 ? card.id : null;
        const name = (typeof card.name === 'string' && card.name) || (id !== null && (cardData[String(id)] || {}).name) || (id !== null ? `Card ${id}` : '');
        return name ? {id, name, serial:card.serial} : null;
      });
      const known = entries.filter(Boolean).length;
      return {count, entries, known, unknown:count === null ? null : Math.max(0, count - known),
              inconsistent:count !== null && entries.length > count};
    }
    function inventoryRows(snapshot, zone, reveal) {
      if (zone === 'prize') {
        return Array.from({length:Math.max(snapshot.entries.length, Math.min(snapshot.count || 0, 200))}, (_, index) => {
          const card = reveal ? snapshot.entries[index] : null;
          return {card, name:card ? card.name : reveal ? 'Unknown Prize card' : 'Face-down Prize card', suffix:`Slot ${index + 1}`};
        });
      }
      if (zone === 'deck' && !reveal) return [];
      const groups = new Map();
      for (const card of snapshot.entries.filter(Boolean)) {
        const key = card.id !== null ? `id:${card.id}` : `name:${card.name}`;
        if (!groups.has(key)) groups.set(key, {card, name:card.name, count:0});
        groups.get(key).count += 1;
      }
      return [...groups.values()].sort((a,b) => a.name.localeCompare(b.name) || (a.card.id || 0) - (b.card.id || 0))
        .map(row => ({...row, suffix:`x${row.count}`}));
    }
    function renderCardZones() {
      const frameIndex = Math.max(0, Math.min(selectedFrameIndex(), Math.max(0, frames.length - 1)));
      const current = (frames[frameIndex] || {}).current || {};
      const group = turns[turnCursor] || {};
      const action = (group.actions || [])[actionCursor];
      const timing = snapshotMoment === 'end' ? 'After final action' : snapshotMoment === 'start' || !action ? 'Turn start' : `After action ${action.number}`;
      const crossedTurn = Number(current.turn) > Number(group.turn);
      $('zoneFrame').textContent = frames.length ? `Frame ${frameIndex + 1}` : 'No snapshot';
      $('zoneTiming').textContent = `${timing} | Recorded turn ${current.turn ?? '?'}${crossedTurn ? ' | Next-turn prompt; its opening draw may already be included.' : ''}`;
      document.querySelectorAll('[name="snapshotMoment"]').forEach(input => { input.checked = input.value === snapshotMoment; });
      const reveal = $('revealZones').checked;
      $('zoneVisibility').textContent = reveal ? 'Full replay information, not agent knowledge. Missing identities remain unknown.' : 'Deck and Prize identities concealed in this view.';
      document.querySelectorAll('[data-zone-tab]').forEach(tab => {
        const active = tab.dataset.zoneTab === selectedZone;
        tab.setAttribute('aria-selected', String(active)); tab.tabIndex = active ? 0 : -1;
      });
      $('zonePlayers').setAttribute('aria-labelledby', `zone-${selectedZone}`);
      const filter = $('zoneFilter').value.trim().toLowerCase();
      const players = Array.isArray(current.players) ? current.players : [];
      const zoneName = {deck:'Deck', prize:'Prizes', discard:'Discard'}[selectedZone];
      $('zonePlayers').innerHTML = [0,1].map(index => {
        const player = players[index] || {};
        const snapshots = Object.fromEntries(['deck','prize','discard'].map(zone => [zone, zoneSnapshot(player,zone)]));
        const snapshot = snapshots[selectedZone];
        const rows = inventoryRows(snapshot,selectedZone,reveal).filter(row => row.name.toLowerCase().includes(filter));
        const emptyText = selectedZone === 'deck' && !reveal ? 'Deck contents concealed.' : snapshot.count === 0 ? 'Empty' : filter ? 'No matching cards' : 'Card identities not recorded.';
        const rendered = rows.map(row => `<li class="zone-row">${row.card && row.card.id !== null ? `<button data-card-id="${row.card.id}" title="Show card information">${esc(row.name)}</button>` : `<span>${esc(row.name)}</span>`}<span class="zone-quantity">${esc(row.suffix)}</span></li>`).join('');
        const counts = Object.entries(snapshots).map(([zone, value]) => `${{deck:'Deck', prize:'Prizes', discard:'Discard'}[zone]} ${value.count ?? '?'}`).join(' | ');
        const unavailable = snapshot.count === null ? 'Zone count not recorded.' : snapshot.unknown && (reveal || selectedZone === 'discard') ? `${snapshot.unknown} card identities not recorded.` : '';
        return `<section class="zone-player" data-zone-player="${index}"><div class="zone-player-head"><h3>Player ${index + 1}</h3><span class="zone-totals">${zoneName}: ${snapshot.count ?? '?'}</span></div><p class="zone-totals">${counts}</p>
          <ul class="zone-inventory" aria-label="Player ${index + 1} ${zoneName}">${rendered || `<li class="zone-row empty">${emptyText}</li>`}</ul>
          <p class="zone-missing">${esc(unavailable)}${snapshot.inconsistent ? ' Recorded list and count differ.' : ''}</p></section>`;
      }).join('');
    }
    function renderBoard() {
      const frameIndex = Math.max(0, Math.min(selectedFrameIndex(), Math.max(0, frames.length - 1)));
      const frame = frames[frameIndex] || {};
      const current = frame.current || {};
      const players = current.players || [];
      $("framePosition").textContent = `Frame ${frameIndex + 1} / ${frames.length}`;
      $("board").innerHTML = players.map((player, index) => boardPlayer(player, index, Number(current.yourIndex))).join("");
      $("stadium").innerHTML = (current.stadium || []).length ? (current.stadium || []).map(cardButton).join("") : `<span class="empty">None</span>`;
      const result = Number(current.result);
      const group = turns[turnCursor] || {};
      $("matchStatus").textContent = result === -1 ? (group.actor === null ? "Setup" : `Turn ${current.turn || 0}`) : result === 2 ? "Draw" : `Player ${result + 1} wins`;
      $("matchStatus").className = result === -1 ? "status" : "status winner";
    }
    function renderCardDetail() {
      const card = cardData[String(selectedCardId)] || null;
      if (!card) {
        $("cardDetail").innerHTML = `<span class="empty">Select a card name.</span>`;
        return;
      }
      const rows = [
        ["Card ID", card.id], ["Set", [card.set, card.number].filter(Boolean).join(" ")], ["Type", card.type],
        ["Stage", card.stage], ["HP", card.hp], ["Evolves from", card.previous_stage], ["Retreat", card.retreat],
        ["Weakness", card.weakness], ["Resistance", card.resistance], ["Rule", card.rule]
      ].filter((row) => row[1] !== null && row[1] !== undefined && String(row[1]) !== "" && String(row[1]).toLowerCase() !== "n/a");
      const moves = (card.moves || []).map((move) => `<div class="move"><strong>${esc(move.name)}</strong><span>${esc([move.cost ? `Cost ${move.cost}` : "", move.damage && move.damage !== "n/a" ? `Damage ${move.damage}` : ""].filter(Boolean).join(" | "))}</span>${move.effect ? `<p>${esc(move.effect)}</p>` : ""}</div>`).join("");
      $("cardDetail").innerHTML = `<h2>${esc(card.name)}</h2><dl>${rows.map((row) => `<dt>${esc(row[0])}</dt><dd>${esc(row[1])}</dd>`).join("")}</dl>${moves}`;
    }
    function render() {
      renderTurnList();
      renderProcedure();
      renderBoard();
      renderCardZones();
      renderCardDetail();
      $("prevTurn").disabled = turnCursor <= 0;
      $("nextTurn").disabled = turnCursor >= turns.length - 1;
    }
    function stop() {
      if (timer) clearInterval(timer);
      timer = null;
      $("play").innerHTML = `__ICON_play__`;
      $("play").setAttribute("aria-label", "Play actions");
      $("play").title = "Play actions";
    }
    function goTurn(index) {
      stop();
      turnCursor = Math.max(0, Math.min(Number(index), Math.max(0, turns.length - 1)));
      actionCursor = -1;
      render();
    }
    function goAction(index) {
      stop();
      actionCursor = Number(index);
      snapshotMoment = 'action';
      render();
    }
    function playNext() {
      snapshotMoment = 'action';
      const actions = (turns[turnCursor] || {}).actions || [];
      if (actionCursor < actions.length - 1) actionCursor += 1;
      else if (turnCursor < turns.length - 1) { turnCursor += 1; actionCursor = -1; }
      else stop();
      render();
    }
    $("prevTurn").onclick = () => goTurn(turnCursor - 1);
    $("nextTurn").onclick = () => goTurn(turnCursor + 1);
    $("showBothHands").onchange = render;
    $('revealZones').onchange = renderCardZones;
    $('zoneFilter').oninput = renderCardZones;
    document.querySelectorAll('[name="snapshotMoment"]').forEach(input => { input.onchange = () => {
      stop(); snapshotMoment = input.value; renderBoard(); renderCardZones();
    }; });
    document.querySelectorAll('[data-zone-tab]').forEach((tab, index, tabs) => {
      tab.onclick = () => { selectedZone = tab.dataset.zoneTab; renderCardZones(); };
      tab.onkeydown = event => {
        let next;
        if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
        else if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length;
        else if (event.key === 'Home') next = 0;
        else if (event.key === 'End') next = tabs.length - 1;
        else return;
        event.preventDefault(); tabs[next].click(); tabs[next].focus();
      };
    });
    $("play").onclick = () => {
      if (timer) { stop(); return; }
      $("play").innerHTML = `__ICON_pause__`;
      $("play").setAttribute("aria-label", "Pause actions");
      $("play").title = "Pause actions";
      timer = setInterval(playNext, Number($("playbackSpeed").value));
    };
    $("playbackSpeed").onchange = () => { if (timer) { clearInterval(timer); timer = setInterval(playNext, Number($("playbackSpeed").value)); } };
    document.addEventListener("click", (event) => {
      const turnButton = event.target.closest("[data-turn-index]");
      if (turnButton) { goTurn(turnButton.dataset.turnIndex); return; }
      const actionButton = event.target.closest("[data-action-index]");
      if (actionButton) { goAction(actionButton.dataset.actionIndex); return; }
      const card = event.target.closest("[data-card-id]");
      if (card) { selectedCardId = Number(card.dataset.cardId); renderCardDetail(); }
    });
    __REVIEW_JS__
    render();
  </script>
</body>
</html>
"""

OFFICIAL_REPLAY_HTML = decorate_page(OFFICIAL_REPLAY_HTML, "replay")
