from __future__ import annotations

import asyncio
import os
import shutil
import socket
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO

import aio_pika
import asyncpg
import httpx
import pytest
from core.bus import BusClient, BusRpcTimeoutError, StorageBusConsumer
from core.bus.constants import ROUTING_EVENT_PUBLISH
from core.contracts.bus import BusMessageV1, EventPublishPayload, StorageTableUpsertPayload
from core.contracts.storage import PluginStorageConfig, StorageLimits, StorageTableSpec
from core.storage import UniversalStorage
from db.session import build_async_engine
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

DEFAULT_BOOTSTRAP = """\
version: 1
app:
  id: demo
  title: Demo
widgets:
  - type: system.status
"""

ROOT_DIR = Path(__file__).resolve().parents[3]
COMPOSE_FILE = ROOT_DIR / "tests" / "backend" / "integration" / "docker-compose.deps.yaml"

ALL_STORAGE_OPS = {
    "storage.kv.get",
    "storage.kv.set",
    "storage.kv.delete",
    "storage.table.get",
    "storage.table.upsert",
    "storage.table.delete",
    "storage.table.query",
}


def _event_headers() -> dict[str, str]:
    return {
        "X-Oko-Actor": "integration-tester",
        "X-Oko-Capabilities": "read.events",
    }


def _storage_config() -> PluginStorageConfig:
    return PluginStorageConfig(
        mode="core_universal",
        limits=StorageLimits(max_qps=1_000.0, max_query_limit=50),
        tables=[StorageTableSpec(name="devices", primary_key="id", indexes=["ip"])],
    )


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _docker_compose_command() -> tuple[str, ...]:
    if shutil.which("docker") is not None:
        probe = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            text=True,
            check=False,
        )
        if probe.returncode == 0:
            return ("docker", "compose")

    if shutil.which("docker-compose") is not None:
        probe = subprocess.run(
            ["docker-compose", "version"],
            capture_output=True,
            text=True,
            check=False,
        )
        if probe.returncode == 0:
            return ("docker-compose",)

    pytest.skip("Docker Compose is required for integration tests")


@dataclass(frozen=True)
class _ComposeDeps:
    command: tuple[str, ...]
    compose_file: Path
    project_name: str
    env: dict[str, str]
    database_url: str
    postgres_dsn: str
    broker_url: str

    def compose_cmd(self, *args: str) -> list[str]:
        return [*self.command, "-f", str(self.compose_file), "-p", self.project_name, *args]


@dataclass
class _ServiceProcess:
    name: str
    process: subprocess.Popen[str]
    log_path: Path
    log_handle: TextIO


