from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run palfingon through the existing official local cabt worker.")
    parser.add_argument("--opponent", choices=("random", "mirror", "palaking"), default="mirror")
    parser.add_argument("--games", type=int, default=1)
    args = parser.parse_args()
    if args.games < 1:
        parser.error("--games must be positive")
    root = Path(__file__).resolve().parent
    simulator = root.parent / "cabt-local-simulator"
    sys.path.insert(0, str(simulator / "src"))
    from cabt_local.runner import TwoDeckRunner

    own = f"file:{root / 'agent.py'}:agent"
    opponent_root = root.parent / "Palaking" if args.opponent == "palaking" else root
    other = "random" if args.opponent == "random" else f"file:{opponent_root / 'agent.py'}:agent"
    runner = TwoDeckRunner(simulator / "data", timeout_s=5.0)
    for game in range(args.games):
        decks = [root / "deck.csv", opponent_root / "deck.csv"]
        agents = [own, other]
        if game % 2:
            decks.reverse()
            agents.reverse()
        result = runner.play_paths(*decks, *agents, record=True, prefer_kaggle_env=False)
        print(json.dumps(vars(result), indent=2, default=str))
        if result.error:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
