from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from apps.health.model.contracts import HealthCheckResultV1, MonitoredServiceSpec
from apps.health.model.sqlalchemy import HealthSampleRow, MonitoredServiceRow, ServiceHealthStateRow
from apps.health.service.repository import HealthRepository, _as_utc
from db.base import Base
from db.session import build_async_engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

pytestmark = pytest.mark.asyncio


async def _session_factory(tmp_path: Path) -> async_sessionmaker[AsyncSession]:
    _ = (MonitoredServiceRow, HealthSampleRow, ServiceHealthStateRow)
    db_path = (tmp_path / "health-repository.sqlite3").resolve()
    engine = build_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return async_sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


async def _dispose(session_factory: async_sessionmaker[AsyncSession]) -> None:
    bind = session_factory.kw.get("bind")
    if isinstance(bind, AsyncEngine):
        await bind.dispose()


def _spec(
    service_id: UUID,
    *,
    item_id: str,
    name: str,
    enabled: bool = True,
    target: str = "https://example.local",
) -> MonitoredServiceSpec:
    return MonitoredServiceSpec(
        id=service_id,
        item_id=item_id,
        name=name,
        check_type="http",
        target=target,
        interval_sec=60,
        timeout_ms=1000,
        latency_threshold_ms=250,
        tls_verify=True,
        enabled=enabled,
    )


async def test_service_crud_and_listing(tmp_path: Path) -> None:
    session_factory = await _session_factory(tmp_path)
    repository = HealthRepository(session_factory)
    missing_id = uuid4()
    try:
        created_b = await repository.create_service(
            item_id="svc-b",
            name="B Service",
            check_type="tcp",
            target="127.0.0.1:443",
            interval_sec=45,
            timeout_ms=1200,
            latency_threshold_ms=200,
            tls_verify=False,
            enabled=False,
        )
        created_a = await repository.create_service(
            item_id="svc-a",
            name="A Service",
            check_type="http",
            target="https://a.local",
            interval_sec=30,
            timeout_ms=800,
            latency_threshold_ms=150,
            enabled=True,
        )

        all_services = await repository.list_services()
        assert [service.name for service in all_services] == ["A Service", "B Service"]

        enabled_services = await repository.list_enabled_services()
        assert [service.item_id for service in enabled_services] == ["svc-a"]

        assert await repository.get_service(missing_id) is None

        no_patch = await repository.update_service(created_a.id, {})
        assert no_patch is not None
        assert no_patch.name == "A Service"

        patched = await repository.update_service(
            created_a.id,
            {"name": "A Service v2", "enabled": False, "unknown_field": "ignored"},
        )
        assert patched is not None
        assert patched.name == "A Service v2"
        assert patched.enabled is False

        assert await repository.update_service(missing_id, {"name": "ghost"}) is None
        assert await repository.delete_service(missing_id) is False
        assert await repository.delete_service(created_b.id) is True
    finally:
        await _dispose(session_factory)


async def test_sync_services_updates_and_disables_removed_rows(tmp_path: Path) -> None:
    session_factory = await _session_factory(tmp_path)
    repository = HealthRepository(session_factory)
    service_a = uuid4()
    service_b = uuid4()
    service_c = uuid4()
    try:
        await repository.sync_services(
            [
                _spec(service_a, item_id="svc-a", name="Service A", enabled=True),
                _spec(service_b, item_id="svc-b", name="Service B", enabled=True),
            ]
        )
        await repository.sync_services(
            [
                _spec(service_a, item_id="svc-a-updated", name="Service A+", enabled=False, target="https://a2.local"),
                _spec(service_c, item_id="svc-c", name="Service C", enabled=True),
            ]
        )

        reloaded_a = await repository.get_service(service_a)
        reloaded_b = await repository.get_service(service_b)
        reloaded_c = await repository.get_service(service_c)
        assert reloaded_a is not None
        assert reloaded_a.item_id == "svc-a-updated"
        assert reloaded_a.target == "https://a2.local"
        assert reloaded_a.enabled is False
        assert reloaded_b is not None
        assert reloaded_b.enabled is False
        assert reloaded_c is not None
        assert reloaded_c.enabled is True

        enabled_services = await repository.list_enabled_services()
        assert [service.item_id for service in enabled_services] == ["svc-c"]
    finally:
        await _dispose(session_factory)