def _run_compose(stack: _ComposeDeps, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    process = subprocess.run(
        stack.compose_cmd(*args),
        cwd=ROOT_DIR,
        env=stack.env,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and process.returncode != 0:
        raise RuntimeError(
            f"docker compose {' '.join(args)} failed (exit={process.returncode})\n"
            f"STDOUT:\n{process.stdout}\nSTDERR:\n{process.stderr}"
        )
    return process


async def _wait_for_postgres(postgres_dsn: str, timeout_sec: float) -> None:
    deadline = asyncio.get_running_loop().time() + timeout_sec
    last_error: Exception | None = None
    while asyncio.get_running_loop().time() < deadline:
        try:
            connection = await asyncpg.connect(postgres_dsn, timeout=2.0)
            try:
                await connection.execute("SELECT 1")
            finally:
                await connection.close()
            return
        except Exception as exc:  # pragma: no cover - transient infrastructure errors
            last_error = exc
            await asyncio.sleep(1.0)

    raise RuntimeError(f"Postgres did not become ready in {timeout_sec:.0f}s: {last_error}")


async def _wait_for_rabbitmq(broker_url: str, timeout_sec: float) -> None:
    deadline = asyncio.get_running_loop().time() + timeout_sec
    last_error: Exception | None = None
    while asyncio.get_running_loop().time() < deadline:
        try:
            connection = await aio_pika.connect_robust(broker_url, timeout=2.0)
            await connection.close()
            return
        except Exception as exc:  # pragma: no cover - transient infrastructure errors
            last_error = exc
            await asyncio.sleep(1.0)

    raise RuntimeError(f"RabbitMQ did not become ready in {timeout_sec:.0f}s: {last_error}")


async def _wait_for_backend_health(base_url: str, timeout_sec: float) -> None:
    deadline = asyncio.get_running_loop().time() + timeout_sec
    last_error: Exception | None = None
    async with httpx.AsyncClient(timeout=3.0) as client:
        while asyncio.get_running_loop().time() < deadline:
            try:
                response = await client.get(f"{base_url}/api/v1/health")
                if response.status_code == httpx.codes.OK:
                    return
                last_error = RuntimeError(f"Unexpected status: {response.status_code}")
            except Exception as exc:  # pragma: no cover - transient startup errors
                last_error = exc
            await asyncio.sleep(1.0)

    raise RuntimeError(f"Backend health endpoint did not become ready in {timeout_sec:.0f}s: {last_error}")


async def _collect_stream_until(
    stream_iter: Any,
    *,
    contains: tuple[str, ...],
    timeout_sec: float,
) -> str:
    deadline = asyncio.get_running_loop().time() + timeout_sec
    buffer = ""
    while True:
        if all(token in buffer for token in contains):
            return buffer
        remaining = deadline - asyncio.get_running_loop().time()
        if remaining <= 0:
            raise AssertionError(f"Timed out waiting for SSE tokens: {contains}")
        try:
            chunk = await asyncio.wait_for(anext(stream_iter), timeout=remaining)
        except StopAsyncIteration as exc:
            raise AssertionError(f"SSE stream ended before receiving tokens: {contains}") from exc
        buffer += chunk


async def _wait_for_storage_row(postgres_dsn: str, probe_id: str, timeout_sec: float) -> None:
    deadline = asyncio.get_running_loop().time() + timeout_sec
    last_error: Exception | None = None
    while asyncio.get_running_loop().time() < deadline:
        connection = None
        try:
            connection = await asyncpg.connect(postgres_dsn, timeout=3.0)
            row = await connection.fetchrow(
                """
                SELECT pk
                FROM plugin_rows
                WHERE plugin_id = 'autodiscover'
                  AND "table" = 'devices'
                  AND row_json LIKE '%' || $1 || '%'
                LIMIT 1
                """,
                probe_id,
            )
            if row is not None:
                return
        except Exception as exc:  # pragma: no cover - transient DB startup/visibility delays
            last_error = exc
        finally:
            if connection is not None:
                await connection.close()
        await asyncio.sleep(0.5)

    raise RuntimeError(f"Storage row was not persisted in {timeout_sec:.0f}s (last_error={last_error})")


async def _storage_upsert_rpc_with_retry(
    *,
    caller_bus: BusClient,
    probe_id: str,
    attempts: int = 3,
    timeout_sec: float = 20.0,
) -> None:
    payload = StorageTableUpsertPayload(
        table="devices",
        row={"id": probe_id, "ip": "127.0.0.1"},
    )
    last_error: Exception | None = None

    for index in range(attempts):
        try:
            reply = await caller_bus.call(
                message=BusMessageV1(
                    type="storage.table.upsert",
                    plugin_id="autodiscover",
                    payload=payload.model_dump(mode="json"),
                ),
                routing_key="storage.table.upsert",
                timeout_sec=timeout_sec,
            )
            assert reply.ok is True
            return
        except BusRpcTimeoutError as exc:
            last_error = exc
            if index + 1 < attempts:
                await asyncio.sleep(1.0)
                continue
            raise

    raise AssertionError(f"RPC upsert failed after retries: {last_error}")


def _start_service_process(
    *,
    name: str,
    cmd: list[str],
    env: dict[str, str],
    logs_dir: Path,
) -> _ServiceProcess:
    log_path = logs_dir / f"{name}.log"
    log_handle = log_path.open("w", encoding="utf-8")
    process_env = env.copy()
    process_env.setdefault("PYTHONUNBUFFERED", "1")
    process = subprocess.Popen(
        cmd,
        cwd=ROOT_DIR,
        env=process_env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return _ServiceProcess(name=name, process=process, log_path=log_path, log_handle=log_handle)


def _stop_service_process(service: _ServiceProcess) -> None:
    try:
        if service.process.poll() is None:
            service.process.terminate()
            try:
                service.process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                service.process.kill()
                service.process.wait(timeout=10)
    finally:
        service.log_handle.close()


def _log_tail(path: Path, lines: int = 120) -> str:
    if not path.exists():
        return ""
    content = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(content[-lines:])


async def _dispose_engine(engine: AsyncEngine | None) -> None:
    if engine is not None:
        await engine.dispose()


@pytest.fixture
def compose_deps() -> _ComposeDeps:
    if os.getenv("OKO_RUN_INTEGRATION") != "1":
        pytest.skip("Set OKO_RUN_INTEGRATION=1 to run Docker Compose integration tests")

    command = _docker_compose_command()
    postgres_port = _get_free_port()
    amqp_port = _get_free_port()
    project_name = f"oko-it-{uuid.uuid4().hex[:8]}"

    env = os.environ.copy()
    env["OKO_ITEST_PG_PORT"] = str(postgres_port)
    env["OKO_ITEST_AMQP_PORT"] = str(amqp_port)

    postgres_dsn = f"postgresql://oko:oko@127.0.0.1:{postgres_port}/oko"
    database_url = f"postgresql+asyncpg://oko:oko@127.0.0.1:{postgres_port}/oko"
    broker_url = f"amqp://oko:oko@127.0.0.1:{amqp_port}/"
    stack = _ComposeDeps(
        command=command,
        compose_file=COMPOSE_FILE,
        project_name=project_name,
        env=env,
        postgres_dsn=postgres_dsn,
        database_url=database_url,
        broker_url=broker_url,
    )

    _run_compose(stack, "up", "-d")
    try:
        asyncio.run(_wait_for_postgres(postgres_dsn, timeout_sec=120.0))
        asyncio.run(_wait_for_rabbitmq(broker_url, timeout_sec=120.0))
        yield stack
    finally:
        _run_compose(stack, "down", "-v", "--remove-orphans", check=False)


async def test_compose_postgres_rabbitmq_rpc_and_sse_e2e(
    tmp_path: Path,
    compose_deps: _ComposeDeps,
) -> None:
    bootstrap = (tmp_path / "bootstrap.yaml").resolve()
    bootstrap.write_text(DEFAULT_BOOTSTRAP, encoding="utf-8")
    logs_dir = (tmp_path / "logs").resolve()
    logs_dir.mkdir(parents=True, exist_ok=True)

    backend_port = _get_free_port()
    base_url = f"http://127.0.0.1:{backend_port}"
    probe_id = f"it-{uuid.uuid4().hex[:10]}"

    env_base = os.environ.copy()
    env_base["DATABASE_URL"] = compose_deps.database_url
    env_base["BROKER_URL"] = compose_deps.broker_url
    env_base["OKO_BOOTSTRAP_CONFIG_FILE"] = str(bootstrap)
    env_base["OKO_EVENTS_KEEPALIVE_SEC"] = "3"
    env_base["PYTHONPATH"] = "backend"

    backend_env = env_base.copy()
    backend_env["OKO_RUNTIME_ROLE"] = "backend"
    backend = _start_service_process(
        name="backend",
        cmd=["uv", "run", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", str(backend_port)],
        env=backend_env,
        logs_dir=logs_dir,
    )

    storage_engine: AsyncEngine | None = None
    consumer_bus: BusClient | None = None
    caller_bus: BusClient | None = None
    storage_consumer: StorageBusConsumer | None = None

    try:
        await _wait_for_backend_health(base_url, timeout_sec=90.0)

        storage_engine = build_async_engine(compose_deps.database_url)
        session_factory = async_sessionmaker(
            bind=storage_engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

        config = _storage_config()
        consumer_bus = BusClient(broker_url=compose_deps.broker_url, prefetch_count=16)
        await consumer_bus.connect()
        storage = UniversalStorage(session_factory=session_factory, plugin_configs={"autodiscover": config})
        storage_consumer = StorageBusConsumer(
            bus_client=consumer_bus,
            storage=storage,
            plugin_configs={"autodiscover": config},
            capabilities={"autodiscover": set(ALL_STORAGE_OPS)},
        )
        await storage_consumer.start()

        caller_bus = BusClient(broker_url=compose_deps.broker_url, prefetch_count=16)
        await caller_bus.connect()

        await _storage_upsert_rpc_with_retry(
            caller_bus=caller_bus,
            probe_id=probe_id,
        )

        await _wait_for_storage_row(compose_deps.postgres_dsn, probe_id=probe_id, timeout_sec=15.0)

        timeout = httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=10.0)
        async with (
            httpx.AsyncClient(base_url=base_url, timeout=timeout) as stream_client,
            stream_client.stream("GET", "/api/v1/events/stream", headers=_event_headers()) as stream_response,
        ):
            assert stream_response.status_code == httpx.codes.OK
            stream_iter = stream_response.aiter_text()

            snapshot_payload = await _collect_stream_until(
                stream_iter,
                contains=("event: core.state.snapshot",),
                timeout_sec=20.0,
            )
            assert "event: core.state.snapshot" in snapshot_payload

            integration_event = EventPublishPayload(
                event_type="integration.bus.event",
                source="tests.integration",
                payload={"probe_id": probe_id},
            )
            await caller_bus.emit(
                message=BusMessageV1(
                    type="event.publish",
                    plugin_id="core",
                    payload=integration_event.model_dump(mode="json"),
                ),
                routing_key=ROUTING_EVENT_PUBLISH,
            )

            events_payload = await _collect_stream_until(
                stream_iter,
                contains=("event: integration.bus.event", probe_id),
                timeout_sec=30.0,
            )
            assert "event: integration.bus.event" in events_payload
            assert probe_id in events_payload
    except Exception as exc:
        backend_tail = _log_tail(backend.log_path)
        raise AssertionError(
            f"Integration flow failed: {exc}\n\n"
            f"Backend log tail:\n{backend_tail}"
        ) from exc
    finally:
        if storage_consumer is not None:
            await storage_consumer.stop()
        if caller_bus is not None:
            await caller_bus.close()
        if consumer_bus is not None:
            await consumer_bus.close()
        await _dispose_engine(storage_engine)
        _stop_service_process(backend)
