from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from core.contracts.models import ActionEnvelope
from core.contracts.storage import (
    PluginStorageConfig,
    StorageDDLColumnSpec,
    StorageDDLIndexSpec,
    StorageDDLSpec,
    StorageDDLTableSpec,
    StorageLimits,
    StorageTableSpec,
)
from core.events import EventBus
from core.gateway import ActionGateway
from core.plugins.migrations import (
    ACTION_STORAGE_MIGRATE,
    CAPABILITY_STORAGE_MIGRATE,
    StorageMigrationLockManager,
    register_storage_migration_action,
)
from core.storage import PhysicalStorage, StorageModeRouter, StorageQueryNotAllowed, UniversalStorage
from core.storage.models import (
    ActionRow,
    AppStateRow,
    AuditLogRow,
    ConfigRevisionRow,
    PluginIndexRow,
    PluginKvRow,
    PluginRow,
)
from core.storage.repositories import ActionRepository, AuditRepository
from db.base import Base
from db.session import build_async_engine
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


async def _session_factory(tmp_path: Path) -> async_sessionmaker[AsyncSession]:
    _ = (ActionRow, AppStateRow, AuditLogRow, ConfigRevisionRow, PluginKvRow, PluginRow, PluginIndexRow)
    db_path = (tmp_path / "storage-migration.sqlite3").resolve()
    engine = build_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return async_sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


async def _dispose(session_factory: async_sessionmaker[AsyncSession]) -> None:
    bind = session_factory.kw.get("bind")
    if isinstance(bind, AsyncEngine):
        await bind.dispose()


def _ddl() -> StorageDDLSpec:
    return StorageDDLSpec(
        version=1,
        tables=[
            StorageDDLTableSpec(
                name="scan_runs",
                primary_key="scan_id",
                columns=[
                    StorageDDLColumnSpec(name="scan_id", type="string", nullable=False),
                    StorageDDLColumnSpec(name="status", type="string", nullable=False),
                    StorageDDLColumnSpec(name="dry_run", type="boolean", nullable=False),
                    StorageDDLColumnSpec(name="requested_at", type="datetime", nullable=False),
                    StorageDDLColumnSpec(name="updated_at", type="datetime", nullable=False),
                    StorageDDLColumnSpec(name="summary", type="json", nullable=True),
                ],
                indexes=[
                    StorageDDLIndexSpec(name="ix_scan_runs_status", columns=["status"]),
                    StorageDDLIndexSpec(name="ix_scan_runs_dry_run", columns=["dry_run"]),
                ],
            )
        ],
    )


def _plugin_config() -> PluginStorageConfig:
    return PluginStorageConfig(
        mode="core_physical_tables",
        ddl=_ddl(),
        limits=StorageLimits(
            max_tables=4,
            max_rows_per_table=10_000,
            max_row_bytes=262_144,
            max_kv_bytes=16_384,
            max_qps=1000.0,
            max_query_limit=500,
        ),
        tables=[StorageTableSpec(name="scan_runs", primary_key="scan_id", indexes=["status", "dry_run"])],
    )


def _scan_row(scan_id: str, *, status: str, dry_run: bool) -> dict[str, object]:
    ts = datetime.now(UTC).isoformat()
    return {
        "scan_id": scan_id,
        "status": status,
        "dry_run": dry_run,
        "requested_at": ts,
        "updated_at": ts,
        "summary": {"scan_id": scan_id, "status": status},
    }


async def _build_runtime(tmp_path: Path):
    session_factory = await _session_factory(tmp_path)
    config = _plugin_config()

    universal_storage = UniversalStorage(session_factory=session_factory, plugin_configs={"autodiscover": config})
    physical_storage = PhysicalStorage(session_factory=session_factory, plugin_configs={"autodiscover": config})
    await physical_storage.install_all()

    lock_manager = StorageMigrationLockManager()
    storage_router = StorageModeRouter(
        plugin_configs={"autodiscover": config},
        universal_storage=universal_storage,
        physical_storage=physical_storage,
        lock_manager=lock_manager,
    )

    actions_repo = ActionRepository(session_factory)
    audit_repo = AuditRepository(session_factory)
    event_bus = EventBus()
    gateway = ActionGateway(actions=actions_repo, audit=audit_repo, events=event_bus, execute_enabled=True)
    register_storage_migration_action(
        gateway,
        event_bus=event_bus,
        storage_router=storage_router,
        universal_storage=universal_storage,
        physical_storage=physical_storage,
        lock_manager=lock_manager,
    )
    return session_factory, storage_router, universal_storage, physical_storage, lock_manager, gateway


async def _execute_migration_action(
    gateway: ActionGateway,
    *,
    payload: dict[str, object],
    dry_run: bool = False,
):
    action = ActionEnvelope(
        type=ACTION_STORAGE_MIGRATE,
        requested_by="tester",
        capability=CAPABILITY_STORAGE_MIGRATE,
        payload=payload,
        dry_run=dry_run,
    )
    response = await gateway.execute_action(action=action, actor="tester")
    return action, response


