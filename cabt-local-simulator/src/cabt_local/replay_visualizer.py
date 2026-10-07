from __future__ import annotations

import json
import re
from copy import deepcopy
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable


TURN_RE = re.compile(r"^(?P<player>.+?)'s Turn$")
OPENING_HAND_RE = re.compile(r"^(?P<player>.+?) drew (?P<count>\d+) cards for the opening hand\.$")
DRAW_RE = re.compile(r"^(?P<player>.+?) drew (?P<card>.+?)\.$")
PLAY_ACTIVE_RE = re.compile(r"^(?P<player>.+?) played (?P<card>.+?) to the Active Spot\.$")
PLAY_BENCH_RE = re.compile(r"^(?P<player>.+?) played (?P<card>.+?) to the Bench\.$")
PLAY_CARD_RE = re.compile(r"^(?P<player>.+?) played (?P<card>.+?)\.$")
ATTACH_RE = re.compile(r"^(?P<player>.+?) attached (?P<card>.+?) to (?P<target>.+?)\.$")
EVOLVE_RE = re.compile(r"^(?P<player>.+?) evolved (?P<source>.+?) to (?P<dest>.+?)(?: (?P<where>on the Bench|in the Active Spot))?\.$")
RETREAT_RE = re.compile(r"^(?P<player>.+?) retreated (?P<card>.+?) to the Bench\.$")
NEW_ACTIVE_RE = re.compile(r"^(?P<player>.+?)'s (?P<card>.+?) is now in the Active Spot\.$")
USED_RE = re.compile(r"^(?P<player>.+?)'s (?P<card>.+?) used (?P<name>.+?)(?: on (?P<target>.+?) for (?P<damage>\d+) damage)?\.$")
KO_RE = re.compile(r"^(?P<target>.+?) was Knocked Out!$")
PRIZE_RE = re.compile(r"^(?P<player>.+?) took a Prize card\.$")
PRIZES_RE = re.compile(r"^(?P<player>.+?) took (?P<count>\d+) Prize cards\.$")
HAND_ADD_RE = re.compile(r"^(?P<card>.+?) was added to (?P<player>.+?)'s hand\.$")
HIDDEN_HAND_ADD_RE = re.compile(r"^A card was added to (?P<player>.+?)'s hand\.$")
TURN_END_RE = re.compile(r"^(?P<player>.+?) ended their turn\.$")
TIMEOUT_RE = re.compile(r"^(?P<player>.+?) didn't take an action in time\.$")
ACTIVATED_RE = re.compile(r"^(?P<card>.+?) was activated\.$")
MULLIGAN_RE = re.compile(r"^(?P<player>.+?) took a mulligan\.$")
COIN_CALL_RE = re.compile(r"^(?P<player>.+?) chose (?P<choice>heads|tails) for the opening coin flip\.$", re.I)
COIN_WIN_RE = re.compile(r"^(?P<player>.+?) won the coin toss\.$")
FIRST_RE = re.compile(r"^(?P<player>.+?) decided to go (?P<choice>first|second)\.$", re.I)
STADIUM_RE = re.compile(r"^(?P<player>.+?) played (?P<card>.+?) to the Stadium spot\.$")
DIRECT_DISCARD_RE = re.compile(r"^(?P<card>.+?) was discarded from (?P<target>.+?)\.$")
WIN_RE = re.compile(r"^(?:(?:Opponent conceded|.+?Prize cards|No Benched Pok[eé]mon for backup|.+?Pok[eé]mon in play).+? )?(?P<player>[^.]+?) wins\.$")
DISCARD_RE = re.compile(r"^- (?P<player>.+?) (?:moved|discarded) (?P<count>\d+|a) cards? to the discard pile\.$")
SWITCH_DETAIL_RE = re.compile(r"^- (?P<player>.+?)'s (?P<to>.+?) was switched with (?P=player)'s (?P<from>.+?) to become the Active Pok[eé]mon\.$")
MOVE_TO_BENCH_RE = re.compile(r"^- (?P<player>.+?) moved (?P=player)'s (?P<card>.+?) to the Bench\.$")
MOVE_TO_DECK_RE = re.compile(r"^- (?P<player>.+?) moved (?P=player)'s (?P<card>.+?) to their deck\.$")
DAMAGE_RE = re.compile(r"^- (?:(?P<player>.+?)'s )?(?P<card>.+?) took (?P<damage>\d+) damage\.$")
DAMAGE_COUNTER_RE = re.compile(r"^- (?P<player>.+?) put (?P<count>\d+|a) damage counters? on (?P<target>.+?)\.$")
CONDITION_RE = re.compile(r"^- (?P<target>.+?) is now (?P<condition>Poisoned|Burned|Asleep|Paralyzed|Confused)\.$", re.I)
CHECKUP_DAMAGE_RE = re.compile(r"^(?P<count>\d+|A) damage counters? was placed on (?P<target>.+?) for the Special Condition (?P<condition>.+?)\.$", re.I)
DETAIL_DRAW_RE = re.compile(r"^- (?P<player>.+?) drew (?P<value>.+?)\.$")
DETAIL_ATTACH_RE = re.compile(r"^- (?P<player>.+?) attached (?P<card>.+?) to (?P<target>.+?)\.$")
DETAIL_MOVE_HAND_RE = re.compile(r"^- (?P<player>.+?) moved (?:(?P=player)'s )?(?P<card>.+?) to their hand\.$")
DETAIL_DISCARD_ONE_RE = re.compile(r"^- (?P<player>.+?) discarded (?P<card>.+?)\.$")
DETAIL_DISCARD_FROM_RE = re.compile(r"^- (?P<card>.+?) (?:was|were) discarded from (?P<target>.+?)\.$")


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.ignored_depth += 1
        elif not self.ignored_depth and tag in {"br", "p", "div", "li", "pre", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.ignored_depth:
            self.ignored_depth -= 1
        elif not self.ignored_depth and tag in {"p", "div", "li", "pre", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.ignored_depth:
            self.parts.append(data)

    def text(self) -> str:
        return "".join(self.parts)


@dataclass
class ReplayEvent:
    index: int
    turn: str
    player: str
    action: str
    card: str
    target: str
    detail: str
    raw: str
    tags: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_battle_log(text: str) -> dict[str, Any]:
    text = extract_log_text(text)
    events: list[ReplayEvent] = []
    snapshots: list[dict[str, Any]] = []
    unparsed_lines: list[dict[str, Any]] = []
    board = empty_board()
    current_turn = "Setup"
    current_player = ""
    pending_event: ReplayEvent | None = None

    meaningful_lines = 0
    parsed_lines = 0
    detail_lines = 0
    for line_number, raw in enumerate(text.splitlines(), start=1):
        line = normalize_line(raw)
        if not line:
            continue
        meaningful_lines += 1
        if line == "Setup" or re.fullmatch(r"log\d+:Setup", line, re.I):
            current_turn = "Setup"
            current_player = ""
            pending_event = add_event(events, snapshots, board, current_turn, "", "SETUP", "", "", "", line, ["setup"])
            parsed_lines += 1
            continue
        if line == "Pokémon Checkup" or line == "Pokemon Checkup":
            current_turn = "Pokémon Checkup"
            pending_event = add_event(events, snapshots, board, current_turn, "", "CHECKUP", "", "", "", line, ["checkup"])
            parsed_lines += 1
            continue
        turn_match = TURN_RE.match(line)
        if turn_match:
            current_player = turn_match.group("player")
            current_turn = line
            ensure_player(board, current_player)
            pending_event = add_event(events, snapshots, board, current_turn, current_player, "TURN_START", "", "", "", line, ["turn"])
            parsed_lines += 1
            continue
        if is_detail_line(line):
            detail_lines += 1
            if pending_event is not None:
                pending_event.detail = append_detail(pending_event.detail, line)
                update_from_detail(board, pending_event, line)
                snapshots[-1] = snapshot(board, pending_event.index)
                parsed_lines += 1
            else:
                unparsed_lines.append({"line": line_number, "text": line, "reason": "detail without parent event"})
            continue

        event = classify_log_line(line, current_turn, current_player)
        apply_event(board, event)
        pending_event = event
        events.append(event)
        snapshots.append(snapshot(board, event.index))
        if event.action == "UNKNOWN":
            unparsed_lines.append({"line": line_number, "text": line, "reason": "no parser rule"})
        else:
            parsed_lines += 1

    coverage_percent = round(100.0 * parsed_lines / meaningful_lines, 1) if meaningful_lines else 100.0
    return {
        "ok": True,
        "source": "battle_log_text",
        "summary": summarize(events, board),
        "coverage": {
            "meaningful_lines": meaningful_lines,
            "parsed_lines": parsed_lines,
            "detail_lines": detail_lines,
            "unparsed_lines": len(unparsed_lines),
            "percent": coverage_percent,
        },
        "unparsed_lines": unparsed_lines,
        "events": [event.to_dict() for event in events],
        "snapshots": snapshots,
    }


def extract_log_text(text: str) -> str:
    if not re.search(r"<\s*(?:!doctype|html|body|pre|div|p|br)\b", text, re.I):
        return text
    parser = _VisibleTextParser()
    try:
        parser.feed(text)
        visible = parser.text()
    except Exception:
        return text
    lines = [line.strip() for line in visible.splitlines() if line.strip()]
    return "\n".join(lines) if lines else text


def episode_payload_from_path(path: str | Path) -> dict[str, Any]:
    rows = []
    for line_no, line in enumerate(Path(path).read_text(encoding="utf-8-sig").splitlines(), start=1):
        text = line.strip()
        if not text:
            continue
        try:
            rows.append(json.loads(text))
        except json.JSONDecodeError as exc:
            return {"ok": False, "error": f"{path}:{line_no}: invalid JSONL row: {exc}"}
    return episode_payload(rows, source=str(path))


def episode_payload(rows: Iterable[dict[str, Any]], source: str = "episode_jsonl") -> dict[str, Any]:
    decisions = []
    for idx, row in enumerate(rows):
        obs = row.get("observation") or {}
        current = obs.get("current") or {}
        select = obs.get("select") or {}
        logs = obs.get("logs") or []
        features = row.get("features") or {}
        legal = row.get("legal_options") or (select.get("option") if isinstance(select, dict) else []) or []
        selected = row.get("selected_indexes") or []
        decisions.append(
            {
                "index": idx,
                "turn": row.get("turn", features.get("turn", 0)),
                "player": row.get("player", features.get("acting_player", "")),
                "deck_id": row.get("deck_id", ""),
                "agent_id": row.get("agent_id", ""),
                "features": features,
                "logs": logs,
                "legal_options": legal,
                "selected_indexes": selected,
                "selected_options": row.get("selected_options") or select_by_index(legal, selected),
                "current": compact_current(current),
            }
        )
    return {
        "ok": True,
        "source": source,
        "summary": {
            "decisions": len(decisions),
            "turns": sorted({str(decision["turn"]) for decision in decisions}),
            "players": sorted({str(decision["player"]) for decision in decisions}),
        },
        "decisions": decisions,
    }


def normalize_line(raw: str) -> str:
    text = raw.strip()
    while text.startswith(" "):
        text = text[1:]
    return text.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')


def classify_log_line(line: str, current_turn: str, current_player: str) -> ReplayEvent:
    checkup_damage = CHECKUP_DAMAGE_RE.match(line)
    if checkup_damage:
        data = checkup_damage.groupdict()
        return ReplayEvent(
            -1,
            current_turn,
            owner_from_target(data["target"]),
            "CHECKUP_DAMAGE",
            clean_card(data["target"]),
            "",
            str(10 * parse_count(data["count"], 1)),
            line,
            ["checkup", "damage"],
        )
    patterns = [
        (OPENING_HAND_RE, "OPENING_HAND", ["setup", "draw"]),
        (COIN_CALL_RE, "COIN_CALL", ["setup"]),
        (COIN_WIN_RE, "COIN_WIN", ["setup"]),
        (FIRST_RE, "GO_FIRST_SECOND", ["setup"]),
        (MULLIGAN_RE, "MULLIGAN", ["setup"]),
        (TURN_END_RE, "TURN_END", ["turn"]),
        (TIMEOUT_RE, "TIMEOUT", ["timeout"]),
        (ACTIVATED_RE, "ACTIVATE_EFFECT", ["effect"]),
        (DRAW_RE, "DRAW", ["draw"]),
        (PLAY_ACTIVE_RE, "PLAY_ACTIVE", ["board"]),
        (PLAY_BENCH_RE, "PLAY_BENCH", ["bench"]),
        (ATTACH_RE, "ATTACH_ENERGY", ["energy"]),
        (EVOLVE_RE, "EVOLVE", ["evolve"]),
        (RETREAT_RE, "RETREAT", ["switch"]),
        (NEW_ACTIVE_RE, "NEW_ACTIVE", ["switch"]),
        (USED_RE, "USE_ATTACK_OR_ABILITY", ["use"]),
        (PRIZES_RE, "PRIZE", ["prize"]),
        (PRIZE_RE, "PRIZE", ["prize"]),
        (HIDDEN_HAND_ADD_RE, "ADD_TO_HAND_HIDDEN", ["hand", "hidden"]),
        (HAND_ADD_RE, "ADD_TO_HAND", ["hand"]),
        (STADIUM_RE, "PLAY_STADIUM", ["stadium"]),
        (DIRECT_DISCARD_RE, "DISCARD_ATTACHED", ["discard"]),
        (WIN_RE, "WIN", ["terminal"]),
        (PLAY_CARD_RE, "PLAY_CARD", ["trainer"]),
    ]
    idx = -1
    for pattern, action, tags in patterns:
        match = pattern.match(line)
        if not match:
            continue
        data = match.groupdict()
        card = data.get("card") or data.get("dest") or data.get("name") or data.get("choice") or ""
        raw_target = data.get("target") or data.get("source") or ""
        target = raw_target if action == "DISCARD_ATTACHED" else clean_card(raw_target)
        detail = data.get("where") or data.get("count") or ""
        if data.get("damage"):
            detail = f"{data['damage']} damage"
            tags = [*tags, "damage"]
        return ReplayEvent(idx, current_turn, data.get("player") or current_player, action, clean_card(card), target, detail, line, tags)
    ko = KO_RE.match(line)
    if ko:
        raw_target = ko.group("target")
        player = owner_from_target(raw_target)
        return ReplayEvent(idx, current_turn, player, "KNOCKOUT", clean_card(raw_target), "", "", line, ["ko"])
    discard = DISCARD_RE.match(line)
    if discard:
        return ReplayEvent(idx, current_turn, discard.group("player"), "DISCARD", "", "", discard.group("count"), line, ["discard"])
    return ReplayEvent(idx, current_turn, current_player, "UNKNOWN", "", "", "", line, ["unknown"])


def add_event(
    events: list[ReplayEvent],
    snapshots: list[dict[str, Any]],
    board: dict[str, Any],
    turn: str,
    player: str,
    action: str,
    card: str,
    target: str,
    detail: str,
    raw: str,
    tags: list[str],
) -> ReplayEvent:
    event = ReplayEvent(len(events), turn, player, action, card, target, detail, raw, tags)
    apply_event(board, event)
    events.append(event)
    snapshots.append(snapshot(board, event.index))
    return event


def apply_event(board: dict[str, Any], event: ReplayEvent) -> None:
    event.index = board["event_index"]
    board["event_index"] += 1
    if event.player:
        ensure_player(board, event.player)
    if event.action == "PLAY_ACTIVE":
        set_active(board, event.player, event.card)
        consume_hand_card(board, event.player, event.card)
    elif event.action == "PLAY_BENCH":
        add_bench(board, event.player, event.card)
        consume_hand_card(board, event.player, event.card)
    elif event.action == "EVOLVE":
        evolve_card(board, event.player, event.target, event.card, event.detail)
        consume_hand_card(board, event.player, event.card)
    elif event.action == "ATTACH_ENERGY":
        attach_energy(board, event.player, event.card, event.target)
        consume_hand_card(board, event.player, event.card)
    elif event.action == "RETREAT":
        move_active_to_bench(board, event.player, event.card)
    elif event.action == "NEW_ACTIVE":
        promote_active(board, event.player, event.card)
    elif event.action == "KNOCKOUT":
        remove_knocked_out(board, event.player, event.card)
    elif event.action == "PRIZE":
        player = ensure_player(board, event.player)
        player["prizes_taken"] += parse_count(event.detail, 1)
    elif event.action == "OPENING_HAND":
        ensure_player(board, event.player)["hand_count"] = parse_count(event.detail, 7)
    elif event.action == "DRAW":
        player = ensure_player(board, event.player)
        player["hand_count"] += 1
        player["hand_known"].append(event.card)
    elif event.action == "ADD_TO_HAND":
        player = ensure_player(board, event.player)
        player["hand_count"] += 1
        player["hand_known"].append(event.card)
    elif event.action == "ADD_TO_HAND_HIDDEN":
        ensure_player(board, event.player)["hand_count"] += 1
    elif event.action == "PLAY_STADIUM":
        board["stadium"] = event.card
        consume_hand_card(board, event.player, event.card)
    elif event.action == "PLAY_CARD":
        consume_hand_card(board, event.player, event.card)
    elif event.action == "DISCARD_ATTACHED":
        discard_attachment(board, event.target, event.card)
    elif event.action == "TURN_START":
        board["current_player"] = event.player
        board["turn_number"] += 1
    elif event.action == "TURN_END":
        board["current_player"] = ""
    elif event.action == "TIMEOUT":
        board["timeouts"] += 1
    elif event.action == "CHECKUP_DAMAGE":
        add_damage(board, event.player, event.card, parse_count(event.detail, 10))
    elif event.action == "WIN":
        board["winner"] = event.player


def empty_board() -> dict[str, Any]:
    return {
        "event_index": 0,
        "players": {},
        "winner": "",
        "stadium": "",
        "current_player": "",
        "turn_number": 0,
        "timeouts": 0,
    }


def ensure_player(board: dict[str, Any], name: str) -> dict[str, Any]:
    if not name:
        name = "Unknown"
    players = board.setdefault("players", {})
    return players.setdefault(
        name,
        {
            "active": "",
            "bench": [],
            "attachments": {},
            "damage": {},
            "conditions": {},
            "prizes_taken": 0,
            "hand_count": 0,
            "hand_known": [],
            "discard_known": [],
        },
    )


def set_active(board: dict[str, Any], player_name: str, card: str) -> None:
    player = ensure_player(board, player_name)
    player["active"] = card
    remove_one(player["bench"], card)


def add_bench(board: dict[str, Any], player_name: str, card: str) -> None:
    player = ensure_player(board, player_name)
    if len(player["bench"]) < 5:
        player["bench"].append(card)


def evolve_card(board: dict[str, Any], player_name: str, source: str, dest: str, where: str = "") -> None:
    player = ensure_player(board, player_name)
    prefer_bench = "bench" in where.lower()
    prefer_active = "active" in where.lower()
    if not prefer_bench:
        if source and same_name(player["active"], source):
            player["active"] = dest
            move_attachments(player, source, dest)
            return
    if not prefer_active:
        for idx, card in enumerate(player["bench"]):
            if same_name(card, source):
                player["bench"][idx] = dest
                if not same_name(player["active"], source):
                    move_attachments(player, source, dest)
                return
    if prefer_bench and source and same_name(player["active"], source):
        player["active"] = dest
        move_attachments(player, source, dest)
        return
    add_bench(board, player_name, dest)


def attach_energy(board: dict[str, Any], player_name: str, energy: str, target: str) -> None:
    player = ensure_player(board, player_name)
    clean_target = strip_owner(target)
    attachments = player.setdefault("attachments", {})
    attachments.setdefault(clean_target, []).append(energy)


def move_active_to_bench(board: dict[str, Any], player_name: str, card: str) -> None:
    player = ensure_player(board, player_name)
    if same_name(player["active"], card):
        if len(player["bench"]) < 5:
            player["bench"].append(player["active"])
        player["active"] = ""


def promote_active(board: dict[str, Any], player_name: str, card: str) -> None:
    player = ensure_player(board, player_name)
    remove_one(player["bench"], card)
    player["active"] = card


def remove_knocked_out(board: dict[str, Any], owner: str, target: str) -> None:
    owner_name = owner or owner_from_target(target)
    card = strip_owner(target)
    player = ensure_player(board, owner_name)
    if same_name(player["active"], card):
        player["active"] = ""
        player["attachments"].pop(card, None)
        player["damage"].pop(card, None)
        player["conditions"].pop(card, None)
        return
    remove_one(player["bench"], card)


def update_from_detail(board: dict[str, Any], event: ReplayEvent, line: str) -> bool:
    switch = SWITCH_DETAIL_RE.match(line)
    if switch:
        switch_active(board, switch.group("player"), switch.group("from"), switch.group("to"))
        return True
    moved_bench = MOVE_TO_BENCH_RE.match(line)
    if moved_bench:
        add_bench(board, moved_bench.group("player"), clean_card(moved_bench.group("card")))
        return True
    moved_deck = MOVE_TO_DECK_RE.match(line)
    if moved_deck:
        remove_from_field(board, moved_deck.group("player"), moved_deck.group("card"))
        return True
    damage = DAMAGE_RE.match(line)
    if damage:
        add_damage(board, damage.group("player") or owner_from_target(damage.group("card")), damage.group("card"), int(damage.group("damage")))
        return True
    counters = DAMAGE_COUNTER_RE.match(line)
    if counters:
        add_damage(board, counters.group("player"), counters.group("target"), 10 * parse_count(counters.group("count"), 1))
        return True
    condition = CONDITION_RE.match(line)
    if condition:
        set_condition(board, owner_from_target(condition.group("target")), condition.group("target"), condition.group("condition"))
        return True
    discard_from = DETAIL_DISCARD_FROM_RE.match(line)
    if discard_from:
        card_name = clean_card(discard_from.group("card"))
        if not re.match(r"^(?:\d+|a) cards?$", card_name, re.I):
            discard_attachment(board, discard_from.group("target"), card_name)
        return True
    detail_attach = DETAIL_ATTACH_RE.match(line)
    if detail_attach:
        attach_energy(board, detail_attach.group("player"), detail_attach.group("card"), detail_attach.group("target"))
        return True
    detail_move_hand = DETAIL_MOVE_HAND_RE.match(line)
    if detail_move_hand:
        player = ensure_player(board, detail_move_hand.group("player"))
        player["hand_count"] += 1
        player["hand_known"].append(clean_card(detail_move_hand.group("card")))
        return True
    detail_draw = DETAIL_DRAW_RE.match(line)
    if detail_draw:
        value = detail_draw.group("value")
        player = ensure_player(board, detail_draw.group("player"))
        count_match = re.match(r"(?P<count>\d+) cards?(?: and played them to the Bench)?$", value)
        if count_match:
            if "played them to the Bench" not in value:
                player["hand_count"] += int(count_match.group("count"))
        elif value.lower() != "a card":
            player["hand_count"] += 1
            player["hand_known"].append(clean_card(value))
        else:
            player["hand_count"] += 1
        return True
    detail_discard = DETAIL_DISCARD_ONE_RE.match(line)
    if detail_discard:
        player = ensure_player(board, detail_discard.group("player"))
        card_name = clean_card(detail_discard.group("card"))
        player["discard_known"].append(card_name)
        consume_hand_card(board, detail_discard.group("player"), card_name)
        return True
    card_text = clean_card(line.lstrip("- ").lstrip("\u2022").strip())
    cards = [clean_card(value) for value in card_text.split(",") if clean_card(value)]
    if not cards:
        return False
    if event.action == "PLAY_BENCH" or "to the Bench" in event.detail:
        for card in cards:
            add_bench(board, event.player, card)
        return True
    if line_has_card_bullet(line):
        player = ensure_player(board, event.player)
        context = detail_context(event.detail)
        if "played them to the Bench" in context:
            for card in cards:
                add_bench(board, event.player, card)
            return True
        if "discard" in context:
            for card in cards:
                player["discard_known"].append(card)
                consume_hand_card(board, event.player, card)
            return True
        if "shuffled" in context and "into their deck" in context:
            for card in cards:
                consume_hand_card(board, event.player, card)
            return True
        if "drew" in context or event.action in {"OPENING_HAND", "DRAW", "ADD_TO_HAND"}:
            player["hand_known"].extend(cards)
            return True
    return True


def detail_context(detail: str) -> str:
    for row in reversed(detail.splitlines()[:-1]):
        stripped = row.strip()
        if stripped and not stripped.startswith("•"):
            return stripped.lower()
    return ""


def switch_active(board: dict[str, Any], player_name: str, old_active: str, new_active: str) -> None:
    player = ensure_player(board, player_name)
    old_card = clean_card(old_active)
    new_card = clean_card(new_active)
    if same_name(player["active"], old_card):
        if not any(same_name(card, old_card) for card in player["bench"]):
            player["bench"].append(player["active"])
    remove_one(player["bench"], new_card)
    player["active"] = new_card


def remove_from_field(board: dict[str, Any], player_name: str, card: str) -> None:
    player = ensure_player(board, player_name)
    clean = clean_card(card)
    if same_name(player["active"], clean):
        player["active"] = ""
    else:
        remove_one(player["bench"], clean)


def add_damage(board: dict[str, Any], player_name: str, target: str, amount: int) -> None:
    card = clean_card(target)
    owner = player_name or owner_from_target(target)
    player = ensure_player(board, owner)
    player["damage"][card] = int(player["damage"].get(card, 0)) + max(0, int(amount))


def set_condition(board: dict[str, Any], player_name: str, target: str, condition: str) -> None:
    player = ensure_player(board, player_name or owner_from_target(target))
    card = clean_card(target)
    conditions = player["conditions"].setdefault(card, [])
    if condition not in conditions:
        conditions.append(condition)


def discard_attachment(board: dict[str, Any], target: str, card: str) -> None:
    owner = owner_from_target(target)
    player = ensure_player(board, owner)
    target_card = clean_card(target)
    attached = player["attachments"].get(target_card, [])
    remove_one(attached, card)
    player["discard_known"].append(clean_card(card))


def consume_hand_card(board: dict[str, Any], player_name: str, card: str) -> None:
    player = ensure_player(board, player_name)
    remove_one(player["hand_known"], card)
    player["hand_count"] = max(0, player["hand_count"] - 1)


def parse_count(value: Any, default: int = 1) -> int:
    if str(value).lower() in {"a", "an"}:
        return 1
    try:
        return int(value)
    except Exception:
        return default


def snapshot(board: dict[str, Any], event_index: int) -> dict[str, Any]:
    data = deepcopy(board)
    data.pop("event_index", None)
    data["event_index"] = event_index
    return data


def summarize(events: list[ReplayEvent], board: dict[str, Any]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for event in events:
        counts[event.action] = counts.get(event.action, 0) + 1
    return {
        "events": len(events),
        "players": sorted(board.get("players", {}).keys()),
        "winner": board.get("winner", ""),
        "turns": sum(1 for event in events if event.action == "TURN_START"),
        "attacks_or_abilities": counts.get("USE_ATTACK_OR_ABILITY", 0),
        "knockouts": counts.get("KNOCKOUT", 0),
        "prizes_taken": sum(parse_count(event.detail, 1) for event in events if event.action == "PRIZE"),
        "timeouts": counts.get("TIMEOUT", 0),
        "unclassified_events": counts.get("UNKNOWN", 0),
        "actions": counts,
    }


def is_detail_line(line: str) -> bool:
    return line.startswith("- ") or line.startswith("\u2022") or line.startswith("   ") or line.startswith("Damage breakdown:")


def line_has_card_bullet(line: str) -> bool:
    return line.lstrip().startswith("\u2022")


def append_detail(existing: str, line: str) -> str:
    return line if not existing else existing + "\n" + line


def owner_from_target(target: str) -> str:
    if "'s " in target:
        return target.split("'s ", 1)[0].strip()
    return ""


def strip_owner(target: str) -> str:
    if "'s " in target:
        return target.split("'s ", 1)[1].strip()
    return target.strip()


def clean_card(value: str) -> str:
    value = strip_owner(value)
    value = re.sub(r"\s+in the Active Spot$", "", value)
    value = re.sub(r"\s+on the Bench$", "", value)
    value = re.sub(r"\s+in the Bench$", "", value)
    return value.strip()


def same_name(left: str, right: str) -> bool:
    return clean_compare(left) == clean_compare(right)


def clean_compare(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", strip_owner(value).lower())


def remove_one(cards: list[str], target: str) -> bool:
    for idx, card in enumerate(cards):
        if same_name(card, target):
            del cards[idx]
            return True
    return False


def move_attachments(player: dict[str, Any], source: str, dest: str) -> None:
    attachments = player.setdefault("attachments", {})
    clean_source = strip_owner(source)
    clean_dest = strip_owner(dest)
    if clean_source in attachments and clean_dest not in attachments:
        attachments[clean_dest] = attachments.pop(clean_source)


def select_by_index(options: list[Any], selected: list[Any]) -> list[Any]:
    result = []
    for raw in selected:
        try:
            idx = int(raw)
        except Exception:
            continue
        if 0 <= idx < len(options):
            result.append(options[idx])
    return result


def compact_current(current: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(current, dict):
        return {}
    return {
        "turn": current.get("turn"),
        "firstPlayer": current.get("firstPlayer"),
        "selectPlayer": current.get("selectPlayer"),
        "energyAttached": current.get("energyAttached"),
        "supporter": current.get("supporter"),
        "stadium": current.get("stadium"),
        "retreated": current.get("retreated"),
    }
