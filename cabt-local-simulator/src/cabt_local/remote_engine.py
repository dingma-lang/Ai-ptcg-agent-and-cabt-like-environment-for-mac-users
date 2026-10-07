from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .engine import CabtInitializationError, CabtUnavailable


DEFAULT_ENGINE_URL = "http://127.0.0.1:8780"


@dataclass(frozen=True)
class RemoteStartData:
    battlePtr: int = 0
    errorPlayer: int = 0
    errorType: int = 0


class RemoteCabtGame:
    """Client with the same battle methods as the organizer's cg.game wrapper."""

    def __init__(self, base_url: str | None = None, timeout_s: float = 15.0) -> None:
        self.base_url = (base_url or os.getenv("CABT_ENGINE_URL") or DEFAULT_ENGINE_URL).rstrip("/")
        self.timeout_s = timeout_s
        self.session_id: str | None = None

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def verify_environment(self) -> dict[str, Any]:
        return self._request("POST", "/environment/verify", {})

    def battle_start(self, deck_a: list[int], deck_b: list[int]) -> tuple[dict | None, RemoteStartData]:
        data = self._request("POST", "/battle/start", {"deck_a": deck_a, "deck_b": deck_b}, allow_engine_error=True)
        start = data.get("start_data") or {}
        start_data = RemoteStartData(
            battlePtr=int(start.get("battlePtr") or 0),
            errorPlayer=int(start.get("errorPlayer") or 0),
            errorType=int(start.get("errorType") or 0),
        )
        if not data.get("ok"):
            return None, start_data
        self.session_id = str(data["session_id"])
        observation = data.get("observation")
        return observation if isinstance(observation, dict) else None, start_data

    def battle_select(self, selection: list[int]) -> dict:
        data = self._request(
            "POST",
            "/battle/select",
            {"session_id": self._session(), "selection": selection},
        )
        observation = data.get("observation")
        if not isinstance(observation, dict):
            raise CabtInitializationError("engine worker returned an invalid observation")
        return observation

    def visualize_data(self) -> str:
        data = self._request("POST", "/battle/visualize", {"session_id": self._session()})
        return str(data.get("visualizer") or "")

    def battle_finish(self) -> None:
        session_id = self.session_id
        self.session_id = None
        if session_id is None:
            return
        self._request("POST", "/battle/finish", {"session_id": session_id})

    def _session(self) -> str:
        if self.session_id is None:
            raise CabtInitializationError("no remote cabt battle is active")
        return self.session_id

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        allow_engine_error: bool = False,
    ) -> dict[str, Any]:
        raw = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
        request = Request(
            self.base_url + path,
            data=raw,
            method=method,
            headers={"Content-Type": "application/json"} if raw is not None else {},
        )
        try:
            with urlopen(request, timeout=self.timeout_s) as response:
                value = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise CabtUnavailable(f"cabt worker HTTP {exc.code}: {detail}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise CabtUnavailable(f"cabt worker unavailable at {self.base_url}: {exc}") from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise CabtUnavailable(f"cabt worker returned invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise CabtUnavailable("cabt worker response was not an object")
        if not value.get("ok") and not allow_engine_error:
            raise CabtUnavailable(str(value.get("error") or "cabt worker request failed"))
        return value


def remote_engine_health(base_url: str | None = None, timeout_s: float = 1.0) -> dict[str, Any]:
    try:
        return RemoteCabtGame(base_url=base_url, timeout_s=timeout_s).health()
    except CabtUnavailable as exc:
        return {"ok": False, "error": str(exc)}


class RemoteCabtSearch:
    def __init__(self, base_url: str | None = None, timeout_s: float = 15.0) -> None:
        self.client = RemoteCabtGame(base_url=base_url, timeout_s=timeout_s)

    def search_begin(self, **inputs: Any) -> dict[str, Any]:
        return self.client._request("POST", "/search/begin", inputs)

    def search_step(self, search_id: int, selection: list[int]) -> dict[str, Any]:
        return self.client._request(
            "POST", "/search/step", {"search_id": search_id, "selection": selection}
        )

    def search_release(self, search_id: int) -> None:
        self.client._request("POST", "/search/release", {"search_id": search_id})

    def search_end(self) -> None:
        self.client._request("POST", "/search/end", {})


class RemoteCabtMetadata:
    def __init__(self, base_url: str | None = None, timeout_s: float = 15.0) -> None:
        self.client = RemoteCabtGame(base_url=base_url, timeout_s=timeout_s)

    def all_card_data(self) -> list[dict[str, Any]]:
        value = self.client._request("GET", "/metadata/cards")
        cards = value.get("cards")
        if not isinstance(cards, list):
            raise CabtUnavailable("cabt worker returned invalid card metadata")
        return cards

    def all_attack(self) -> list[dict[str, Any]]:
        value = self.client._request("GET", "/metadata/attacks")
        attacks = value.get("attacks")
        if not isinstance(attacks, list):
            raise CabtUnavailable("cabt worker returned invalid attack metadata")
        return attacks