@pytest.mark.asyncio
async def test_migrate_a_to_b_via_action_gateway_and_audit(tmp_path: Path) -> None:
    (
        session_factory,
        storage_router,
        _universal_storage,
        physical_storage,
        _lock_manager,
        gateway,
    ) = await _build_runtime(tmp_path)

    try:
        storage_router.set_table_mode(plugin_id="autodiscover", table="scan_runs", mode="core_universal")
        await storage_router.table_upsert(
            plugin_id="autodiscover",
            table="scan_runs",
            row=_scan_row("scan-a1", status="completed", dry_run=False),
        )
        await storage_router.table_upsert(
            plugin_id="autodiscover",
            table="scan_runs",
            row=_scan_row("scan-a2", status="completed", dry_run=True),
        )

        action, response = await _execute_migration_action(
            gateway,
            payload={
                "plugin_id": "autodiscover",
                "from_mode": "core_universal",
                "to_mode": "core_physical_tables",
                "tables": ["scan_runs"],
                "dry_run": False,
                "strategy": "read_only_lock",
            },
        )

        assert response.status == "succeeded"
        assert await physical_storage.count_table_rows(plugin_id="autodiscover", table="scan_runs") == 2
        migrated_row = await physical_storage.table_get(plugin_id="autodiscover", table="scan_runs", pk="scan-a1")
        assert migrated_row is not None
        assert migrated_row["status"] == "completed"
        assert storage_router.get_table_mode(plugin_id="autodiscover", table="scan_runs") == "core_physical_tables"

        async with session_factory() as session:
            audit_rows = (await session.execute(
                select(AuditLogRow).where(AuditLogRow.action_id == str(action.id))
            )).scalars().all()
        assert len(audit_rows) >= 2
    finally:
        await _dispose(session_factory)


@pytest.mark.asyncio
async def test_lock_blocks_table_upsert_during_migration(tmp_path: Path) -> None:
    (
        session_factory,
        storage_router,
        _universal_storage,
        _physical_storage,
        lock_manager,
        _gateway,
    ) = await _build_runtime(tmp_path)

    try:
        with (
            lock_manager.read_only_lock(plugin_id="autodiscover", tables=["scan_runs"]),
            pytest.raises(StorageQueryNotAllowed),
        ):
            await storage_router.table_upsert(
                plugin_id="autodiscover",
                table="scan_runs",
                row=_scan_row("scan-lock", status="blocked", dry_run=False),
            )
    finally:
        await _dispose(session_factory)


@pytest.mark.asyncio
async def test_dry_run_returns_plan_without_writes(tmp_path: Path) -> None:
    (
        session_factory,
        storage_router,
        _universal_storage,
        physical_storage,
        _lock_manager,
        gateway,
    ) = await _build_runtime(tmp_path)

    try:
        storage_router.set_table_mode(plugin_id="autodiscover", table="scan_runs", mode="core_universal")
        await storage_router.table_upsert(
            plugin_id="autodiscover",
            table="scan_runs",
            row=_scan_row("scan-dr1", status="completed", dry_run=False),
        )
        await storage_router.table_upsert(
            plugin_id="autodiscover",
            table="scan_runs",
            row=_scan_row("scan-dr2", status="completed", dry_run=False),
        )

        _action, response = await _execute_migration_action(
            gateway,
            payload={
                "plugin_id": "autodiscover",
                "from_mode": "core_universal",
                "to_mode": "core_physical_tables",
                "tables": ["scan_runs"],
                "dry_run": True,
                "strategy": "read_only_lock",
            },
            dry_run=True,
        )

        assert response.status == "succeeded"
        assert response.result is not None
        assert response.result["status"] == "planned"
        assert response.result["plan"][0]["rows"] == 2
        assert await physical_storage.count_table_rows(plugin_id="autodiscover", table="scan_runs") == 0
        assert storage_router.get_table_mode(plugin_id="autodiscover", table="scan_runs") == "core_universal"
    finally:
        await _dispose(session_factory)


@pytest.mark.asyncio
async def test_migrate_b_to_a_rebuilds_indexes(tmp_path: Path) -> None:
    (
        session_factory,
        storage_router,
        universal_storage,
        _physical_storage,
        _lock_manager,
        gateway,
    ) = await _build_runtime(tmp_path)

    try:
        await storage_router.table_upsert(
            plugin_id="autodiscover",
            table="scan_runs",
            row=_scan_row("scan-b1", status="completed", dry_run=False),
        )
        await storage_router.table_upsert(
            plugin_id="autodiscover",
            table="scan_runs",
            row=_scan_row("scan-b2", status="completed", dry_run=True),
        )

        _action, response = await _execute_migration_action(
            gateway,
            payload={
                "plugin_id": "autodiscover",
                "from_mode": "core_physical_tables",
                "to_mode": "core_universal",
                "tables": ["scan_runs"],
                "dry_run": False,
                "strategy": "read_only_lock",
            },
        )

        assert response.status == "succeeded"
        assert await universal_storage.count_table_rows(plugin_id="autodiscover", table="scan_runs") == 2
        indexed_rows = await universal_storage.table_query(
            plugin_id="autodiscover",
            table="scan_runs",
            where={"status": "completed"},
            limit=10,
        )
        assert len(indexed_rows) == 2
        assert storage_router.get_table_mode(plugin_id="autodiscover", table="scan_runs") == "core_universal"
    finally:
        await _dispose(session_factory)
