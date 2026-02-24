#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _compose_file(root: Path) -> Path:
    yml = root / "docker-compose.yml"
    if yml.exists():
        return yml
    yaml = root / "docker-compose.yaml"
    if yaml.exists():
        return yaml
    raise FileNotFoundError("docker-compose.yml/docker-compose.yaml was not found")


def _require_binary(name: str) -> None:
    if shutil.which(name) is None:
        raise RuntimeError(f"Required binary is missing in PATH: {name}")


def _run(cmd: list[str], *, cwd: Path, env: dict[str, str]) -> int:
    process = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        check=False,
    )
    return int(process.returncode)


def _base_env(root: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("DATABASE_URL", "postgresql+asyncpg://oko:oko@127.0.0.1:5432/oko")
    env.setdefault("BROKER_URL", "amqp://oko:oko@127.0.0.1:5672/")
    env.setdefault("OKO_BOOTSTRAP_CONFIG_FILE", str(root / "_dashboard.yaml"))
    env.setdefault("OKO_EVENTS_KEEPALIVE_SEC", "15")
    env.setdefault("OKO_ACTIONS_EXECUTE_ENABLED", "true")
    env.setdefault("OKO_STORAGE_RPC_TIMEOUT_SEC", "2.0")
    env.setdefault("OKO_ACTION_RPC_TIMEOUT_SEC", "5.0")
    env.setdefault("OKO_BROKER_PREFETCH_COUNT", "32")
    env.setdefault("PYTHONPATH", "backend")
    return env


def _docker_cmd(*args: str) -> list[str]:
    return ["docker", "compose", *args]


def main() -> int:
    parser = argparse.ArgumentParser(description="Oko local/docker dev launcher")
    parser.add_argument(
        "target",
        choices=[
            "backend",
            "backend-allinone",
            "worker",
            "frontend",
            "infra-up",
            "infra-down",
            "docker-up",
            "docker-down",
            "migrate-local",
        ],
    )
    args = parser.parse_args()

    root = _project_root()
    env = _base_env(root)
    compose = _compose_file(root)

    if args.target in {"backend", "worker", "migrate-local"}:
        _require_binary("uv")
    if args.target == "frontend":
        _require_binary("npm")
    if args.target in {"infra-up", "infra-down", "docker-up", "docker-down"}:
        _require_binary("docker")

    if args.target in {"backend", "backend-allinone"}:
        env["OKO_RUNTIME_ROLE"] = "backend"
        if args.target == "backend-allinone":
            env["OKO_ENABLE_LOCAL_CONSUMERS"] = "true"
        host = env.get("OKO_BACKEND_HOST", "127.0.0.1")
        port = env.get("OKO_BACKEND_PORT", "8000")
        return _run(
            ["uv", "run", "uvicorn", "backend.main:app", "--host", host, "--port", port, "--reload"],
            cwd=root,
            env=env,
        )

    if args.target == "worker":
        env["OKO_RUNTIME_ROLE"] = "worker"
        return _run(
            ["uv", "run", "python", "-m", "oko.worker"],
            cwd=root,
            env=env,
        )

    if args.target == "frontend":
        host = env.get("OKO_FRONTEND_HOST", "127.0.0.1")
        port = env.get("OKO_FRONTEND_PORT", "5173")
        return _run(
            ["npm", "run", "dev", "--", "--host", host, "--port", port],
            cwd=root / "frontend",
            env=env,
        )

    if args.target == "infra-up":
        return _run(
            _docker_cmd("-f", str(compose), "up", "-d", "postgres", "rabbitmq"),
            cwd=root,
            env=env,
        )

    if args.target == "infra-down":
        return _run(
            _docker_cmd("-f", str(compose), "stop", "postgres", "rabbitmq"),
            cwd=root,
            env=env,
        )

    if args.target == "docker-up":
        return _run(
            _docker_cmd("-f", str(compose), "up", "--build"),
            cwd=root,
            env=env,
        )

    if args.target == "docker-down":
        return _run(
            _docker_cmd("-f", str(compose), "down", "--remove-orphans"),
            cwd=root,
            env=env,
        )

    if args.target == "migrate-local":
        return _run(
            ["uv", "run", "alembic", "-c", "alembic.ini", "upgrade", "head"],
            cwd=root,
            env=env,
        )

    return 2


if __name__ == "__main__":
    sys.exit(main())
