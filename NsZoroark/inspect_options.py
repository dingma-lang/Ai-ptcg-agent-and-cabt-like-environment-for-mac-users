from __future__ import annotations

import argparse
import json
from pathlib import Path

from action_classifier import classify_legal_option
from decision_reason import explain_option
from policy import debug_scores
from state_eval import getv, normalize_state


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("observation_json", help="Path to a saved observation dictionary as JSON.")
    args = parser.parse_args()

    obs = json.loads(Path(args.observation_json).read_text(encoding="utf-8"))
    state = normalize_state(obs)
    choice, rows = debug_scores(obs)
    print(f"context={state.context} type={state.select_type} min={state.min_count} max={state.max_count}")
    print("choice=", choice)
    for idx, score, label in sorted(rows, key=lambda row: row[1], reverse=True):
        option = state.options[idx]
        classified = classify_legal_option(state, option, idx)
        reason = explain_option(state, classified, score, idx in choice)
        print(f"{idx:3d} {score:9.1f} {classified.category:24s} {label} raw_type={getv(option, 'type')} | {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
