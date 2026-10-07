from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cabt_local.local_runtime import LocalRuntimeManager


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage the local official cabt engine worker.")
    parser.add_argument("action", choices=("status", "start", "stop"))
    args = parser.parse_args()
    manager = LocalRuntimeManager(ROOT)
    result = manager.status() if args.action == "status" else getattr(manager, args.action)()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok", result.get("available", False)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