async def test_samples_states_snapshot_and_cutoff_cleanup(tmp_path: Path) -> None:
    session_factory = await _session_factory(tmp_path)
    repository = HealthRepository(session_factory)
    service_down = uuid4()
    service_weird = uuid4()
    service_disabled = uuid4()
    now = datetime.now(UTC)
    try:
        await repository.sync_services(
            [
                _spec(service_down, item_id="svc-down", name="Service Down", enabled=True),
                _spec(service_weird, item_id="svc-weird", name="Service Weird", enabled=True),
                _spec(service_disabled, item_id="svc-disabled", name="Service Disabled", enabled=False),
            ]
        )

        old_sample = HealthCheckResultV1(
            service_id=service_down,
            item_id="svc-down",
            check_type="http",
            target="https://down.local",
            success=False,
            latency_ms=None,
            error_message="old",
            checked_at=datetime(2026, 1, 1, 10, 0, 0),
        )
        new_sample = old_sample.model_copy(
            update={
                "checked_at": now,
                "latency_ms": 91,
                "error_message": None,
            }
        )
        await repository.insert_sample(old_sample)
        await repository.insert_sample(new_sample)

        latest_only = await repository.list_latest_samples(service_down, limit=0)
        assert len(latest_only) == 1
        assert latest_only[0].latency_ms == 91

        removed = await repository.delete_samples_older_than(now - timedelta(days=7))
        assert removed >= 1

        upserted = await repository.upsert_state(
            service_id=service_down,
            status="down",
            last_change_ts=datetime(2026, 1, 1, 11, 0, 0),
            avg_latency=12.6,
            success_rate=0.0,
            consecutive_failures=3,
        )
        assert upserted.current_status == "down"
        assert upserted.last_change_ts.tzinfo is not None

        async with session_factory() as session, session.begin():
            session.add(
                ServiceHealthStateRow(
                    service_id=str(service_weird),
                    current_status="BROKEN",
                    last_change_ts=now,
                    avg_latency=None,
                    success_rate=0.5,
                    consecutive_failures=0,
                    updated_at=now,
                )
            )

        snapshot = await repository.list_snapshot_items()
        assert sorted(item["item_id"] for item in snapshot) == ["svc-down", "svc-weird"]
        by_item = {str(item["item_id"]): item for item in snapshot}
        assert by_item["svc-down"]["status"] == "down"
        assert by_item["svc-down"]["ok"] is False
        assert by_item["svc-down"]["latency_ms"] == 13
        assert by_item["svc-down"]["error"] == "check failed"
        assert by_item["svc-weird"]["status"] == "unknown"
        assert by_item["svc-weird"]["ok"] is False
        assert by_item["svc-weird"]["error"] is None

        assert await repository.get_state(uuid4()) is None
    finally:
        await _dispose(session_factory)


async def test_upsert_state_raises_when_reload_returns_none(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_factory = await _session_factory(tmp_path)
    repository = HealthRepository(session_factory)
    service_id = uuid4()
    try:
        await repository.sync_services([_spec(service_id, item_id="svc-one", name="Service One")])

        async def _missing(_service_id: UUID) -> None:
            return None

        monkeypatch.setattr(repository, "get_state", _missing)
        with pytest.raises(RuntimeError, match="Failed to upsert health state"):
            await repository.upsert_state(
                service_id=service_id,
                status="online",
                last_change_ts=datetime.now(UTC),
                avg_latency=1.0,
                success_rate=1.0,
                consecutive_failures=0,
            )
    finally:
        await _dispose(session_factory)


async def test_as_utc_normalizes_naive_and_aware_datetimes() -> None:
    naive = datetime(2026, 1, 1, 10, 0, 0)
    aware = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)
    assert _as_utc(naive).tzinfo is UTC
    assert _as_utc(aware).tzinfo is UTC
