from __future__ import annotations

import json
import hashlib
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

from .remote_engine import DEFAULT_ENGINE_URL, remote_engine_health


VM_NAME = "ce"
CONTAINER_NAME = "cabt-engine-worker"
LIMA_HOME = Path.home() / ".cabt-lima"
KAGGLE_ENV_VERSION = "1.32.7"
RUNTIME_IMAGE = f"cabt-engine-runtime:{KAGGLE_ENV_VERSION}"
KAGGLE_WHEEL = f"kaggle_environments-{KAGGLE_ENV_VERSION}-py3-none-any.whl"
KAGGLE_WHEEL_URL = (
    "https://files.pythonhosted.org/packages/f1/a3/"
    "16f3211bec7d5b594619e4f53400111783cc0c1575343bef006485d02f64/"
    + KAGGLE_WHEEL
)
KAGGLE_WHEEL_SHA256 = "2a1bb862ad2d6463080f80f6a766f46d94b53fd57168cfeddb9857fc3dbc4c8f"


class LocalRuntimeManager:
    def __init__(self, root: Path, engine_url: str | None = None) -> None:
        self.root = root.resolve()
        self.engine_url = engine_url or os.getenv("CABT_ENGINE_URL") or DEFAULT_ENGINE_URL
        self.limactl = self.root / ".runtime" / "lima" / "bin" / "limactl"
        self.env = {**os.environ, "LIMA_HOME": str(LIMA_HOME)}

    def status(self) -> dict[str, Any]:
        health = remote_engine_health(self.engine_url, timeout_s=0.5)
        vm = self._vm_info()
        return {
            "available": bool(health.get("ok")),
            "engine_url": self.engine_url,
            "lima_installed": self.limactl.is_file(),
            "lima_path": str(self.limactl),
            "vm_name": VM_NAME,
            "vm_status": str(vm.get("status") or "Missing"),
            "vm_architecture": str(vm.get("arch") or ""),
            "rosetta_enabled": bool((((vm.get("config") or {}).get("vmOpts") or {}).get("vz") or {}).get("rosetta", {}).get("enabled")),
            "worker": health,
            "runtime_image": RUNTIME_IMAGE,
            "kaggle_environment_ready": bool(health.get("cabt_environment_registered")),
        }

    def start(self) -> dict[str, Any]:
        if remote_engine_health(self.engine_url, timeout_s=0.5).get("ok"):
            return {"ok": True, "detail": "Official cabt worker is already running.", "runtime": self.status()}
        if not self.limactl.is_file():
            return {"ok": False, "error": "Private Lima runtime is not installed. Run scripts/install_engine_runtime.sh once."}
        vm = self._vm_info()
        if not vm:
            return {"ok": False, "error": f"Lima VM {VM_NAME!r} is not provisioned. Run scripts/install_engine_runtime.sh once."}
        if vm.get("status") != "Running":
            self._run([str(self.limactl), "start", VM_NAME, "-y"], timeout=300)

        self._ensure_runtime_image()
        official_root = self._official_root()
        self._shell(["nerdctl", "rm", "-f", CONTAINER_NAME], timeout=30, check=False)
        command = [
            "nerdctl",
            "run",
            "-d",
            "--name",
            CONTAINER_NAME,
            "--platform=linux/amd64",
            "--device=lima-vm.io/rosetta=cached",
            "--net=host",
            "-v",
            f"{official_root}:/official:ro",
            "-v",
            f"{self.root}:/app:ro",
            "-e",
            "PYTHONPATH=/official",
            RUNTIME_IMAGE,
            "python",
            "/app/engine_worker/worker.py",
            "--host=0.0.0.0",
            "--port=8780",
        ]
        result = self._shell(command, timeout=180)
        deadline = time.monotonic() + 30.0
        health: dict[str, Any] = {}
        while time.monotonic() < deadline:
            health = remote_engine_health(self.engine_url, timeout_s=1.0)
            if health.get("ok"):
                return {
                    "ok": True,
                    "detail": "Official cabt worker started through Lima VZ and Rosetta.",
                    "container_id": result.stdout.strip(),
                    "runtime": self.status(),
                }
            time.sleep(0.5)
        logs = self._shell(["nerdctl", "logs", CONTAINER_NAME], timeout=20, check=False)
        return {
            "ok": False,
            "error": "The container started but the worker did not become healthy.",
            "health": health,
            "logs": (logs.stdout + logs.stderr)[-8000:],
        }

    def _ensure_runtime_image(self) -> None:
        inspected = self._shell(["nerdctl", "image", "inspect", RUNTIME_IMAGE], timeout=20, check=False)
        if inspected.returncode == 0:
            return
        downloads = self.root / ".runtime" / "downloads"
        dependencies = downloads / "kaggle-deps-amd64"
        downloads.mkdir(parents=True, exist_ok=True)
        dependencies.mkdir(parents=True, exist_ok=True)
        wheel = downloads / KAGGLE_WHEEL
        if not wheel.is_file() or _sha256(wheel) != KAGGLE_WHEEL_SHA256:
            with urllib.request.urlopen(KAGGLE_WHEEL_URL, timeout=120) as response:
                wheel.write_bytes(response.read())
        if _sha256(wheel) != KAGGLE_WHEEL_SHA256:
            raise RuntimeError("Downloaded kaggle-environments wheel failed its SHA-256 check.")
        requirements = self.root / "configs" / "kaggle-runtime-requirements.txt"
        required_names = {line.split("==", 1)[0].replace("-", "_").lower() for line in requirements.read_text().splitlines() if line.strip()}
        present_names = {path.name.split("-", 1)[0].replace("-", "_").lower() for path in dependencies.glob("*.whl")}
        if not required_names.issubset(present_names):
            self._run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "download",
                    "--only-binary=:all:",
                    "--platform=manylinux2014_x86_64",
                    "--python-version=311",
                    "--implementation=cp",
                    "--abi=cp311",
                    "--dest",
                    str(dependencies),
                    "--requirement",
                    str(requirements),
                ],
                timeout=300,
            )
        self._shell(
            [
                "nerdctl",
                "build",
                "--platform=linux/amd64",
                "--tag",
                RUNTIME_IMAGE,
                "--file",
                str(self.root / "configs" / "Dockerfile.kaggle-runtime"),
                str(downloads),
            ],
            timeout=900,
        )

    def stop(self) -> dict[str, Any]:
        if not self.limactl.is_file():
            return {"ok": True, "detail": "Lima is not installed; no worker was running."}
        self._shell(["nerdctl", "rm", "-f", CONTAINER_NAME], timeout=30, check=False)
        return {"ok": True, "detail": "Official cabt worker stopped.", "runtime": self.status()}

    def _official_root(self) -> Path:
        preferred = self.root.parent / "sample_submission"
        if (preferred / "cg" / "game.py").is_file() and (preferred / "cg" / "libcg.so").is_file():
            return preferred.resolve()
        for game_py in sorted(self.root.parent.rglob("cg/game.py")):
            candidate = game_py.parent.parent
            if (candidate / "cg" / "libcg.so").is_file():
                return candidate.resolve()
        raise RuntimeError("Could not find an official sample_submission/cg package with libcg.so.")

    def _vm_info(self) -> dict[str, Any]:
        if not self.limactl.is_file():
            return {}
        result = self._run([str(self.limactl), "list", VM_NAME, "--json"], timeout=15, check=False)
        if result.returncode != 0 or not result.stdout.strip():
            return {}
        try:
            value = json.loads(result.stdout.splitlines()[0])
        except json.JSONDecodeError:
            return {}
        return value if isinstance(value, dict) else {}

    def _shell(self, args: list[str], timeout: float, check: bool = True) -> subprocess.CompletedProcess[str]:
        return self._run([str(self.limactl), "shell", VM_NAME, *args], timeout=timeout, check=check)

    def _run(self, args: list[str], timeout: float, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            args,
            cwd=self.root,
            env=self.env,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=check,
        )


