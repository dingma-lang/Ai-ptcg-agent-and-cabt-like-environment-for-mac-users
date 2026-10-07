from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import threading
import traceback
import uuid
from dataclasses import asdict
from pathlib import Path
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


MAX_REQUEST_BYTES = 2 * 1024 * 1024


class BattleService:
    """Serialize access to the official wrapper's process-global Battle pointer."""

    def __init__(self) -> None:
        from cg import api, game

        self.api = api
        self.game = game
        self.lock = threading.RLock()
        self.session_id: str | None = None
        self.search_ids: set[int] = set()
        self.cards = self.api.all_card_data()
        self.attacks = self.api.all_attack()
        self.card_count = len(self.cards)
        self.attack_count = len(self.attacks)
        self.kaggle_environment = self._load_kaggle_environment()

    def health(self) -> dict[str, Any]:
        with self.lock:
            return {
                "ok": True,
                "service": "cabt-official-engine-worker",
                "architecture": platform.machine(),
                "python": platform.python_version(),
                "engine_loaded": True,
                "card_count": self.card_count,
                "attack_count": self.attack_count,
                "battle_active": self.session_id is not None,
                **self.kaggle_environment,
            }

    def _load_kaggle_environment(self) -> dict[str, Any]:
        try:
            import kaggle_environments
            from kaggle_environments.envs.cabt import cabt

            visualizer = Path(cabt.__file__).parent / "visualizer" / "default" / "dist" / "index.html"
            return {
                "kaggle_environments": kaggle_environments.__version__,
                "cabt_environment_registered": "cabt" in kaggle_environments.environments,
                "official_visualizer_available": visualizer.is_file(),
            }
        except Exception as exc:
            return {
                "kaggle_environments": "unavailable",
                "cabt_environment_registered": False,
                "official_visualizer_available": False,
                "kaggle_environment_error": f"{type(exc).__name__}: {exc}",
            }

    def all_cards(self) -> dict[str, Any]:
        return {"ok": True, "cards": [asdict(card) for card in self.cards]}

    def all_attacks(self) -> dict[str, Any]:
        return {"ok": True, "attacks": [asdict(attack) for attack in self.attacks]}

    def verify_environment(self) -> dict[str, Any]:
        script = r'''
import json
import kaggle_environments
from kaggle_environments import make
from kaggle_environments.envs.cabt import cabt

env = make("cabt", debug=False)
steps = env.run([cabt.random_agent, cabt.random_agent])
print("__CABT_VERIFY__" + json.dumps({
    "ok": True,
    "kaggle_environments": kaggle_environments.__version__,
    "cabt_environment_registered": "cabt" in kaggle_environments.environments,
    "steps": len(steps),
    "rewards": [state.reward for state in env.state],
    "statuses": [state.status for state in env.state],
}, separators=(",", ":")))
'''
        with self.lock:
            if self.session_id is not None:
                raise RuntimeError("finish the active battle before verifying the Kaggle environment")
            completed = subprocess.run(
                [sys.executable, "-c", script],
                check=False,
                capture_output=True,
                text=True,
                timeout=90,
            )
        marker = "__CABT_VERIFY__"
        line = next((line for line in reversed(completed.stdout.splitlines()) if line.startswith(marker)), "")
        if completed.returncode or not line:
            detail = (completed.stderr or completed.stdout or "verification produced no result")[-4000:]
            raise RuntimeError(f"Kaggle cabt verification failed: {detail}")
        result = json.loads(line.removeprefix(marker))
        result["official_visualizer_available"] = bool(
            self.kaggle_environment.get("official_visualizer_available")
        )
        result["execution"] = "kaggle_environments.make('cabt') random versus random"
        return result

    def start(self, payload: dict[str, Any]) -> dict[str, Any]:
        deck_a = _deck(payload.get("deck_a"), "deck_a")
        deck_b = _deck(payload.get("deck_b"), "deck_b")
        with self.lock:
            self._finish_unlocked()
            observation, start_data = self.game.battle_start(deck_a, deck_b)
            start = {
                "battlePtr": int(start_data.battlePtr or 0),
                "errorPlayer": int(start_data.errorPlayer),
                "errorType": int(start_data.errorType),
            }
            if observation is None:
                return {"ok": False, "error": "battle_start returned no observation", "start_data": start}
            self.session_id = uuid.uuid4().hex
            return {
                "ok": True,
                "session_id": self.session_id,
                "observation": observation,
                "start_data": start,
            }

    def select(self, payload: dict[str, Any]) -> dict[str, Any]:
        selection = payload.get("selection")
        if not isinstance(selection, list) or not all(type(value) is int for value in selection):
            raise ValueError("selection must be list[int]")
        with self.lock:
            self._require_session(payload)
            observation = self.game.battle_select(selection)
            return {"ok": True, "session_id": self.session_id, "observation": observation}

    def visualize(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            self._require_session(payload)
            return {"ok": True, "session_id": self.session_id, "visualizer": self.game.visualize_data()}

    def finish(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self.lock:
            requested = payload.get("session_id")
            if self.session_id is not None and requested not in (None, "", self.session_id):
                raise ValueError("stale or unknown session_id")
            was_active = self.session_id is not None
            self._finish_unlocked()
            return {"ok": True, "finished": was_active}

    def search_begin(self, payload: dict[str, Any]) -> dict[str, Any]:
        observation = payload.get("agent_observation")
        if not isinstance(observation, dict):
            raise ValueError("agent_observation must be an observation dictionary")
        with self.lock:
            if self.session_id is None:
                raise RuntimeError("no battle is active")
            state = self.api.search_begin(
                self.api.to_observation_class(observation),
                _int_list(payload.get("your_deck"), "your_deck"),
                _int_list(payload.get("your_prize"), "your_prize"),
                _int_list(payload.get("opponent_deck"), "opponent_deck"),
                _int_list(payload.get("opponent_prize"), "opponent_prize"),
                _int_list(payload.get("opponent_hand"), "opponent_hand"),
                _int_list(payload.get("opponent_active"), "opponent_active"),
                bool(payload.get("manual_coin")),
            )
            search_id = int(state.searchId)
            self.search_ids.add(search_id)
            return {"ok": True, "search_id": search_id, "observation": asdict(state.observation)}

    def search_step(self, payload: dict[str, Any]) -> dict[str, Any]:
        search_id = int(payload.get("search_id"))
        selection = _int_list(payload.get("selection"), "selection")
        with self.lock:
            if search_id not in self.search_ids:
                raise ValueError("stale or unknown search_id")
            state = self.api.search_step(search_id, selection)
            next_id = int(state.searchId)
            self.search_ids.add(next_id)
            return {"ok": True, "search_id": next_id, "observation": asdict(state.observation)}

    def search_release(self, payload: dict[str, Any]) -> dict[str, Any]:
        search_id = int(payload.get("search_id"))
        with self.lock:
            if search_id in self.search_ids:
                self.api.search_release(search_id)
                self.search_ids.discard(search_id)
            return {"ok": True, "released": search_id}

    def search_end(self) -> dict[str, Any]:
        with self.lock:
            if self.search_ids:
                self.api.search_end()
                self.search_ids.clear()
            return {"ok": True}

    def _require_session(self, payload: dict[str, Any]) -> None:
        if self.session_id is None:
            raise RuntimeError("no battle is active")
        if payload.get("session_id") != self.session_id:
            raise ValueError("stale or unknown session_id")

    def _finish_unlocked(self) -> None:
        if self.search_ids:
            try:
                self.api.search_end()
            finally:
                self.search_ids.clear()
        if self.session_id is None:
            return
        try:
            self.game.battle_finish()
        finally:
            self.session_id = None


def _deck(value: Any, name: str) -> list[int]:
    if not isinstance(value, list) or len(value) != 60 or not all(type(card_id) is int for card_id in value):
        raise ValueError(f"{name} must contain exactly 60 integer card IDs")
    return value


def _int_list(value: Any, name: str) -> list[int]:
    if not isinstance(value, list) or not all(type(item) is int for item in value):
        raise ValueError(f"{name} must be list[int]")
    return value


class WorkerServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], service: BattleService) -> None:
        super().__init__(address, WorkerHandler)
        self.service = service


