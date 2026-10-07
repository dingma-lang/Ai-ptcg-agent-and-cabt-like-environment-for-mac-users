"""Read-only retrospective audit of saved simulator records, not an agent evaluator."""

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


MAIN_CONTEXT = 0
ATTACK_OPTION = 13
END_OPTION = 14


def wilson(wins, games):
    """Illustrative 95% binomial interval; does not correct sampling bias."""
    if not 0 <= wins <= games:
        raise ValueError("Require 0 <= wins <= games")
    if not games:
        return None
    z = 1.959963984540054
    p = wins / games
    denominator = 1 + z * z / games
    center = (p + z * z / (2 * games)) / denominator
    half = z * math.sqrt(p * (1 - p) / games + z * z / (4 * games * games)) / denominator
    return [max(0.0, center - half), min(1.0, center + half)]


def selection_status(row):
    select = (row.get("observation") or {}).get("select")
    if not isinstance(select, dict) or not isinstance(select.get("option"), list):
        return "unverifiable"
    options = select["option"]
    minimum, maximum = select.get("minCount"), select.get("maxCount")
    if (type(minimum) is not int or type(maximum) is not int
            or not 0 <= minimum <= maximum or minimum > len(options)):
        return "unverifiable"
    indices = row.get("selected_indexes")
    if not isinstance(indices, list) or any(type(i) is not int for i in indices):
        return "invalid"
    if (len(indices) != len(set(indices)) or not minimum <= len(indices) <= maximum
            or any(i < 0 or i >= len(options) for i in indices)):
        return "invalid"
    return "valid"


def agent_label(agent_id):
    if agent_id == "random":
        return "random"
    path = str(agent_id).replace("\\", "/")
    if "/imported_agents/" in path:
        return "import:" + path.split("/imported_agents/", 1)[1].split("/", 1)[0]
    if path.endswith("/agent.py:agent"):
        return "workspace:" + path.rsplit("/", 2)[-2]
    return "unknown"


def comparison_seat(match):
    labels = [match["seat_0"], match["seat_1"]]
    for seat in (0, 1):
        if (labels[seat].startswith("import:submission-palfingon-1.3-")
                and labels[1 - seat].startswith("import:submission-palfingon-1.2-")):
            return seat
    return None


def longest_pass_streak(turns):
    longest = current = 0
    previous = None
    for turn in sorted(turns, key=lambda t: t["turn"]):
        if turn["pass_only"]:
            current = current + 1 if previous == turn["turn"] - 2 else 1
            longest = max(longest, current)
        else:
            current = 0
        previous = turn["turn"]
    return longest


def main_turns(match_id, rows):
    grouped = defaultdict(list)
    for row in rows:
        select = (row.get("observation") or {}).get("select") or {}
        if select.get("context") == MAIN_CONTEXT:
            grouped[(row["player"], row["turn"])].append(row)
    turns = []
    for (player, turn), windows in sorted(grouped.items()):
        types = []
        verified = all(selection_status(row) == "valid" for row in windows)
        for row in windows:
            if selection_status(row) == "valid":
                options = row["observation"]["select"]["option"]
                types.extend(options[i].get("type") for i in row["selected_indexes"])
        turns.append({
            "match_id": match_id, "player": player, "turn": turn,
            "main_windows": len(windows), "selected_main_actions": len(types),
            "verified": verified,
            "pass_only": bool(verified and types and all(t == END_OPTION for t in types)),
            "attack_option_selected": ATTACK_OPTION in types,
            "end_selected": END_OPTION in types,
        })
    return turns


