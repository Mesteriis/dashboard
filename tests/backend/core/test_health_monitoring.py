from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from apps.health.bus_handlers.check_result_consumer import HealthCheckResultConsumer
from apps.health.model.contracts import (
    HealthCheckRequestedV1,
    HealthCheckResultV1,
    HealthSample,
    MonitoredServiceSpec,
)
from apps.health.service.checkers import HealthChecker
from apps.health.service.config_sync import extract_service_specs_from_config
from apps.health.service.repository import HealthRepository
from apps.health.service.status import evaluate_health
from apps.health.worker.scheduler import HealthScheduler
from core.bus.client import BusClient
from core.contracts.bus import BusMessageV1
from core.events import BrokerEventPublisher, EventBus, EventPublishConsumer
from core.storage.models import (
    ActionRow,
    AppStateRow,
    AuditLogRow,
    ConfigRevisionRow,
    PluginIndexRow,
    PluginKvRow,
    PluginRow,
)
from core.storage.repositories import ConfigRepository
from db.base import Base
from db.session import build_async_engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

pytestmark = pytest.mark.asyncio


async def _session_factory(tmp_path: Path) -> async_sessionmaker[AsyncSession]:
    _ = (
        ActionRow,
        AppStateRow,
        AuditLogRow,
        ConfigRevisionRow,
        PluginKvRow,
        PluginRow,
        PluginIndexRow,
    )
    db_path = (tmp_path / "health-monitoring.sqlite3").resolve()
    engine = build_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return async_sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


async def _dispose(session_factory: async_sessionmaker[AsyncSession]) -> None:
    bind = session_factory.kw.get("bind")
    if isinstance(bind, AsyncEngine):
        await bind.dispose()


