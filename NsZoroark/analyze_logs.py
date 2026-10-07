from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from action_classifier import ActionCategory, ClassifiedAction, classify_legal_option
from deck_profile import list_value
from policy import KO_ATTACK_SCORE, score_options
from state_eval import (
    active_pokemon,
    bench_pokemon,
    card_id,
    deck_count,
    getv,
    int_or,
    normalize_state,
)


SUMMARY_FIELDS = [
    "missed_KO_count",
    "bad_pass_count",
    "bad_discard_count",
    "unsafe_bench_count",
    "prize_selection_count",
    "illegal_action_count",
    "timeout_count",
]

EXTRA_FIELDS = [
    "crash_count",
    "failed_deino_setup_count",
    "bad_promotion_count",
    "bad_boss_count",
    "deckout_draw_count",
    "bad_prize_selection_count",
    "decision_count",
    "game_count",
]

PROTECTED_IDS = set(list_value("protected_cards")) | set(list_value("protected_energy_ids"))
UNSAFE_BENCH_IDS = set(list_value("avoid_benching")) | set(list_value("support_pokemon"))
DEINO_ID = 227


@dataclass
class UnsafeBenchEvent:
    card_id: Optional[int]
    card_name: str
    used: bool = False


@dataclass
class GameAnalyzer:
    source: str
    timeout_sec: float
    agent_label_filter: str = "our"
    counts: Dict[str, int] = field(default_factory=lambda: {key: 0 for key in SUMMARY_FIELDS + EXTRA_FIELDS})
    findings: List[Dict[str, Any]] = field(default_factory=list)
    unsafe_bench_events: List[UnsafeBenchEvent] = field(default_factory=list)
    saw_early_decision: bool = False
    saw_deino_early: bool = False
    missed_deino_opportunity: bool = False

    def add_finding(self, kind: str, detail: str, record: Any = None) -> None:
        self.findings.append(
            {
                "kind": kind,
                "source": self.source,
                "detail": detail,
                "turn": getv(record, "turn") if record is not None else None,
                "step": getv(record, "step") if record is not None else None,
            }
        )

    def finalize(self) -> None:
        for event in self.unsafe_bench_events:
            if not event.used:
                self.counts["unsafe_bench_count"] += 1
                self.add_finding("unsafe_bench", f"Benched {event.card_name or event.card_id} without later logged use.")
        if self.saw_early_decision and not self.saw_deino_early and self.missed_deino_opportunity:
            self.counts["failed_deino_setup_count"] += 1
            self.add_finding("failed_deino_setup", "Early Deino setup opportunity was not converted.")


