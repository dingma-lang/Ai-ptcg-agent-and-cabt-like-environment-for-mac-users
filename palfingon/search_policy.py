from __future__ import annotations

from typing import Any, Optional


def maybe_search(obs: Any, state: Any, scores: list) -> Optional[list]:
    """Hook for future cabt tactical search.

    The first milestone keeps this disabled because the local macOS workspace
    cannot load the Linux cabt engine. The heuristic policy calls this hook
    safely, so a later search implementation can be dropped in without changing
    agent.py.
    """
    return None