def effective_environment_report(root: Path) -> dict[str, Any]:
    """Describe the host and the process that actually executes official cabt."""
    from .engine import describe_environment

    host = describe_environment(root).to_dict()
    runtime = LocalRuntimeManager(root).status()
    worker = runtime.get("worker") or {}
    ready = bool(worker.get("ok"))
    return {
        "status": "ready" if ready else "official engine worker stopped",
        "execution_model": "macOS host -> localhost bridge -> Linux x86-64 official cg",
        "host_platform": host.get("platform", ""),
        "host_architecture": host.get("machine", ""),
        "host_python": host.get("python_version", ""),
        "host_cg_import": "not loaded directly (expected on macOS ARM)" if host.get("cg_package") == "missing" else host.get("cg_package", ""),
        "official_cg": "loaded in worker" if ready else "worker not running",
        "official_engine_api": "cg.game + cg.api" if ready else "unavailable until worker starts",
        "kaggle_environments": worker.get("kaggle_environments", "not loaded"),
        "cabt_environment": "registered" if worker.get("cabt_environment_registered") else "not registered",
        "official_visualizer": "available" if worker.get("official_visualizer_available") else "not available",
        "worker_service": worker.get("service", "not running"),
        "worker_architecture": worker.get("architecture", ""),
        "worker_python": worker.get("python", ""),
        "official_card_count": worker.get("card_count", 0),
        "official_attack_count": worker.get("attack_count", 0),
        "vm_status": runtime.get("vm_status", "Missing"),
        "vm_architecture": runtime.get("vm_architecture", ""),
        "rosetta_for_linux": "enabled" if runtime.get("rosetta_enabled") else "disabled",
        "native_core": "organizer libcg.so loaded successfully" if ready else host.get("native_library_note", ""),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