def analyze_decision_record(game: GameAnalyzer, record: Dict[str, Any]) -> None:
    options = getv(record, "legal_options", []) or []
    if not isinstance(options, list):
        return
    choice = normalize_choice(getv(record, "chosen_index", []))
    game.counts["decision_count"] += 1

    if elapsed_seconds(record) > game.timeout_sec:
        game.counts["timeout_count"] += 1
        game.add_finding("timeout", f"Decision took {elapsed_seconds(record):.3f}s.", record)

    if not decision_choice_is_legal(record, options, choice):
        game.counts["illegal_action_count"] += 1
        game.add_finding("illegal_action", f"Illegal choice {choice}.", record)
        return

    chosen = [row for row in options if int_or(getv(row, "index", -1), -1) in choice]
    chosen_categories = {str(getv(row, "category", "")) for row in chosen}

    ko_rows = [row for row in options if str(getv(row, "category", "")) == ActionCategory.ATTACK and float_or(getv(row, "score"), 0.0) >= KO_ATTACK_SCORE]
    if ko_rows and not any(row in chosen for row in ko_rows):
        game.counts["missed_KO_count"] += 1
        best = max(ko_rows, key=lambda row: float_or(getv(row, "score"), 0.0))
        game.add_finding("missed_KO", f"Legal KO attack was available but not chosen: {option_name(best)}.", record)

    if ActionCategory.END_TURN in chosen_categories and useful_attachment_row_exists(options):
        game.counts["bad_pass_count"] += 1
        game.add_finding("bad_pass", "Passed while a useful Energy attachment was available.", record)

    for row in chosen:
        category = str(getv(row, "category", ""))
        cid = optional_int(getv(row, "card_id"))
        if category == ActionCategory.DISCARD_COST and is_protected_discard(cid, str(getv(row, "reason", ""))):
            game.counts["bad_discard_count"] += 1
            game.add_finding("bad_discard", f"Discarded protected card {option_name(row)}.", record)
        if category in (ActionCategory.PLAY_BASIC_TO_BENCH, ActionCategory.SETUP_CHOOSE_BENCH) and is_unsafe_bench(cid, str(getv(row, "card_name", ""))):
            game.unsafe_bench_events.append(UnsafeBenchEvent(cid, str(getv(row, "card_name", ""))))
        if category == ActionCategory.USE_ABILITY:
            mark_support_used(game, cid, str(getv(row, "card_name", "")))
        if is_boss_row(row) and float_or(getv(row, "score"), 0.0) < KO_ATTACK_SCORE:
            game.counts["bad_boss_count"] += 1
            game.add_finding("bad_boss", "Used Boss's Orders without a visible KO/prize-route score.", record)

    if any(str(getv(row, "category", "")) == ActionCategory.PRIZE_SELECTION for row in options):
        if ActionCategory.PRIZE_SELECTION in chosen_categories:
            game.counts["prize_selection_count"] += 1
        else:
            game.counts["bad_prize_selection_count"] += 1
            game.add_finding("bad_prize_selection", "Prize prompt was present but no prize option was chosen.", record)

    promote_rows = [row for row in options if str(getv(row, "category", "")) == ActionCategory.PROMOTE_AFTER_KO]
    if promote_rows and chosen:
        chosen_score = max(float_or(getv(row, "score"), 0.0) for row in chosen)
        best_score = max(float_or(getv(row, "score"), 0.0) for row in promote_rows)
        if best_score > chosen_score + 250.0:
            game.counts["bad_promotion_count"] += 1
            game.add_finding("bad_promotion", "Did not promote the highest-scored attacker/pivot after KO.", record)

    track_deino_from_decision(game, record, options, chosen)


