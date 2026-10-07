from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from agent import agent as our_agent
from deck_profile import load_deck_ids
from run_local import load_sample_agent, random_agent, run_game


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=20)
    parser.add_argument("--opponent", choices=["random", "sample", "self"], default="random")
    parser.add_argument("--out", default="eval_results")
    parser.add_argument("--max-steps", type=int, default=2000)
    args = parser.parse_args()

    if args.opponent == "random":
        opponent = random_agent
    elif args.opponent == "sample":
        opponent = load_sample_agent()
        if opponent is None:
            print("Sample agent could not be imported.")
            return 1
    else:
        opponent = our_agent

    deck = load_deck_ids()
    out = Path(args.out)
    wins = 0
    losses = 0
    draws = 0
    crashes = 0
    summaries: List[dict] = []

    for game_index in range(args.games):
        our_seat = game_index % 2
        if our_seat == 0:
            result = run_game(
                our_agent,
                opponent,
                deck,
                deck,
                f"{args.opponent}_{game_index:03d}",
                out,
                args.max_steps,
                agent_labels=("our", args.opponent),
            )
        else:
            result = run_game(
                opponent,
                our_agent,
                deck,
                deck,
                f"{args.opponent}_{game_index:03d}",
                out,
                args.max_steps,
                agent_labels=(args.opponent, "our"),
            )
        summaries.append(result)
        if result.get("engine_error"):
            print("Engine unavailable locally:", result["engine_error"])
            print("No tournament games were run.")
            return 0
        if result.get("crash"):
            crashes += 1
            continue
        winner = result.get("winner")
        if winner is None or winner == 2:
            draws += 1
        elif winner == our_seat:
            wins += 1
        else:
            losses += 1
        print(json.dumps(result, sort_keys=True))

    total_finished = max(1, wins + losses + draws)
    report = {
        "opponent": args.opponent,
        "games": args.games,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "crashes": crashes,
        "win_rate_finished": round(wins / total_finished, 3),
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps({"report": report, "games": summaries}, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if crashes == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
