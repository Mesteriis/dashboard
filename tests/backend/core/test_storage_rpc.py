from __future__ import annotations

from pathlib import Path

import pytest
from core.contracts.storage import PluginStorageConfig, StorageLimits, StorageRpcRequest, StorageTableSpec
from core.storage import (
    STORAGE_RPC_QUEUE,
    BusStorageRPC,
    InProcStorageRPC,
    StorageRpcBus,
    StorageRpcConsumer,
    StorageRpcTimeout,
    UniversalStorage,
)
from core.storage.models import PluginIndexRow, PluginKvRow, PluginRow
from db.base import Base
from db.session import build_async_engine
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


async def _build_session_factory(tmp_path: Path) -> async_sessionmaker[AsyncSession]:
    _ = (PluginKvRow, PluginRow, PluginIndexRow)
    db_path = (tmp_path / "storage-rpc.sqlite3").resolve()
    engine = build_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return async_sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


async def _dispose(session_factory: async_sessionmaker[AsyncSession]) -> None:
    bind = session_factory.kw.get("bind")
    if isinstance(bind, AsyncEngine):
        await bind.dispose()


def _storage_config() -> PluginStorageConfig:
    return PluginStorageConfig(
        mode="core_universal",
        limits=StorageLimits(max_qps=1_000.0),
        tables=[
            StorageTableSpec(name="scan_runs", primary_key="scan_id", indexes=["status"]),
        ],
    )


@pytest.mark.asyncio
async def test_inproc_storage_rpc_happy_path(tmp_path: Path) -> None:
    session_factory = await _build_session_factory(tmp_path)
    storage = UniversalStorage(
        session_factory=session_factory,
        plugin_configs={"autodiscover": _storage_config()},
    )
    rpc = InProcStorageRPC(storage=storage)
    try:
        await rpc.table_upsert(
            plugin_id="autodiscover",
            table="scan_runs",
            row={"scan_id": "scan-1", "status": "completed"},
        )

        rows = await rpc.table_query(
            plugin_id="autodiscover",
            table="scan_runs",
            where={"status": "completed"},
        )

        assert rows == [{"scan_id": "scan-1", "status": "completed"}]
    finally:
        await _dispose(session_factory)


@pytest.mark.asyncio
async def test_bus_storage_rpc_request_response_and_timeout(tmp_path: Path) -> None:
    session_factory = await _build_session_factory(tmp_path)
    storage = UniversalStorage(
        session_factory=session_factory,
        plugin_configs={"autodiscover": _storage_config()},
    )
    bus = StorageRpcBus()
    consumer = StorageRpcConsumer(
        bus=bus,
        storage=storage,
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
                    row={"scan_id": "scan-2", "status": "completed"},
                )
            )
            assert response.ok is True

            rows = await rpc.table_query(
                plugin_id="autodiscover",
                table="scan_runs",
                where={"status": "completed"},
            )
            assert rows == [{"scan_id": "scan-2", "status": "completed"}]
        finally:
            await consumer.stop()

        rpc_timeout = BusStorageRPC(bus=bus, queue_name=STORAGE_RPC_QUEUE, timeout_sec=0.05)
        with pytest.raises(StorageRpcTimeout):
            await rpc_timeout.kv_get(plugin_id="autodiscover", key="missing")
    finally:
        await _dispose(session_factory)