def analyze_trace_record(game: GameAnalyzer, record: Dict[str, Any]) -> None:
    agent_label = str(getv(record, "agent_label", ""))
    if game.agent_label_filter and agent_label and agent_label != game.agent_label_filter:
        return

    obs = getv(record, "obs") or getv(record, "observation")
    if not isinstance(obs, dict):
        analyze_summary_record(game, record)
        return

    action = normalize_choice(getv(record, "action", getv(record, "choice", [])))
    game.counts["decision_count"] += 1

    if elapsed_seconds(record) > game.timeout_sec:
        game.counts["timeout_count"] += 1
        game.add_finding("timeout", f"Decision took {elapsed_seconds(record):.3f}s.", record)

    try:
        state = normalize_state(obs)
        raw_options = state.options
        classified = [classify_legal_option(state, option, idx) for idx, option in enumerate(raw_options)]
        scores = score_options(state)
    except Exception as exc:
        game.counts["illegal_action_count"] += 1
        game.add_finding("trace_parse_error", f"Could not parse trace observation: {exc!r}.", record)
        return

    legal, reason = action_is_legal_for_state(state, action)
    if not legal:
        game.counts["illegal_action_count"] += 1
        game.add_finding("illegal_action", reason, record)
        return

    chosen_actions = [classified[idx] for idx in action if 0 <= idx < len(classified)]

    ko_indices = [idx for idx, item in enumerate(classified) if item.category == ActionCategory.ATTACK and idx < len(scores) and scores[idx] >= KO_ATTACK_SCORE]
    if ko_indices and not any(idx in action for idx in ko_indices):
        game.counts["missed_KO_count"] += 1
        game.add_finding("missed_KO", "Legal KO attack was available but not chosen.", record)

    if any(item.category == ActionCategory.END_TURN for item in chosen_actions) and useful_attachment_action_exists(classified, scores):
        game.counts["bad_pass_count"] += 1
        game.add_finding("bad_pass", "Passed while a useful Energy attachment was available.", record)

    for item in chosen_actions:
        if item.category == ActionCategory.DISCARD_COST and is_protected_discard(item.card_id, ""):
            game.counts["bad_discard_count"] += 1
            game.add_finding("bad_discard", f"Discarded protected card {item.card_name or item.card_id}.", record)
        if item.category in (ActionCategory.PLAY_BASIC_TO_BENCH, ActionCategory.SETUP_CHOOSE_BENCH) and is_unsafe_bench(item.card_id, item.card_name):
            game.unsafe_bench_events.append(UnsafeBenchEvent(item.card_id, item.card_name))
        if item.category == ActionCategory.USE_ABILITY:
            mark_support_used(game, item.card_id, item.card_name)
        if is_boss_action(item) and scores[item.index] < KO_ATTACK_SCORE:
            game.counts["bad_boss_count"] += 1
            game.add_finding("bad_boss", "Used Boss's Orders without a visible KO/prize-route score.", record)
        if item.category == ActionCategory.DRAW_OR_SEARCH and deck_count(state) <= 3:
            game.counts["deckout_draw_count"] += 1
            game.add_finding("deckout_draw", "Used draw/search while deck count was 3 or fewer.", record)

    if any(item.category == ActionCategory.PRIZE_SELECTION for item in classified):
        if any(item.category == ActionCategory.PRIZE_SELECTION for item in chosen_actions):
            game.counts["prize_selection_count"] += 1
        else:
            game.counts["bad_prize_selection_count"] += 1
            game.add_finding("bad_prize_selection", "Prize prompt was present but no prize option was chosen.", record)

    promote_indices = [item.index for item in classified if item.category == ActionCategory.PROMOTE_AFTER_KO]
    if promote_indices and action:
        chosen_score = max(scores[idx] for idx in action if 0 <= idx < len(scores))
        best_score = max(scores[idx] for idx in promote_indices if 0 <= idx < len(scores))
        if best_score > chosen_score + 250.0:
            game.counts["bad_promotion_count"] += 1
            game.add_finding("bad_promotion", "Did not promote the highest-scored attacker/pivot after KO.", record)

    track_deino_from_trace(game, state, classified, chosen_actions)


def analyze_summary_record(game: GameAnalyzer, record: Dict[str, Any]) -> None:
    if getv(record, "crash", False):
        game.counts["crash_count"] += 1
        error = str(getv(record, "error", ""))
        if "timeout" in error.lower() or "max_steps" in error.lower() or "exceeded" in error.lower():
            game.counts["timeout_count"] += 1
        if looks_like_illegal_error(error):
            game.counts["illegal_action_count"] += 1
        game.add_finding("crash", error or "Game summary reported a crash.", record)
    if getv(record, "engine_error"):
        game.add_finding("engine_error", str(getv(record, "engine_error")), record)


def track_deino_from_decision(game: GameAnalyzer, record: Dict[str, Any], options: Sequence[Any], chosen: Sequence[Any]) -> None:
    turn = int_or(getv(record, "turn", 99), 99)
    if turn > 4:
        return
    game.saw_early_decision = True
    if any(optional_int(getv(row, "card_id")) == DEINO_ID for row in chosen):
        game.saw_deino_early = True
    deino_rows = [row for row in options if optional_int(getv(row, "card_id")) == DEINO_ID]
    if deino_rows and not any(row in chosen for row in deino_rows):
        game.missed_deino_opportunity = True


