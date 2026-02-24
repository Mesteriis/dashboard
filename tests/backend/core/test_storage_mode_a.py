from __future__ import annotations

from pathlib import Path

import pytest
from core.contracts.storage import PluginStorageConfig, StorageLimits, StorageTableSpec
from core.storage import StorageLimitExceeded, StorageQueryNotAllowed, StorageRateLimited, UniversalStorage
from core.storage.models import PluginIndexRow, PluginKvRow, PluginRow
from db.base import Base
from db.session import build_async_engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


async def _build_session_factory(tmp_path: Path) -> async_sessionmaker[AsyncSession]:
    _ = (PluginKvRow, PluginRow, PluginIndexRow)
    db_path = (tmp_path / "storage.sqlite3").resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = build_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return async_sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


async def _dispose(session_factory: async_sessionmaker[AsyncSession]) -> None:
    bind = session_factory.kw.get("bind")
    if isinstance(bind, AsyncEngine):
        await bind.dispose()


def _base_config(*, limits: StorageLimits | None = None) -> PluginStorageConfig:
    return PluginStorageConfig(
        mode="core_universal",
        limits=limits or StorageLimits(max_qps=1000.0),
        tables=[
            StorageTableSpec(
                name="devices",
                primary_key="id",
                indexes=["ip", "kind"],
            )
        ],
    )


@pytest.mark.asyncio
async def test_indexes_are_rebuilt_on_upsert(tmp_path: Path) -> None:
    session_factory = await _build_session_factory(tmp_path)
    storage = UniversalStorage(
        session_factory=session_factory,
        plugin_configs={"plugin.autodiscover": _base_config()},
    )
    try:
        await storage.table_upsert(
            plugin_id="plugin.autodiscover",
            table="devices",
            row={"id": "node-1", "ip": "10.0.0.2", "kind": "router"},
        )

        assert await storage.table_query(
            plugin_id="plugin.autodiscover",
            table="devices",
            where={"ip": "10.0.0.2"},
        ) == [{"id": "node-1", "ip": "10.0.0.2", "kind": "router"}]

        await storage.table_upsert(
            plugin_id="plugin.autodiscover",
            table="devices",
            row={"id": "node-1", "ip": "10.0.0.9", "kind": "router"},
        )

        assert await storage.table_query(
            plugin_id="plugin.autodiscover",
            table="devices",
            where={"ip": "10.0.0.2"},
        ) == []
        assert await storage.table_query(
            plugin_id="plugin.autodiscover",
            table="devices",
            where={"ip": "10.0.0.9"},
        ) == [{"id": "node-1", "ip": "10.0.0.9", "kind": "router"}]
    finally:
        await _dispose(session_factory)


@pytest.mark.asyncio
async def test_query_restrictions_and_limit_clamp(tmp_path: Path) -> None:
    session_factory = await _build_session_factory(tmp_path)
    storage = UniversalStorage(
        session_factory=session_factory,
        plugin_configs={
            "plugin.autodiscover": _base_config(
                limits=StorageLimits(
                    max_qps=1000.0,
                    max_query_limit=2,
                )
            )
        },
    )
    try:
        await storage.table_upsert(
            plugin_id="plugin.autodiscover",
            table="devices",
            row={"id": "1", "ip": "10.0.0.1", "kind": "router"},
        )
        await storage.table_upsert(
            plugin_id="plugin.autodiscover",
            table="devices",
            row={"id": "2", "ip": "10.0.0.2", "kind": "router"},
        )
        await storage.table_upsert(
            plugin_id="plugin.autodiscover",
            table="devices",
            row={"id": "3", "ip": "10.0.0.3", "kind": "router"},
        )

        with pytest.raises(StorageQueryNotAllowed):
            await storage.table_query(
                plugin_id="plugin.autodiscover",
                table="devices",
                where={},
            )

        with pytest.raises(StorageQueryNotAllowed):
            await storage.table_query(
                plugin_id="plugin.autodiscover",
                table="devices",
                where={"hostname": "edge"},
            )

        rows = await storage.table_query(
            plugin_id="plugin.autodiscover",
            table="devices",
            where={"kind": "router"},
            limit=999,
        )
        assert len(rows) == 2
    finally:
        await _dispose(session_factory)


@pytest.mark.asyncio
async def test_limits_for_row_bytes_rows_per_table_and_qps(tmp_path: Path) -> None:
    session_factory = await _build_session_factory(tmp_path)
    storage = UniversalStorage(
        session_factory=session_factory,
        plugin_configs={
            "plugin.autodiscover": _base_config(
                limits=StorageLimits(
                    max_tables=2,
                    max_rows_per_table=1,
                    max_row_bytes=80,
                    max_kv_bytes=64,
                    max_qps=1000.0,
                    max_query_limit=50,
                )
            )
        },
    )
    qps_session_factory = await _build_session_factory(tmp_path / "qps")
    qps_limited = UniversalStorage(
        session_factory=qps_session_factory,
        plugin_configs={
            "plugin.autodiscover": _base_config(
                limits=StorageLimits(
                    max_qps=1.0,
                    max_query_limit=50,
                )
            )
        },
    )
    try:
        with pytest.raises(StorageLimitExceeded):
            await storage.table_upsert(
                plugin_id="plugin.autodiscover",
                table="devices",
                row={
                    "id": "too-large",
                    "ip": "10.0.0.1",
                    "kind": "router",
                    "blob": "x" * 400,
                },
            )

        await storage.table_upsert(
            plugin_id="plugin.autodiscover",
            table="devices",
            row={"id": "first", "ip": "10.0.0.10", "kind": "switch"},
        )

        with pytest.raises(StorageLimitExceeded):
            await storage.table_upsert(
                plugin_id="plugin.autodiscover",
                table="devices",
                row={"id": "second", "ip": "10.0.0.11", "kind": "switch"},
            )

        await qps_limited.kv_set(plugin_id="plugin.autodiscover", key="a", value={"ok": True})
        with pytest.raises(StorageRateLimited):
            await qps_limited.kv_set(plugin_id="plugin.autodiscover", key="b", value={"ok": True})
    finally:
        await _dispose(session_factory)
        await _dispose(qps_session_factory)


@pytest.mark.asyncio
async def test_plugin_id_isolation(tmp_path: Path) -> None:
    session_factory = await _build_session_factory(tmp_path)
    storage = UniversalStorage(
        session_factory=session_factory,
        plugin_configs={
            "plugin.a": _base_config(),
            "plugin.b": _base_config(),
        },
    )
    try:
        await storage.table_upsert(
            plugin_id="plugin.a",
            table="devices",
            row={"id": "shared", "ip": "10.0.1.1", "kind": "router"},
        )
        await storage.table_upsert(
            plugin_id="plugin.b",
            table="devices",
            row={"id": "shared", "ip": "10.0.1.1", "kind": "sensor"},
        )

        rows_a = await storage.table_query(plugin_id="plugin.a", table="devices", where={"ip": "10.0.1.1"})
        rows_b = await storage.table_query(plugin_id="plugin.b", table="devices", where={"ip": "10.0.1.1"})

        assert rows_a == [{"id": "shared", "ip": "10.0.1.1", "kind": "router"}]
        assert rows_b == [{"id": "shared", "ip": "10.0.1.1", "kind": "sensor"}]
    finally:
        await _dispose(session_factory)
