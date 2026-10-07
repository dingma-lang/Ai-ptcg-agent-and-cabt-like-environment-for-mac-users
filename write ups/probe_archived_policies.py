"""Isolated fixed-observation experiments, never a counterfactual game simulator."""

import argparse
import contextlib
import copy
import hashlib
import io
import json
import os
import re
import statistics
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REVIEW = Path("/Users/ding/.codex/attachments/a682223e-d4d8-42bf-bcab-7e105b109e24/pasted-text.txt")


def worker(payload):
    # The parent starts this process with -I and an extracted archive as cwd.
    sys.path.insert(0, os.getcwd())
    import agent as entry
    import adapters.cabt.submission_entry as adapter
    import core.agent_memory as memory_module

    if entry._cabt_agent is None:
        raise RuntimeError("Archive did not import its full agent")
    fallback_calls = []
    outer_errors = []
    original_fallback = adapter.safe_cabt_fallback
    original_adapter = entry._cabt_agent

    def tracked_adapter(observation):
        try:
            return original_adapter(observation)
        except Exception as exc:
            outer_errors.append(type(exc).__name__)
            raise

    def tracked_fallback(select):
        fallback_calls.append(1)
        return original_fallback(select)

    adapter.safe_cabt_fallback = tracked_fallback
    entry._cabt_agent = tracked_adapter
    if payload["mode"] == "without_before_commit":
        import core.reviewed_turn_planner as reviewed
        reviewed.before_commit_choice = lambda state, scores: None

    results = []
    for case in payload["cases"]:
        for repeat in range(payload["repeats"]):
            # Preserve aliases to the global object while clearing all match history.
            memory_module.GLOBAL_AGENT_MEMORY.__dict__.clear()
            memory_module.GLOBAL_AGENT_MEMORY.__dict__.update(memory_module.AgentMemory().__dict__)
            observation = copy.deepcopy(case["observation"])
            before = len(fallback_calls)
            errors_before = len(outer_errors)
            start = time.perf_counter_ns()
            with contextlib.redirect_stdout(io.StringIO()):
                choice = entry.agent(observation)
            elapsed = (time.perf_counter_ns() - start) / 1e6
            options = case["observation"]["select"]["option"]
            select = case["observation"]["select"]
            valid = (isinstance(choice, list) and all(type(i) is int for i in choice)
                     and len(set(choice)) == len(choice)
                     and select["minCount"] <= len(choice) <= select["maxCount"]
                     and all(0 <= i < len(options) for i in choice))
            results.append({
                "dataset": case["dataset"], "decision": case["decision"], "repeat": repeat,
                "choice": choice, "valid": valid, "fallback_calls": len(fallback_calls) - before,
                "outer_errors": len(outer_errors) - errors_before,
                "agent_ms": elapsed,
                "expected_expert": case.get("expected_expert"),
                "expected_regression": case.get("expected_regression"),
                "recorded_choice": case["recorded_choice"],
                "selected_types": [options[i].get("type") for i in choice] if valid else [],
            })
    return results