def track_deino_from_trace(game: GameAnalyzer, state: Any, options: Sequence[ClassifiedAction], chosen: Sequence[ClassifiedAction]) -> None:
    turn = int_or(getv(state.current, "turn", 99), 99)
    if turn > 4:
        return
    game.saw_early_decision = True
    if card_id(active_pokemon(state)) == DEINO_ID or any(card_id(pokemon) == DEINO_ID for pokemon in bench_pokemon(state)):
        game.saw_deino_early = True
    if any(item.card_id == DEINO_ID for item in chosen):
        game.saw_deino_early = True
    deino_options = [item for item in options if item.card_id == DEINO_ID]
    if deino_options and not any(item.card_id == DEINO_ID for item in chosen):
        game.missed_deino_opportunity = True


def decision_choice_is_legal(record: Dict[str, Any], options: Sequence[Any], choice: Sequence[int]) -> bool:
    option_indices = {int_or(getv(row, "index", -1), -1) for row in options}
    min_count = max(0, int_or(getv(record, "min_count", 0), 0))
    max_count = max(min_count, int_or(getv(record, "max_count", min_count), min_count))
    if len(choice) < min_count or len(choice) > max_count:
        return False
    if len(set(choice)) != len(choice):
        return False
    return all(idx in option_indices for idx in choice)


def action_is_legal_for_state(state: Any, action: Sequence[int]) -> Tuple[bool, str]:
    if len(action) < state.min_count or len(action) > state.max_count:
        return False, f"Choice length {len(action)} outside [{state.min_count}, {state.max_count}]."
    if len(set(action)) != len(action):
        return False, f"Choice has duplicate indices: {list(action)}."
    option_count = len(state.options)
    if any(idx < 0 or idx >= option_count for idx in action):
        return False, f"Choice contains index outside range(0, {option_count}): {list(action)}."
    return True, ""


def useful_attachment_row_exists(options: Sequence[Any]) -> bool:
    for row in options:
        if str(getv(row, "category", "")) != ActionCategory.ATTACH_ENERGY:
            continue
        if float_or(getv(row, "score"), 0.0) > 50.0:
            return True
    return False


def useful_attachment_action_exists(options: Sequence[ClassifiedAction], scores: Sequence[float]) -> bool:
    for item in options:
        if item.category == ActionCategory.ATTACH_ENERGY and item.index < len(scores) and scores[item.index] > 50.0:
            return True
    return False


def is_protected_discard(cid: Optional[int], reason: str) -> bool:
    if cid in PROTECTED_IDS:
        return True
    text = reason.lower()
    return "protected" in text or "avoid discarding" in text


def is_unsafe_bench(cid: Optional[int], name: str) -> bool:
    normalized = name.lower()
    return cid in UNSAFE_BENCH_IDS or "fezandipiti ex" in normalized or "pecharunt ex" in normalized


def mark_support_used(game: GameAnalyzer, cid: Optional[int], name: str) -> None:
    normalized = name.lower()
    for event in game.unsafe_bench_events:
        same_id = cid is not None and event.card_id == cid
        same_name = bool(event.card_name and event.card_name.lower() in normalized)
        if same_id or same_name:
            event.used = True


def is_boss_row(row: Any) -> bool:
    return "boss" in (str(getv(row, "card_name", "")) + " " + str(getv(row, "reason", ""))).lower()


def is_boss_action(action: ClassifiedAction) -> bool:
    return "boss" in (action.card_name + " " + action.option_text).lower()


def option_name(row: Any) -> str:
    return str(getv(row, "card_name", "") or getv(row, "attack_name", "") or getv(row, "index", "?"))


def normalize_choice(value: Any) -> List[int]:
    if value is None:
        return []
    if isinstance(value, int):
        return [value]
    if not isinstance(value, list):
        return []
    result: List[int] = []
    for item in value:
        try:
            result.append(int(item))
        except (TypeError, ValueError):
            continue
    return result


