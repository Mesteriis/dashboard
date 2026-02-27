from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from core.contracts.storage import (
    PluginStorageConfig,
    StorageDDLColumnSpec,
    StorageDDLIndexSpec,
    StorageDDLSpec,
    StorageDDLTableSpec,
    StorageLimits,
    StorageRpcRequest,
    StorageTableSpec,
)
from core.storage import (
    STORAGE_RPC_QUEUE,
    BusStorageRPC,
    PhysicalStorage,
    StorageDdlNotAllowed,
    StorageModeRouter,
    StorageQueryNotAllowed,
    StorageRpcBus,
    StorageRpcConsumer,
    StorageRpcTimeout,
    UniversalStorage,
    physical_index_name,
    physical_table_name,
)
from core.storage.models import PluginIndexRow, PluginKvRow, PluginRow
from db.base import Base
from db.session import build_async_engine
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

ALL_OPS = {
    "kv.get",
    "kv.set",
    "kv.delete",
    "table.get",
    "table.upsert",
    "table.delete",
    "table.query",
}


async def _session_factory(tmp_path: Path) -> async_sessionmaker[AsyncSession]:
    _ = (PluginKvRow, PluginRow, PluginIndexRow)
    db_path = (tmp_path / "storage-mode-b.sqlite3").resolve()
    engine = build_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return async_sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


async def _dispose(session_factory: async_sessionmaker[AsyncSession]) -> None:
    bind = session_factory.kw.get("bind")
    if isinstance(bind, AsyncEngine):
        await bind.dispose()


async def _table_names(session_factory: async_sessionmaker[AsyncSession]) -> set[str]:
    bind = session_factory.kw["bind"]
    async with bind.begin() as connection:
        return set(await connection.run_sync(lambda sync_connection: set(inspect(sync_connection).get_table_names())))


async def _column_names(session_factory: async_sessionmaker[AsyncSession], table_name: str) -> set[str]:
    bind = session_factory.kw["bind"]
    async with bind.begin() as connection:
        return set(
            await connection.run_sync(
                lambda sync_connection: {column["name"] for column in inspect(sync_connection).get_columns(table_name)}
            )
        )


async def _index_names(session_factory: async_sessionmaker[AsyncSession], table_name: str) -> set[str]:
    bind = session_factory.kw["bind"]
    async with bind.begin() as connection:
        return set(
            await connection.run_sync(
                lambda sync_connection: {index["name"] for index in inspect(sync_connection).get_indexes(table_name)}
            )
        )


def _ddl_v1() -> StorageDDLSpec:
    return StorageDDLSpec(
        version=1,
        tables=[
            StorageDDLTableSpec(
                name="scan_runs",
                primary_key="scan_id",
                columns=[
                    StorageDDLColumnSpec(name="scan_id", type="string", nullable=False),
                    StorageDDLColumnSpec(name="status", type="string", nullable=False),
                    StorageDDLColumnSpec(name="requested_at", type="datetime", nullable=False),
                    StorageDDLColumnSpec(name="updated_at", type="datetime", nullable=False),
                ],
                indexes=[
                    StorageDDLIndexSpec(name="ix_scan_runs_status", columns=["status"]),
                ],
            )
        ],
    )


