from __future__ import annotations

from pathlib import Path

import pytest
from core.bus import BrokerStorageRPC, BusClient, StorageBusConsumer
from core.contracts.storage import PluginStorageConfig, StorageLimits, StorageTableSpec
from core.storage import StorageQueryNotAllowed, StorageRpcTimeout, UniversalStorage
from core.storage.models import PluginIndexRow, PluginKvRow, PluginRow
from db.base import Base
from db.session import build_async_engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

ALL_STORAGE_OPS = {
    "storage.kv.get",
    "storage.kv.set",
    "storage.kv.delete",
    "storage.table.get",
    "storage.table.upsert",
    "storage.table.delete",
    "storage.table.query",
}


async def _session_factory(tmp_path: Path) -> async_sessionmaker[AsyncSession]:
    _ = (PluginKvRow, PluginRow, PluginIndexRow)
    db_path = (tmp_path / "broker-storage.sqlite3").resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = build_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return async_sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


async def _dispose(session_factory: async_sessionmaker[AsyncSession]) -> None:
    bind = session_factory.kw.get("bind")
    if isinstance(bind, AsyncEngine):
        await bind.dispose()


def _plugin_config() -> PluginStorageConfig:
    return PluginStorageConfig(
        mode="core_universal",
        limits=StorageLimits(max_qps=1_000.0, max_query_limit=50),
        tables=[StorageTableSpec(name="devices", primary_key="id", indexes=["ip", "kind"])],
    )


@pytest.mark.asyncio
async def test_broker_storage_query_policy_and_index_rebuild(tmp_path: Path) -> None:
    session_factory = await _session_factory(tmp_path)
    bus_client = BusClient(broker_url="memory://broker")
    storage = UniversalStorage(session_factory=session_factory, plugin_configs={"autodiscover": _plugin_config()})
    consumer = StorageBusConsumer(
        bus_client=bus_client,
        storage=storage,
        plugin_configs={"autodiscover": _plugin_config()},
        capabilities={"autodiscover": set(ALL_STORAGE_OPS)},
    )
    rpc = BrokerStorageRPC(bus_client=bus_client, timeout_sec=0.2)

    try:
        await bus_client.connect()
        await consumer.start()

        with pytest.raises(StorageQueryNotAllowed):
            await rpc.table_query(
                plugin_id="autodiscover",
                table="devices",
                where={},
                limit=10,
            )

        with pytest.raises(StorageQueryNotAllowed):
            await rpc.table_query(
                plugin_id="autodiscover",
                table="devices",
                where={"hostname": "edge"},
                limit=10,
            )

        await rpc.table_upsert(
            plugin_id="autodiscover",
            table="devices",
            row={"id": "n1", "ip": "10.0.0.2", "kind": "router"},
        )
        await rpc.table_upsert(
            plugin_id="autodiscover",
            table="devices",
            row={"id": "n1", "ip": "10.0.0.9", "kind": "router"},
        )

        old_rows = await rpc.table_query(
            plugin_id="autodiscover",
            table="devices",
            where={"ip": "10.0.0.2"},
            limit=10,
        )
        new_rows = await rpc.table_query(
            plugin_id="autodiscover",
            table="devices",
            where={"ip": "10.0.0.9"},
            limit=10,
        )
        assert old_rows == []
        assert new_rows == [{"id": "n1", "ip": "10.0.0.9", "kind": "router"}]
    finally:
        await consumer.stop()
        await bus_client.close()
        await _dispose(session_factory)


@pytest.mark.asyncio
async def test_broker_storage_capability_default_deny(tmp_path: Path) -> None:
    session_factory = await _session_factory(tmp_path)
    bus_client = BusClient(broker_url="memory://broker")
    storage = UniversalStorage(session_factory=session_factory, plugin_configs={"autodiscover": _plugin_config()})
    consumer = StorageBusConsumer(
        bus_client=bus_client,
        storage=storage,
        plugin_configs={"autodiscover": _plugin_config()},
        capabilities={"autodiscover": {"storage.kv.get"}},
    )
    rpc = BrokerStorageRPC(bus_client=bus_client, timeout_sec=0.2)

    try:
        await bus_client.connect()
        await consumer.start()

        with pytest.raises(StorageQueryNotAllowed):
            await rpc.kv_set(plugin_id="autodiscover", key="blocked", value={"x": 1})
    finally:
        await consumer.stop()
        await bus_client.close()
        await _dispose(session_factory)


@pytest.mark.asyncio
async def test_broker_storage_rpc_timeout_without_consumer() -> None:
    bus_client = BusClient(broker_url="memory://broker")
    rpc = BrokerStorageRPC(bus_client=bus_client, timeout_sec=0.05)

    await bus_client.connect()
    try:
        with pytest.raises(StorageRpcTimeout):
            await rpc.kv_get(plugin_id="autodiscover", key="missing")
    finally:
        await bus_client.close()