def optional_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def float_or(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def elapsed_seconds(record: Any) -> float:
    for key in ("elapsed_sec", "seconds", "duration_sec", "time_sec"):
        value = getv(record, key)
        if value is not None:
            return float_or(value, 0.0)
    return 0.0


def looks_like_illegal_error(error: str) -> bool:
    text = str(error or "").lower()
    return any(term in text for term in ("illegal", "option index", "duplicate", "mincount", "maxcount", "cannot be selected"))


def load_records_from_file(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    if path.suffix.lower() == ".jsonl":
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                records.append(value)
        return records

    if path.suffix.lower() == ".json":
        try:
            value = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except json.JSONDecodeError:
            return []
        records.extend(flatten_json_records(value))
    return records


def flatten_json_records(value: Any) -> List[Dict[str, Any]]:
    if isinstance(value, list):
        out: List[Dict[str, Any]] = []
        for item in value:
            out.extend(flatten_json_records(item))
        return out
    if not isinstance(value, dict):
        return []
    out = [value]
    if isinstance(value.get("games"), list):
        out.extend(item for item in value["games"] if isinstance(item, dict))
    if isinstance(value.get("records"), list):
        out.extend(item for item in value["records"] if isinstance(item, dict))
    return out


def iter_input_files(paths: Sequence[str]) -> Iterable[Path]:
    for raw in paths:
        path = Path(raw)
        if not path.exists():
            continue
        if path.is_file():
            if path.suffix.lower() in (".json", ".jsonl"):
                yield path
            continue
        for child in sorted(path.rglob("*")):
            if child.is_file() and child.suffix.lower() in (".json", ".jsonl"):
                yield child


def record_kind(record: Dict[str, Any]) -> str:
    if "legal_options" in record and "chosen_index" in record:
        return "decision"
    if ("obs" in record or "observation" in record) and ("action" in record or "choice" in record):
        return "trace"
    return "summary"


def analyze_files(paths: Sequence[str], timeout_sec: float, agent_label_filter: str = "our") -> Tuple[Dict[str, int], List[Dict[str, Any]]]:
    totals = {key: 0 for key in SUMMARY_FIELDS + EXTRA_FIELDS}
    findings: List[Dict[str, Any]] = []
    files = list(iter_input_files(paths))
    for path in files:
        records = load_records_from_file(path)
        if not records:
            continue
        game = GameAnalyzer(str(path), timeout_sec, agent_label_filter=agent_label_filter)
        game.counts["game_count"] = 1
        for record in records:
            kind = record_kind(record)
            if kind == "decision":
                analyze_decision_record(game, record)
            elif kind == "trace":
                analyze_trace_record(game, record)
            else:
                analyze_summary_record(game, record)
        game.finalize()
        for key in totals:
            totals[key] += game.counts.get(key, 0)
        findings.extend(game.findings)
    return totals, findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze PTCG agent gameplay logs for natural-gameplay mistakes.")
    parser.add_argument("paths", nargs="*", default=["local_results", "eval_results"], help="JSON/JSONL files or directories to analyze.")
    parser.add_argument("--timeout-sec", type=float, default=2.0, help="Per-decision timeout threshold for log analysis.")
    parser.add_argument("--agent-label", default="our", help="Trace agent_label to analyze; ignored for unlabeled decision logs.")
    parser.add_argument("--all-agents", action="store_true", help="Analyze every labeled trace row, including opponents.")
    parser.add_argument("--out", default="", help="Optional JSON output path.")
    parser.add_argument("--show-findings", action="store_true", help="Include detailed finding rows in stdout.")
    args = parser.parse_args()

    agent_label_filter = "" if args.all_agents else args.agent_label
    summary, findings = analyze_files(args.paths, args.timeout_sec, agent_label_filter=agent_label_filter)
    report: Dict[str, Any] = {"summary": {key: summary.get(key, 0) for key in SUMMARY_FIELDS}}
    extras = {key: summary.get(key, 0) for key in EXTRA_FIELDS if summary.get(key, 0)}
    if extras:
        report["extra"] = extras
    if args.show_findings:
        report["findings"] = findings

    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
