from __future__ import annotations

import argparse
import importlib
import json
import random
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from deck_profile import load_deck_ids


AgentFn = Callable[[dict], List[int]]


def random_agent(obs_dict: dict) -> List[int]:
    select = obs_dict.get("select") if isinstance(obs_dict, dict) else None
    if select is None:
        return load_deck_ids()
    options = select.get("option") or []
    if not options:
        return []
    min_count = max(0, int(select.get("minCount", 0) or 0))
    max_count = min(len(options), max(min_count, int(select.get("maxCount", min_count) or min_count)))
    if max_count <= 0:
        return []
    count = random.randint(min_count, max_count)
    return random.sample(range(len(options)), count)


def load_engine() -> Tuple[Optional[Dict[str, Any]], Optional[Exception]]:
    root = Path(__file__).resolve().parent
    sample = root / "sample_submission"
    if sample.exists() and str(sample) not in sys.path:
        sys.path.insert(0, str(sample))
    try:
        from cg.game import battle_finish, battle_select, battle_start, visualize_data

        return {
            "battle_finish": battle_finish,
            "battle_select": battle_select,
            "battle_start": battle_start,
            "visualize_data": visualize_data,
        }, None
    except Exception as exc:
        return None, exc


def load_sample_agent() -> Optional[AgentFn]:
    try:
        module = importlib.import_module("sample_submission.main")
        return module.agent
    except Exception:
        try:
            module = importlib.import_module("main")
            return module.agent
        except Exception:
            return None


def run_game(
    agent0: AgentFn,
    agent1: AgentFn,
    deck0: List[int],
    deck1: List[int],
    label: str,
    result_dir: Path,
    max_steps: int = 2000,
    agent_labels: Optional[Tuple[str, str]] = None,
) -> Dict[str, Any]:
    engine, engine_error = load_engine()
    if engine is None:
        result_dir.mkdir(parents=True, exist_ok=True)
        summary = {"label": label, "engine_error": str(engine_error), "winner": None, "steps": 0, "crash": False}
        (result_dir / f"{safe_name(label)}.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary

    result_dir.mkdir(parents=True, exist_ok=True)
    agent_labels = agent_labels or ("agent0", "agent1")
    trace_path = result_dir / f"{safe_name(label)}.trace.jsonl"
    try:
        trace_path.unlink()
    except FileNotFoundError:
        pass
    started = time.time()
    obs = None
    crashed = False
    error_text = ""
    winner = None
    steps = 0
    try:
        obs, start_data = engine["battle_start"](deck0, deck1)
        if obs is None:
            return {
                "label": label,
                "winner": None,
                "steps": 0,
                "crash": True,
                "error": f"BattleStart failed player={start_data.errorPlayer} type={start_data.errorType}",
            }

        agents = [agent0, agent1]
        while steps < max_steps:
            current = obs.get("current") or {}
            result = int(current.get("result", -1))
            if result != -1:
                winner = result
                break
            your_index = int(current.get("yourIndex", 0) or 0)
            decision_start = time.time()
            action = agents[your_index](obs)
            elapsed = time.time() - decision_start
            legal, legal_error = action_is_legal(obs, action)
            append_trace(
                trace_path,
                {
                    "label": label,
                    "step": steps,
                    "player_index": your_index,
                    "agent_label": agent_labels[your_index] if 0 <= your_index < len(agent_labels) else f"agent{your_index}",
                    "elapsed_sec": round(elapsed, 6),
                    "action": action,
                    "legal": legal,
                    "legal_error": legal_error,
                    "obs": obs,
                },
            )
            obs = engine["battle_select"](action)
            steps += 1
        else:
            error_text = f"Exceeded max_steps={max_steps}"
            crashed = True

        try:
            html = engine["visualize_data"]()
            (result_dir / f"{safe_name(label)}.html").write_text(html, encoding="utf-8")
        except Exception:
            pass
    except Exception as exc:
        crashed = True
        error_text = repr(exc)
    finally:
        try:
            engine["battle_finish"]()
        except Exception:
            pass

    summary = {
        "label": label,
        "winner": winner,
        "steps": steps,
        "seconds": round(time.time() - started, 3),
        "crash": crashed,
        "error": error_text,
    }
    (result_dir / f"{safe_name(label)}.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def action_is_legal(obs: Any, action: Any) -> Tuple[bool, str]:
    if not isinstance(action, list) or not all(isinstance(idx, int) for idx in action):
        return False, "action is not list[int]"
    select = obs.get("select") if isinstance(obs, dict) else None
    if select is None:
        return True, ""
    options = select.get("option") or []
    min_count = max(0, int(select.get("minCount", 0) or 0))
    max_count = min(len(options), max(min_count, int(select.get("maxCount", min_count) or min_count)))
    if len(action) < min_count or len(action) > max_count:
        return False, f"choice length {len(action)} outside [{min_count}, {max_count}]"
    if len(set(action)) != len(action):
        return False, "choice has duplicate indices"
    if any(idx < 0 or idx >= len(options) for idx in action):
        return False, f"choice contains index outside range(0, {len(options)})"
    return True, ""


def append_trace(path: Path, row: Dict[str, Any]) -> None:
    try:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")
    except Exception:
        pass


def safe_name(label: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in label)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-steps", type=int, default=2000)
    parser.add_argument("--out", default="local_results")
    args = parser.parse_args()

    from agent import agent as our_agent

    deck = load_deck_ids()
    result_dir = Path(args.out)
    sample_agent = load_sample_agent()
    matchups: List[Tuple[str, AgentFn, AgentFn, Tuple[str, str]]] = [
        ("our_vs_random", our_agent, random_agent, ("our", "random")),
        ("self_play", our_agent, our_agent, ("our", "our")),
    ]
    if sample_agent is not None:
        matchups.append(("our_vs_sample", our_agent, sample_agent, ("our", "sample")))

    results = []
    for label, a0, a1, agent_labels in matchups:
        result = run_game(a0, a1, deck, deck, label, result_dir, max_steps=args.max_steps, agent_labels=agent_labels)
        results.append(result)
        print(json.dumps(result, sort_keys=True))

    if results and results[0].get("engine_error"):
        print("Engine unavailable locally:", results[0]["engine_error"])
        print("This workspace has a Linux libcg.so, so full battle runs need Linux/Kaggle or a compatible container.")
    return 0 if not any(r.get("crash") for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