async def test_http_200_results_in_online(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_verify_values: list[object] = []

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            _ = (exc_type, exc, tb)
            return False

        async def get(self, url: str):
            _ = url
            return SimpleNamespace(status_code=200)

    def _build_client(**kwargs):
        captured_verify_values.append(kwargs.get("verify"))
        return _Client()

    monkeypatch.setattr(httpx, "AsyncClient", _build_client)
    checker = HealthChecker(icmp_enabled=False)
    request = HealthCheckRequestedV1(
        service_id=uuid4(),
        item_id="svc-http",
        check_type="http",
        target="https://example.local",
        timeout_ms=1500,
        latency_threshold_ms=800,
        window_size=1,
    )
    result = await checker.run(request)
    assert result.success is True
    assert captured_verify_values == [True]
    state = evaluate_health(
        samples=[
            HealthSample(
                id=1,
                service_id=result.service_id,
                ts=result.checked_at,
                success=result.success,
                latency_ms=result.latency_ms,
                error_message=result.error_message,
            )
        ],
        latency_threshold_ms=800,
        window_size=1,
    )
    assert state.status == "online"


async def test_timeout_results_in_down() -> None:
    now = datetime.now(UTC)
    service_id = uuid4()
    state = evaluate_health(
        samples=[
            HealthSample(
                id=1,
                service_id=service_id,
                ts=now,
                success=False,
                latency_ms=None,
                error_message="timeout",
            )
        ],
        latency_threshold_ms=800,
        window_size=1,
    )
    assert state.status == "down"


async def test_http_checker_can_disable_tls_verification(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_verify_values: list[object] = []

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            _ = (exc_type, exc, tb)
            return False

        async def get(self, url: str):
            _ = url
            return SimpleNamespace(status_code=200)

    def _build_client(**kwargs):
        captured_verify_values.append(kwargs.get("verify"))
        return _Client()

    monkeypatch.setattr(httpx, "AsyncClient", _build_client)
    checker = HealthChecker(icmp_enabled=False)
    request = HealthCheckRequestedV1(
        service_id=uuid4(),
        item_id="svc-http-insecure",
        check_type="http",
        target="https://insecure.local",
        timeout_ms=1500,
        latency_threshold_ms=800,
        tls_verify=False,
        window_size=1,
    )
    result = await checker.run(request)
    assert result.success is True
    assert captured_verify_values == [False]


async def test_fifty_percent_failures_results_in_degraded() -> None:
    now = datetime.now(UTC)
    service_id = uuid4()
    state = evaluate_health(
        samples=[
            HealthSample(
                id=2,
                service_id=service_id,
                ts=now,
                success=False,
                latency_ms=None,
                error_message="timeout",
            ),
            HealthSample(
                id=1,
                service_id=service_id,
                ts=now - timedelta(minutes=5),
                success=True,
                latency_ms=90,
                error_message=None,
            ),
        ],
        latency_threshold_ms=800,
        window_size=2,
    )
    assert state.status == "degraded"
    assert state.success_rate == 0.5


async def test_status_changes_publish_event(tmp_path: Path) -> None:
    session_factory = await _session_factory(tmp_path)
    bus_client = BusClient(broker_url="memory://health")
    repository = HealthRepository(session_factory)
    event_bus = EventBus()
    event_publish_consumer = EventPublishConsumer(bus_client=bus_client, event_bus=event_bus)
    result_consumer = HealthCheckResultConsumer(
        bus_client=bus_client,
        repository=repository,
        event_publisher=BrokerEventPublisher(bus_client=bus_client),
        window_size=1,
    )

    service_id = uuid4()
    await repository.sync_services(
        [
            MonitoredServiceSpec(
                id=service_id,
                item_id="svc-status",
                name="svc-status",
                check_type="http",
                target="https://example.local",
                interval_sec=300,
                timeout_ms=1500,
                latency_threshold_ms=800,
                enabled=True,
            )
        ]
    )

    queue = event_bus.subscribe()
    try:
        await bus_client.connect()
        await event_publish_consumer.start()
        await result_consumer.start()

        online_result = HealthCheckResultV1(
            service_id=service_id,
            item_id="svc-status",
            check_type="http",
            target="https://example.local",
            success=True,
            latency_ms=120,
            error_message=None,
        )
        await bus_client.emit(
            message=BusMessageV1(
                type="health.check.result",
                plugin_id="core.health",
                payload=online_result.model_dump(mode="json"),
            ),
            routing_key="health.check.result",
        )
        first_event = await asyncio.wait_for(queue.get(), timeout=2.0)
        assert first_event.type == "health.status.changed"
        assert first_event.payload["item_id"] == "svc-status"
        assert first_event.payload["current_status"] == "online"

        down_result = online_result.model_copy(
            update={
                "success": False,
                "latency_ms": None,
                "error_message": "timeout",
                "checked_at": datetime.now(UTC),
            }
        )
        await bus_client.emit(
            message=BusMessageV1(
                type="health.check.result",
                plugin_id="core.health",
                payload=down_result.model_dump(mode="json"),
            ),
            routing_key="health.check.result",
        )
        second_event = await asyncio.wait_for(queue.get(), timeout=2.0)
        assert second_event.type == "health.status.changed"
        assert second_event.payload["current_status"] == "down"

        repeated_down_result = down_result.model_copy(
            update={
                "checked_at": datetime.now(UTC),
            }
        )
        await bus_client.emit(
            message=BusMessageV1(
                type="health.check.result",
                plugin_id="core.health",
                payload=repeated_down_result.model_dump(mode="json"),
            ),
            routing_key="health.check.result",
        )
        third_event = await asyncio.wait_for(queue.get(), timeout=2.0)
        assert third_event.type == "health.status.updated"
        assert third_event.payload["current_status"] == "down"
    finally:
        event_bus.unsubscribe(queue)
        await result_consumer.stop()
        await event_publish_consumer.stop()
        await bus_client.close()
        await _dispose(session_factory)


async def test_retention_deletes_old_samples(tmp_path: Path) -> None:
    session_factory = await _session_factory(tmp_path)
    repository = HealthRepository(session_factory)
    service_id = uuid4()
    await repository.sync_services(
        [
            MonitoredServiceSpec(
                id=service_id,
                item_id="svc-retention",
                name="svc-retention",
                check_type="http",
                target="https://example.local",
                interval_sec=300,
                timeout_ms=1500,
                latency_threshold_ms=800,
                enabled=True,
            )
        ]
    )

    old_sample = HealthCheckResultV1(
        service_id=service_id,
        item_id="svc-retention",
        check_type="http",
        target="https://example.local",
        success=True,
        latency_ms=10,
        checked_at=datetime.now(UTC) - timedelta(days=10),
    )
    new_sample = old_sample.model_copy(update={"checked_at": datetime.now(UTC), "latency_ms": 20})
    await repository.insert_sample(old_sample)
    await repository.insert_sample(new_sample)

    deleted = await repository.delete_samples_older_than(datetime.now(UTC) - timedelta(days=7))
    latest = await repository.list_latest_samples(service_id, limit=10)

    assert deleted >= 1
    assert len(latest) == 1
    assert latest[0].latency_ms == 20
    await _dispose(session_factory)


async def test_disabled_service_not_scheduled(tmp_path: Path) -> None:
    session_factory = await _session_factory(tmp_path)
    repository = HealthRepository(session_factory)
    config_repository = ConfigRepository(session_factory)
    bus_client = BusClient(broker_url="memory://health")
    captured_item_ids: list[str] = []

    async def _capture(message):
        parsed = BusMessageV1.model_validate_json(message.body.decode("utf-8"))
        if parsed.type == "health.check.request":
            captured_item_ids.append(str(parsed.payload.get("item_id", "")))

    scheduler = HealthScheduler(
        bus_client=bus_client,
        repository=repository,
        config_repository=config_repository,
        tick_sec=0.05,
        heartbeat_sec=0.2,
        window_size=10,
        retention_days=7,
        default_interval_sec=300,
        default_timeout_ms=1500,
        default_latency_threshold_ms=800,
    )

    payload = {
        "version": 1,
        "groups": [
            {
                "id": "core",
                "subgroups": [
                    {
                        "id": "main",
                        "items": [
                            {
                                "id": "svc-enabled",
                                "title": "Enabled",
                                "url": "https://enabled.local",
                                "monitor_health": True,
                            },
                            {
                                "id": "svc-disabled",
                                "title": "Disabled",
                                "url": "https://disabled.local",
                                "monitor_health": False,
                            },
                        ],
                    }
                ],
            }
        ],
    }
    await config_repository.create_revision(payload=payload, source="bootstrap", actor="test")

    try:
        await bus_client.connect()
        await bus_client.consume(
            queue_name="test.health.capture",
            binding_keys=("health.check.request",),
            callback=_capture,
            durable=False,
        )
        await scheduler.start()
        await asyncio.sleep(0.25)
    finally:
        await scheduler.stop()
        await bus_client.close()
        await _dispose(session_factory)

    assert "svc-enabled" in captured_item_ids
    assert "svc-disabled" not in captured_item_ids


async def test_config_sync_respects_monitor_flag_and_fixed_interval() -> None:
    payload = {
        "groups": [
            {
                "id": "core",
                "subgroups": [
                    {
                        "id": "main",
                        "items": [
                            {
                                "id": "svc-http",
                                "type": "link",
                                "title": "HTTP",
                                "url": "https://service.local",
                                "check_url": "https://service.local/healthz",
                                "monitor_health": True,
                                "healthcheck": {
                                    "type": "http",
                                    "interval_sec": 5,
                                    "timeout_ms": 900,
                                    "tls_verify": False,
                                },
                            },
                            {
                                "id": "svc-disabled",
                                "type": "link",
                                "title": "Disabled",
                                "url": "https://disabled.local",
                                "monitor_health": "false",
                                "healthcheck": {
                                    "type": "http",
                                    "url": "https://disabled.local/healthz",
                                },
                            },
                            {
                                "id": "svc-iframe",
                                "type": "iframe",
                                "title": "Iframe",
                                "url": "https://iframe.local",
                                "monitor_health": True,
                                "healthcheck": {
                                    "insecure_skip_verify": True,
                                },
                            },
                            {
                                "id": "svc-private-ip",
                                "type": "iframe",
                                "title": "Private IP",
                                "url": "https://192.168.10.20/",
                                "monitor_health": True,
                            },
                        ],
                    }
                ],
            }
        ]
    }

    specs = extract_service_specs_from_config(
        config_payload=payload,
        default_interval_sec=300,
        default_timeout_ms=1500,
        default_latency_threshold_ms=800,
    )

    spec_by_item = {spec.item_id: spec for spec in specs}
    assert set(spec_by_item) == {"svc-http", "svc-disabled", "svc-iframe", "svc-private-ip"}

    enabled_spec = spec_by_item["svc-http"]
    assert enabled_spec.enabled is True
    assert enabled_spec.interval_sec == 300
    assert enabled_spec.target == "https://service.local/healthz"
    assert enabled_spec.timeout_ms == 900
    assert enabled_spec.tls_verify is False

    disabled_spec = spec_by_item["svc-disabled"]
    assert disabled_spec.enabled is False
    assert disabled_spec.interval_sec == 300
    assert disabled_spec.tls_verify is True

    iframe_spec = spec_by_item["svc-iframe"]
    assert iframe_spec.enabled is True
    assert iframe_spec.target == "https://iframe.local"
    assert iframe_spec.tls_verify is False

    private_ip_spec = spec_by_item["svc-private-ip"]
    assert private_ip_spec.enabled is True
    assert private_ip_spec.target == "https://192.168.10.20/"
    assert private_ip_spec.tls_verify is False