def _ddl_v2() -> StorageDDLSpec:
    return StorageDDLSpec(
        version=2,
        tables=[
            StorageDDLTableSpec(
                name="scan_runs",
                primary_key="scan_id",
                columns=[
                    StorageDDLColumnSpec(name="scan_id", type="string", nullable=False),
                    StorageDDLColumnSpec(name="status", type="string", nullable=False),
                    StorageDDLColumnSpec(name="dry_run", type="boolean", nullable=True),
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


def _ddl_v3_destructive() -> StorageDDLSpec:
    return StorageDDLSpec(
        version=3,
        tables=[
            StorageDDLTableSpec(
                name="scan_runs",
                primary_key="scan_id",
                columns=[
                    StorageDDLColumnSpec(name="scan_id", type="string", nullable=False),
                    StorageDDLColumnSpec(name="dry_run", type="boolean", nullable=True),
                    StorageDDLColumnSpec(name="requested_at", type="datetime", nullable=False),
                    StorageDDLColumnSpec(name="updated_at", type="datetime", nullable=False),
                ],
                indexes=[
                    StorageDDLIndexSpec(name="ix_scan_runs_dry_run", columns=["dry_run"]),
                ],
            )
        ],
    )


def _config(
    *,
    ddl: StorageDDLSpec,
    max_query_limit: int = 100,
    indexes: list[str] | None = None,
) -> PluginStorageConfig:
    resolved_indexes = indexes
    if resolved_indexes is None:
        resolved_indexes = sorted({column_name for index in ddl.tables[0].indexes for column_name in index.columns})

    return PluginStorageConfig(
        mode="core_physical_tables",
        ddl=ddl,
        limits=StorageLimits(max_qps=1000.0, max_query_limit=max_query_limit, max_row_bytes=262_144),
        tables=[
            StorageTableSpec(
                name="scan_runs",
                primary_key="scan_id",
                indexes=resolved_indexes,
            )
        ],
    )


def _scan_row(
    scan_id: str,
    *,
    status: str,
    dry_run: bool | None = None,
    include_summary: bool = True,
) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    row: dict[str, object] = {
        "scan_id": scan_id,
        "status": status,
        "requested_at": now,
        "updated_at": now,
    }
    if dry_run is not None:
        row["dry_run"] = dry_run
    if include_summary:
        row["summary"] = {"scan_id": scan_id, "status": status}
    return row


@pytest.mark.asyncio
async def test_install_creates_prefixed_tables(tmp_path: Path) -> None:
    session_factory = await _session_factory(tmp_path)
    storage = PhysicalStorage(
        session_factory=session_factory,
        plugin_configs={"autodiscover": _config(ddl=_ddl_v2())},
    )
    try:
        await storage.install_all()

        table_name = physical_table_name("autodiscover", "scan_runs")
        assert table_name in await _table_names(session_factory)

        column_names = await _column_names(session_factory, table_name)
        assert {"scan_id", "status", "dry_run", "requested_at", "updated_at", "summary"}.issubset(column_names)

        index_names = await _index_names(session_factory, table_name)
        assert physical_index_name(physical_table=table_name, logical_index_name="ix_scan_runs_status") in index_names
        assert physical_index_name(physical_table=table_name, logical_index_name="ix_scan_runs_dry_run") in index_names
    finally:
        await _dispose(session_factory)


@pytest.mark.asyncio
async def test_upgrade_adds_column_and_index(tmp_path: Path) -> None:
    session_factory = await _session_factory(tmp_path)
    table_name = physical_table_name("autodiscover", "scan_runs")

    storage_v1 = PhysicalStorage(
        session_factory=session_factory,
        plugin_configs={"autodiscover": _config(ddl=_ddl_v1())},
    )
    await storage_v1.install_all()
    await storage_v1.table_upsert(
        plugin_id="autodiscover",
        table="scan_runs",
        row=_scan_row("scan-1", status="completed", include_summary=False),
    )

    storage_v2 = PhysicalStorage(
        session_factory=session_factory,
        plugin_configs={"autodiscover": _config(ddl=_ddl_v2())},
    )
    try:
        await storage_v2.install_all()

        column_names = await _column_names(session_factory, table_name)
        index_names = await _index_names(session_factory, table_name)

        assert "dry_run" in column_names
        assert physical_index_name(physical_table=table_name, logical_index_name="ix_scan_runs_dry_run") in index_names

        old_row = await storage_v2.table_get(plugin_id="autodiscover", table="scan_runs", pk="scan-1")
        assert old_row is not None
        assert old_row["dry_run"] is None
    finally:
        await _dispose(session_factory)


@pytest.mark.asyncio
async def test_upgrade_rejects_destructive_changes(tmp_path: Path) -> None:
    session_factory = await _session_factory(tmp_path)

    storage_v2 = PhysicalStorage(
        session_factory=session_factory,
        plugin_configs={"autodiscover": _config(ddl=_ddl_v2())},
    )
    await storage_v2.install_all()

    try:
        storage_v3 = PhysicalStorage(
            session_factory=session_factory,
            plugin_configs={"autodiscover": _config(ddl=_ddl_v3_destructive())},
        )
        with pytest.raises(StorageDdlNotAllowed):
            await storage_v3.install_all()
    finally:
        await _dispose(session_factory)


@pytest.mark.asyncio
async def test_query_restrictions_and_limit_clamp(tmp_path: Path) -> None:
    session_factory = await _session_factory(tmp_path)
    storage = PhysicalStorage(
        session_factory=session_factory,
        plugin_configs={"autodiscover": _config(ddl=_ddl_v2(), max_query_limit=1)},
    )

    try:
        await storage.install_all()
        await storage.table_upsert(
            plugin_id="autodiscover",
            table="scan_runs",
            row=_scan_row("scan-a", status="completed", dry_run=False),
        )
        await storage.table_upsert(
            plugin_id="autodiscover",
            table="scan_runs",
            row=_scan_row("scan-b", status="completed", dry_run=True),
        )

        rows = await storage.table_query(
            plugin_id="autodiscover",
            table="scan_runs",
            where={"status": "completed"},
            limit=99,
        )
        assert len(rows) == 1

        with pytest.raises(StorageQueryNotAllowed):
            await storage.table_query(plugin_id="autodiscover", table="scan_runs", where={})

        with pytest.raises(StorageQueryNotAllowed):
            await storage.table_query(
                plugin_id="autodiscover",
                table="scan_runs",
                where={"summary": "x"},
            )
    finally:
        await _dispose(session_factory)


@pytest.mark.asyncio
async def test_storage_rpc_bus_mode_b_happy_and_timeout(tmp_path: Path) -> None:
    session_factory = await _session_factory(tmp_path)
    plugin_config = _config(ddl=_ddl_v2())

    universal_storage = UniversalStorage(session_factory=session_factory, plugin_configs={})
    physical_storage = PhysicalStorage(
        session_factory=session_factory,
        plugin_configs={"autodiscover": plugin_config},
    )
    routed_storage = StorageModeRouter(
        plugin_configs={"autodiscover": plugin_config},
        universal_storage=universal_storage,
        physical_storage=physical_storage,
    )

    bus = StorageRpcBus()
    consumer = StorageRpcConsumer(
        bus=bus,
        storage=routed_storage,
        queue_name=STORAGE_RPC_QUEUE,
        capabilities={"autodiscover": set(ALL_OPS)},
    )

    try:
        await consumer.start()
        try:
            rpc = BusStorageRPC(bus=bus, queue_name=STORAGE_RPC_QUEUE, timeout_sec=0.5)
            response = await rpc.call(
                StorageRpcRequest(
                    plugin_id="autodiscover",
                    op="table.upsert",
                    table="scan_runs",
                    row=_scan_row("scan-rpc", status="completed", dry_run=True),
                )
            )
            assert response.ok is True

            rows = await rpc.table_query(
                plugin_id="autodiscover",
                table="scan_runs",
                where={"status": "completed"},
            )
            assert len(rows) == 1
            assert rows[0]["scan_id"] == "scan-rpc"
        finally:
            await consumer.stop()

        timeout_rpc = BusStorageRPC(bus=bus, queue_name=STORAGE_RPC_QUEUE, timeout_sec=0.05)
        with pytest.raises(StorageRpcTimeout):
            await timeout_rpc.table_query(
                plugin_id="autodiscover",
                table="scan_runs",
                where={"status": "completed"},
            )
    finally:
        await _dispose(session_factory)