def extract_checked(archive, target):
    with zipfile.ZipFile(archive) as handle:
        for member in handle.infolist():
            destination = (target / member.filename).resolve()
            if target.resolve() not in destination.parents and destination != target.resolve():
                raise ValueError("Unsafe archive member")
            if (member.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("Archive symlink not supported")
        handle.extractall(target)


def run(output, repeats, annotation_path):
    fixture_path = ROOT / "palfingon/tests/fixtures/battle24_review.json"
    fixture = json.loads(fixture_path.read_text())
    annotation = annotation_path.read_text()
    labels = {int(i): int(j) for i, j in re.findall(
        r"Decision #(\d+)[^\n]*\n(?:Effect:[^\n]*\n)?Original:[^\n]*\nProposed: #(\d+)", annotation)}
    if set(labels) != {int(i) for i in fixture["decisions"]}:
        raise ValueError("Expert annotations do not match the fixture")
    episodes = ROOT / "cabt-local-simulator/data/episodes"
    sources = [fixture_path, annotation_path, Path(__file__).resolve()]

    def episode(number):
        path, = [p for p in episodes.glob("battle{}_*.jsonl".format(number))
                 if not p.name.endswith(".invalid.jsonl")]
        sources.append(path)
        return {r["decision_index"]: r for r in map(json.loads, path.read_text().splitlines())}

    battle24, battle15 = episode(24), episode(15)
    cases = []
    for index, case in sorted(fixture["decisions"].items(), key=lambda pair: int(pair[0])):
        index = int(index)
        if case["observation"] != battle24[index]["observation"]:
            raise ValueError("Fixture differs from recorded observation")
        cases.append({"dataset": "battle24_review", "decision": index,
                      "observation": case["observation"], "expected_expert": [labels[index]],
                      "expected_regression": [case["expected"]],
                      "recorded_choice": battle24[index]["selected_indexes"]})
    for index, row in sorted(battle15.items()):
        if not 12 <= row["turn"] <= 26:
            continue
        select = row["observation"]["select"]
        if select["context"] == 0 and any(select["option"][i].get("type") == 14 for i in row["selected_indexes"]):
            cases.append({"dataset": "battle15_end_windows", "decision": index,
                          "observation": row["observation"], "recorded_choice": row["selected_indexes"]})

    results, configurations = [], []
    for version, mode in [("1.1", "full"), ("1.2", "full"), ("1.3", "full"),
                          ("1.3", "without_before_commit")]:
        archive = ROOT / "palfingon" / ("submission palfingon " + version + ".zip")
        sources.append(archive)
        print("Testing archive {} / {}".format(version, mode), flush=True)
        with tempfile.TemporaryDirectory(prefix="ptcg-scientific-") as folder:
            target = Path(folder)
            extract_checked(archive, target)
            script = "import runpy; runpy.run_path({!r}, run_name='__main__')".format(str(Path(__file__).resolve()))
            payload = {"cases": cases, "mode": mode, "repeats": repeats}
            process = subprocess.run([sys.executable, "-I", "-B", "-c", script, "--worker"],
                                     cwd=target, input=json.dumps(payload), text=True, capture_output=True, timeout=120)
            if process.returncode:
                raise RuntimeError(process.stderr)
            records = json.loads(process.stdout)
        for row in records:
            row.update(version=version, mode=mode)
        results.extend(records)
        first = [r for r in records if r["repeat"] == 0]
        reviewed = [r for r in first if r["dataset"] == "battle24_review"]
        end_windows = [r for r in first if r["dataset"] == "battle15_end_windows"]
        choices = {}
        for row in records:
            choices.setdefault((row["dataset"], row["decision"]), set()).add(tuple(row["choice"]))
        configurations.append({
            "version": version, "mode": mode, "calls": len(records),
            "valid_calls": sum(r["valid"] for r in records),
            "fallback_calls": sum(r["fallback_calls"] for r in records),
            "outer_errors": sum(r["outer_errors"] for r in records),
            "nondeterministic_windows": sum(len(v) > 1 for v in choices.values()),
            "expert_matches": sum(r["choice"] == r["expected_expert"] for r in reviewed),
            "regression_matches": sum(r["choice"] == r["expected_regression"] for r in reviewed),
            "reviewed_windows": len(reviewed),
            "end_windows": len(end_windows),
            "end_still_selected": sum(14 in r["selected_types"] for r in end_windows),
            "median_ms": statistics.median(r["agent_ms"] for r in records),
            "max_ms": max(r["agent_ms"] for r in records),
        })
    output.mkdir(parents=True, exist_ok=True)
    (output / "archive_probes.json").write_text(json.dumps({
        "design": "Independent saved-observation probes; memory reset each case, metadata caches retained; first call may initialize metadata; not full games",
        "repeats": repeats, "configurations": configurations, "records": results,
        "sources": [{"name": str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else "expert battle24 annotation attachment",
                     "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(set(sources))],
    }, indent=2) + "\n")
    print(json.dumps(configurations, indent=2))


if __name__ == "__main__":
    if "--worker" in sys.argv:
        print(json.dumps(worker(json.load(sys.stdin))))
    else:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "scientific_data")
        parser.add_argument("--repeats", type=int, default=3)
        parser.add_argument("--annotations", type=Path, default=REVIEW)
        args = parser.parse_args()
        if args.repeats < 1:
            parser.error("--repeats must be positive")
        run(args.output, args.repeats, args.annotations)