class WorkerHandler(BaseHTTPRequestHandler):
    server: WorkerServer

    def do_GET(self) -> None:
        if self.path == "/health":
            self._run(self.server.service.health)
            return
        if self.path == "/metadata/cards":
            self._run(self.server.service.all_cards)
            return
        if self.path == "/metadata/attacks":
            self._run(self.server.service.all_attacks)
            return
        self._send({"ok": False, "error": "not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        routes = {
            "/battle/start": self.server.service.start,
            "/battle/select": self.server.service.select,
            "/battle/visualize": self.server.service.visualize,
            "/battle/finish": self.server.service.finish,
            "/search/begin": self.server.service.search_begin,
            "/search/step": self.server.service.search_step,
            "/search/release": self.server.service.search_release,
            "/search/end": lambda payload: self.server.service.search_end(),
            "/environment/verify": lambda payload: self.server.service.verify_environment(),
        }
        operation = routes.get(self.path)
        if operation is None:
            self._send({"ok": False, "error": "not found"}, HTTPStatus.NOT_FOUND)
            return
        self._run(lambda: operation(self._read_json()))

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def _run(self, operation: Any) -> None:
        try:
            self._send(operation())
        except (ValueError, IndexError) as exc:
            self._send({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            traceback.print_exc()
            self._send({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def _read_json(self) -> dict[str, Any]:
        raw_length = self.headers.get("Content-Length") or "0"
        try:
            length = int(raw_length)
        except ValueError as exc:
            raise ValueError("invalid Content-Length") from exc
        if length < 0 or length > MAX_REQUEST_BYTES:
            raise ValueError("request body is too large")
        raw = self.rfile.read(length)
        if not raw:
            return {}
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("JSON body must be an object")
        return value

    def _send(self, payload: dict[str, Any], status: int = HTTPStatus.OK) -> None:
        raw = json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def main() -> int:
    parser = argparse.ArgumentParser(description="HTTP bridge for the official cabt native engine.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8780)
    args = parser.parse_args()
    server = WorkerServer((args.host, args.port), BattleService())
    print(f"cabt engine worker listening on {args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.service.finish({})
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
