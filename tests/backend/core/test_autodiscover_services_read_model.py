from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy

import plugins.autodiscover as autodiscover_module
import pytest
from core.contracts.models import ActionEnvelope
from plugins.autodiscover import get_services
from plugins.autodiscover import setup as autodiscover_setup
from plugins.autodiscover import teardown as autodiscover_teardown
from plugins.autodiscover.registry import _persist_scan_snapshot


class _FakeStorageRpc:
    def __init__(
        self,
        *,
        kv: dict[str, object] | None = None,
        scan_runs: list[dict[str, object]] | None = None,
        scan_services: list[dict[str, object]] | None = None,
    ) -> None:
        self.kv: dict[str, object] = dict(kv or {})
        self.scan_runs = [dict(row) for row in (scan_runs or [])]
        self.scan_services = [dict(row) for row in (scan_services or [])]

    async def kv_get(self, *, plugin_id: str, key: str, secret: bool = False) -> object | None:
        _ = (plugin_id, secret)
        return self.kv.get(key)

    async def kv_set(self, *, plugin_id: str, key: str, value: object, secret: bool = False) -> None:
        _ = (plugin_id, secret)
        self.kv[key] = value

    async def kv_delete(self, *, plugin_id: str, key: str) -> bool:
        _ = plugin_id
        return self.kv.pop(key, None) is not None

    async def table_query(
        self,
        *,
        plugin_id: str,
        table: str,
        where: Mapping[str, object],
        limit: int | None = None,
    ) -> list[dict[str, object]]:
        _ = plugin_id
        source = self.scan_runs if table == "scan_runs" else self.scan_services
        rows = []
        for row in source:
            if all(row.get(field) == value for field, value in where.items()):
                rows.append(dict(row))
        if limit is None:
            return rows
        return rows[: max(1, int(limit))]

    async def table_get(self, *, plugin_id: str, table: str, pk: object) -> dict[str, object] | None:
        _ = plugin_id
        source = self.scan_runs if table == "scan_runs" else self.scan_services
        pk_field = "scan_id" if table == "scan_runs" else "service_key"
        for row in source:
            if row.get(pk_field) == pk:
                return dict(row)
        return None

    async def table_upsert(
        self,
        *,
        plugin_id: str,
        table: str,
        row: Mapping[str, object],
    ) -> dict[str, object]:
        _ = plugin_id
        target = self.scan_runs if table == "scan_runs" else self.scan_services
        pk_field = "scan_id" if table == "scan_runs" else "service_key"
        pk_value = row.get(pk_field)

        for index, existing in enumerate(target):
            if existing.get(pk_field) == pk_value:
                target[index] = dict(row)
                return dict(row)

        target.append(dict(row))
        return dict(row)


class _TimeoutStorageRpc:
    async def kv_get(self, *, plugin_id: str, key: str, secret: bool = False) -> object | None:
        _ = (plugin_id, key, secret)
        raise RuntimeError("storage timeout")

    async def kv_set(self, *, plugin_id: str, key: str, value: object, secret: bool = False) -> None:
        _ = (plugin_id, key, value, secret)
        raise RuntimeError("storage timeout")

    async def kv_delete(self, *, plugin_id: str, key: str) -> bool:
        _ = (plugin_id, key)
        raise RuntimeError("storage timeout")

    async def table_query(
        self,
        *,
        plugin_id: str,
        table: str,
        where: Mapping[str, object],
        limit: int | None = None,
    ) -> list[dict[str, object]]:
        _ = (plugin_id, table, where, limit)
        raise RuntimeError("storage timeout")

    async def table_get(self, *, plugin_id: str, table: str, pk: object) -> dict[str, object] | None:
        _ = (plugin_id, table, pk)
        raise RuntimeError("storage timeout")


@pytest.mark.asyncio
async def test_get_services_self_heals_stale_last_scan_id(monkeypatch: pytest.MonkeyPatch) -> None:
    storage = _FakeStorageRpc(
        kv={"last_scan_id": "scan-failed"},
        scan_runs=[
            {
                "scan_id": "scan-failed",
                "status": "failed",
                "requested_at": "2026-03-01T12:10:00+00:00",
                "updated_at": "2026-03-01T12:10:01+00:00",
                "summary": {"error": "boom"},
            },
            {
                "scan_id": "scan-good",
                "status": "completed",
                "requested_at": "2026-03-01T12:00:00+00:00",
                "updated_at": "2026-03-01T12:00:10+00:00",
                "summary": {"generated_at": "2026-03-01T12:00:10+00:00"},
            },
        ],
        scan_services=[
            {
                "service_key": "scan-good:192.168.1.2:22:ssh:",
                "scan_id": "scan-good",
                "host_ip": "192.168.1.2",
                "hostname": "node",
                "port": 22,
                "service": "ssh",
                "title": None,
                "url": None,
                "status": None,
                "server": None,
                "updated_at": "2026-03-01T12:00:10+00:00",
            }
        ],
    )

    async def _noop_sync() -> None:
        return None

    monkeypatch.setattr(autodiscover_module, "_sync_result_to_storage", _noop_sync)

    autodiscover_teardown()
    autodiscover_setup(storage_rpc=storage)
    try:
        response = await get_services()
    finally:
        autodiscover_teardown()

    assert response["total"] == 1
    assert response["services"][0]["host_ip"] == "192.168.1.2"
    assert response["generated_at"] == "2026-03-01T12:00:10+00:00"
    assert storage.kv.get("last_scan_id") == "scan-good"


@pytest.mark.asyncio
async def test_get_services_returns_empty_on_storage_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(autodiscover_module, "_last_services_cache", None)
    autodiscover_teardown()
    autodiscover_setup(storage_rpc=_TimeoutStorageRpc())
    try:
        response = await get_services()
    finally:
        autodiscover_teardown()

    assert response["services"] == []
    assert response["total"] == 0
    assert isinstance(response["generated_at"], str)


@pytest.mark.asyncio
async def test_failed_scan_does_not_override_last_scan_id() -> None:
    storage = _FakeStorageRpc(kv={"last_scan_id": "scan-prev"})

    failed_action = ActionEnvelope(
        type="autodiscover.scan",
        requested_by="plugin.autodiscover.scheduler",
        capability="exec.plugin.autodiscover.scan",
        payload={},
        dry_run=False,
    )

    await _persist_scan_snapshot(
        action=failed_action,
        status="failed",
        summary={"error": "failure"},
        result_payload=None,
        storage_rpc=storage,
    )

    assert storage.kv.get("last_scan_id") == "scan-prev"

    completed_action = ActionEnvelope(
        type="autodiscover.scan",
        requested_by="plugin.autodiscover.scheduler",
        capability="exec.plugin.autodiscover.scan",
        payload={},
        dry_run=False,
    )
    result_payload = {
        "generated_at": "2026-03-01T13:00:00+00:00",
        "hosts": [
            {
                "ip": "192.168.1.20",
                "hostname": "srv",
                "open_ports": [{"port": 80, "service": "http"}],
                "http_services": [{"port": 80, "title": "Nginx", "url": "http://192.168.1.20/"}],
            }
        ],
    }

    await _persist_scan_snapshot(
        action=completed_action,
        status="completed",
        summary={"generated_at": "2026-03-01T13:00:00+00:00"},
        result_payload=deepcopy(result_payload),
        storage_rpc=storage,
    )

    assert storage.kv.get("last_scan_id") == str(completed_action.id)
    assert any(row.get("scan_id") == str(completed_action.id) for row in storage.scan_services)
