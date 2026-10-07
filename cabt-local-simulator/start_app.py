from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cabt_local.webapp import main
from cabt_local.local_runtime import LocalRuntimeManager


if __name__ == "__main__":
    runtime = LocalRuntimeManager(ROOT)
    if runtime.limactl.is_file():
        started = runtime.start()
        print(started.get("detail") or started.get("error") or "cabt runtime checked")
    raise SystemExit(main(["--root", str(ROOT), *sys.argv[1:]]))