def write_csv(path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_audit(root, output):
    data = root / "cabt-local-simulator/data"
    source_files = set()

    def read_json(path):
        source_files.add(path)
        return json.loads(path.read_text(encoding="utf-8"))

    def read_rows(path):
        source_files.add(path)
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    inventory, turns, manifest = [], [], []
    agent_counts, trace_counts, statuses = Counter(), Counter(), Counter()
    terminations, issues = Counter(), []
    all_rows = {}
    for path in sorted((data / "summaries").glob("*.json")):
        summary = read_json(path)
        match_id = summary["match_id"]
        if Path(match_id).name != match_id:
            raise ValueError("Invalid match identifier")
        episode = data / "episodes" / (match_id + ".jsonl")
        sidecar = data / "episodes" / (match_id + ".invalid.jsonl")
        rows = read_rows(episode) if episode.exists() else []
        all_rows[match_id] = rows
        violations = read_rows(sidecar) if sidecar.exists() else []
        match_turns = main_turns(match_id, rows)
        turns.extend(match_turns)
        first = set()
        seats = defaultdict(set)
        selected_statuses = Counter()
        for row in rows:
            label = agent_label(row.get("agent_id"))
            agent_counts[label] += 1
            trace_counts[label] += bool(row.get("agent_trace"))
            seats[row["player"]].add(label)
            current = (row.get("observation") or {}).get("current") or {}
            if current.get("firstPlayer") in (0, 1):
                first.add(current["firstPlayer"])
            selected_statuses[selection_status(row)] += 1
        statuses.update(selected_statuses)
        terminations[str(summary.get("termination_reason"))] += 1
        item = {
            "match_id": match_id,
            "episode_exists": episode.exists(),
            "recorded_decisions": len(rows),
            "summary_decisions": summary.get("decision_count"),
            "engine_turns": summary.get("turn_count"),
            "winner": summary.get("winner"),
            "first_player": next(iter(first)) if len(first) == 1 else None,
            "seat_0": ";".join(sorted(seats[0])),
            "seat_1": ";".join(sorted(seats[1])),
            "termination": summary.get("termination_reason"),
            "reported_error": summary.get("error"),
            "sidecar_exists": sidecar.exists(),
            "raw_invalid_records": len(violations),
            "recorded_invalid_selections": selected_statuses["invalid"],
            "unverifiable_selections": selected_statuses["unverifiable"],
            "trace_decisions": sum(bool(r.get("agent_trace")) for r in rows),
            "observed_main_turns": len(match_turns),
            "pass_only_turns": sum(t["pass_only"] for t in match_turns),
            "attack_turns": sum(t["attack_option_selected"] for t in match_turns),
            "seat_0_max_pass_streak": longest_pass_streak([t for t in match_turns if t["player"] == 0]),
            "seat_1_max_pass_streak": longest_pass_streak([t for t in match_turns if t["player"] == 1]),
        }
        inventory.append(item)
        if len(rows) != summary.get("decision_count"):
            issues.append(match_id + ": summary/episode decision count differs")
        if len(first) > 1 or any(len(values) > 1 for values in seats.values()):
            issues.append(match_id + ": inconsistent first player or agent identity")
        if [r.get("decision_index") for r in rows] != list(range(len(rows))):
            issues.append(match_id + ": non-contiguous decision indices")

    summarized = {m["match_id"] for m in inventory}
    unsummarized = []
    for path in sorted((data / "episodes").glob("*.jsonl")):
        if path.name.endswith(".invalid.jsonl") or path.stem in summarized:
            continue
        unsummarized.append({"match_id": path.stem, "recorded_decisions": len(read_rows(path))})

    comparisons = []
    for match in inventory:
        seat = comparison_seat(match)
        if seat is not None:
            comparison = {k: match[k] for k in (
                "match_id", "winner", "first_player", "engine_turns", "recorded_decisions",
                "pass_only_turns", "seat_0_max_pass_streak", "seat_1_max_pass_streak")}
            comparison["version_1_3_seat"] = seat
            comparisons.append(comparison)
    decided = [m for m in comparisons if m["winner"] in (0, 1)]
    wins = sum(m["winner"] == m["version_1_3_seat"] for m in decided)
    battle15 = next((rs for name, rs in all_rows.items() if name.startswith("battle15_")), [])
    window15 = [r for r in battle15 if 12 <= r["turn"] <= 26]
    end15 = sum(
        any(r["observation"]["select"]["option"][i].get("type") == END_OPTION
            for i in r["selected_indexes"])
        for r in window15 if selection_status(r) == "valid")

    for path in sorted(source_files | {Path(__file__).resolve()}):
        manifest.append({"path": str(path.relative_to(root)), "bytes": path.stat().st_size,
                         "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    result = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Retrospective saved records; no new games or agent changes",
        "summary_count": len(inventory),
        "nonempty_episode_count": sum(bool(m["recorded_decisions"]) for m in inventory),
        "decisions": sum(agent_counts.values()),
        "known_winner_summaries": sum(m["winner"] in (0, 1) for m in inventory),
        "no_winner_summaries": [m["match_id"] for m in inventory if m["winner"] not in (0, 1)],
        "reported_errors": sum(bool(m["reported_error"]) for m in inventory),
        "terminations": dict(terminations),
        "selection_status": dict(statuses),
        "invalid_sidecars_present": sum(m["sidecar_exists"] for m in inventory),
        "raw_invalid_records": sum(m["raw_invalid_records"] for m in inventory),
        "agent_decisions": dict(sorted(agent_counts.items())),
        "trace_decisions_by_agent": dict(sorted(trace_counts.items())),
        "observed_main_turns": len(turns),
        "pass_only_turns": sum(t["pass_only"] for t in turns),
        "attack_turns": sum(t["attack_option_selected"] for t in turns),
        "unsummarized_episodes": unsummarized,
        "integrity_issues": issues,
        "battle15_end_selections_turns12_26": end15,
        "imported_1_3_vs_1_2": {
            "matches": comparisons, "wins_1_3": wins, "decided_games": len(decided),
            "wilson95": wilson(wins, len(decided)),
            "sampling_warning": "Convenience sample; inspect seat and first-player columns; not a paired experiment",
        },
        "input_manifest": manifest,
    }
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "match_inventory.csv", inventory)
    write_csv(output / "turn_metrics.csv", turns)
    (output / "audit_summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "data")
    args = parser.parse_args()
    report = run_audit(args.root.resolve(), args.output.resolve())
    print(json.dumps({k: v for k, v in report.items() if k != "input_manifest"}, indent=2))
