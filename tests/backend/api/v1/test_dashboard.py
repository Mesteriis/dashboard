from __future__ import annotations

import asyncio
import json
from collections import deque
from collections.abc import AsyncIterator

import httpx
import pytest
from faker import Faker
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from support.factories import build_dashboard_config, dump_dashboard_yaml

import depens.v1.health_runtime as dashboard_module
from api.v1 import health as health_router_module
from api.v1 import v1_router as dashboard_router
from config.container import AppContainer
from db.models import HealthSample
from scheme.dashboard import DashboardConfig, ItemHealthStatus, LanScanStateResponse, LinkItemConfig, ValidationIssue
from service.config_service import DashboardConfigValidationError

pytestmark = pytest.mark.asyncio


def _config_with_items(base_config: DashboardConfig, items: list[LinkItemConfig]) -> DashboardConfig:
    config = base_config.model_copy(deep=True)
    config.groups[0].subgroups[0].items = items
    return config


@pytest.fixture(autouse=True)
def clear_health_history() -> None:
    dashboard_module.reset_health_runtime_state()


async def test_get_dashboard_config_returns_current_model(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/dashboard/config")

    assert response.status_code == httpx.codes.OK
    assert response.headers["cache-control"] == "private, max-age=0, must-revalidate"
    assert response.headers["etag"].startswith('"cfg-')
    payload = response.json()
    assert payload["app"]["id"] == "demo"
    assert payload["groups"][0]["id"] == "core"


async def test_get_dashboard_config_returns_304_for_matching_if_none_match(api_client: AsyncClient) -> None:
    first = await api_client.get("/api/v1/dashboard/config")
    assert first.status_code == httpx.codes.OK
    etag = first.headers["etag"]

    second = await api_client.get(
        "/api/v1/dashboard/config",
        headers={"if-none-match": etag},
    )

    assert second.status_code == httpx.codes.NOT_MODIFIED
    assert second.text == ""
    assert second.headers["etag"] == etag


async def test_get_container_returns_500_when_container_is_missing() -> None:
    app = FastAPI()
    app.include_router(dashboard_router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/v1/dashboard/config")
    assert response.status_code == httpx.codes.INTERNAL_SERVER_ERROR


async def test_get_dashboard_config_returns_422_when_service_validation_fails(
    api_client: AsyncClient,
    app_container: AppContainer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_load(*_: object, **__: object) -> object:
        raise DashboardConfigValidationError(
            [ValidationIssue(code="schema_error", path="$.app.title", message="invalid")]
        )

    monkeypatch.setattr(app_container.config_service, "load", fail_load)
    response = await api_client.get("/api/v1/dashboard/config")
    assert response.status_code == httpx.codes.UNPROCESSABLE_ENTITY


async def test_put_dashboard_config_is_open_without_admin_token(
    api_client: AsyncClient,
    fake: Faker,
) -> None:
    payload = build_dashboard_config(fake, title="Config Without Token").model_dump(mode="json", exclude_none=True)

    response = await api_client.put("/api/v1/dashboard/config", json=payload)

    assert response.status_code == httpx.codes.OK
    response_payload = response.json()
    assert response_payload["config"]["app"]["title"] == "Config Without Token"
    assert response_payload["version"]["sha256"]


async def test_download_dashboard_config_backup_returns_yaml_attachment(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/dashboard/config/backup")

    assert response.status_code == httpx.codes.OK
    assert response.headers["cache-control"] == "private, max-age=0, must-revalidate"
    assert "application/x-yaml" in response.headers["content-type"]
    assert response.headers["content-disposition"].startswith('attachment; filename="dashboard-backup-')
    assert response.headers["content-disposition"].endswith('.yaml"')
    assert "version: 1" in response.text


async def test_restore_dashboard_config_is_open_without_admin_token(
    api_client: AsyncClient,
    fake: Faker,
) -> None:
    payload = {"yaml": dump_dashboard_yaml(build_dashboard_config(fake, title="Restored From Backup"))}

    restore_response = await api_client.post("/api/v1/dashboard/config/restore", json=payload)

    assert restore_response.status_code == httpx.codes.OK
    restore_payload = restore_response.json()
    assert restore_payload["config"]["app"]["title"] == "Restored From Backup"
    assert restore_payload["version"]["sha256"]

    persisted_response = await api_client.get("/api/v1/dashboard/config")
    assert persisted_response.status_code == httpx.codes.OK
    assert persisted_response.json()["app"]["title"] == "Restored From Backup"


async def test_get_dashboard_health_filters_items_by_item_id(
    api_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_probe_item_health(**kwargs: object) -> ItemHealthStatus:
        item = kwargs["item"]
        return ItemHealthStatus(
            item_id=item.id,
            ok=True,
            checked_url=str(item.url),
            status_code=200,
            latency_ms=1,
            error=None,
        )

    monkeypatch.setattr(dashboard_module, "probe_item_health", fake_probe_item_health)
    response = await api_client.get("/api/v1/dashboard/health?item_id=svc-link")
    assert response.status_code == httpx.codes.OK
    assert response.headers["cache-control"] == "private, max-age=2, stale-while-revalidate=8"
    assert len(response.json()["items"]) == 1
    assert response.json()["items"][0]["item_id"] == "svc-link"


async def test_get_dashboard_health_returns_group_and_subgroup_aggregates(
    api_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_probe_item_health(**kwargs: object) -> ItemHealthStatus:
        item = kwargs["item"]
        if item.id == "svc-link":
            return ItemHealthStatus(
                item_id=item.id,
                ok=True,
                checked_url=str(item.url),
                status_code=200,
                latency_ms=10,
                error=None,
                level="online",
                reason="ok",
                error_kind=None,
            )
        if item.id == "svc-iframe-public":
            return ItemHealthStatus(
                item_id=item.id,
                ok=False,
                checked_url=str(item.url),
                status_code=404,
                latency_ms=28,
                error="HTTP 404",
                level="degraded",
                reason="http_4xx",
                error_kind="http_error",
            )
        return ItemHealthStatus(
            item_id=item.id,
            ok=False,
            checked_url=str(item.url),
            status_code=503,
            latency_ms=24,
            error="HTTP 503",
            level="down",
            reason="http_5xx",
            error_kind="http_error",
        )

    monkeypatch.setattr(dashboard_module, "probe_item_health", fake_probe_item_health)
    response = await api_client.get("/api/v1/dashboard/health")
    assert response.status_code == httpx.codes.OK

    payload = response.json()
    aggregates = payload["aggregates"]

    assert len(aggregates["groups"]) == 1
    assert aggregates["groups"][0]["group_id"] == "core"
    assert aggregates["groups"][0]["status"] == {
        "total": 3,
        "online": 1,
        "degraded": 1,
        "down": 1,
        "unknown": 0,
        "indirect_failure": 0,
        "level": "down",
    }

    assert len(aggregates["subgroups"]) == 1
    assert aggregates["subgroups"][0]["group_id"] == "core"
    assert aggregates["subgroups"][0]["subgroup_id"] == "core.main"
    assert aggregates["subgroups"][0]["status"]["level"] == "down"


async def test_get_dashboard_health_filtered_items_return_filtered_aggregates(
    api_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_probe_item_health(**kwargs: object) -> ItemHealthStatus:
        item = kwargs["item"]
        return ItemHealthStatus(
            item_id=item.id,
            ok=True,
            checked_url=str(item.url),
            status_code=200,
            latency_ms=8,
            error=None,
            level="online",
            reason="ok",
            error_kind=None,
        )

    monkeypatch.setattr(dashboard_module, "probe_item_health", fake_probe_item_health)
    response = await api_client.get("/api/v1/dashboard/health?item_id=svc-link")
    assert response.status_code == httpx.codes.OK
    payload = response.json()

    assert len(payload["items"]) == 1
    assert payload["items"][0]["item_id"] == "svc-link"
    assert payload["aggregates"]["groups"][0]["status"]["total"] == 1
    assert payload["aggregates"]["groups"][0]["status"]["level"] == "online"
    assert payload["aggregates"]["subgroups"][0]["status"]["total"] == 1


async def test_get_dashboard_health_uses_cached_snapshot_when_refresh_interval_is_positive(
    api_client: AsyncClient,
    app_container: AppContainer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app_container.settings.health_refresh_sec = 60
    probe_calls = 0

    async def fake_probe_item_health(**kwargs: object) -> ItemHealthStatus:
        nonlocal probe_calls
        probe_calls += 1
        item = kwargs["item"]
        return ItemHealthStatus(
            item_id=item.id,
            ok=True,
            checked_url=str(item.url),
            status_code=200,
            latency_ms=6,
            error=None,
            level="online",
            reason="ok",
            error_kind=None,
        )

    monkeypatch.setattr(dashboard_module, "probe_item_health", fake_probe_item_health)

    first = await api_client.get("/api/v1/dashboard/health")
    assert first.status_code == httpx.codes.OK
    assert probe_calls == 3

    second = await api_client.get("/api/v1/dashboard/health")
    assert second.status_code == httpx.codes.OK
    assert probe_calls == 3
    assert second.json()["items"][0]["level"] == "online"


async def test_dashboard_health_stream_returns_initial_snapshot_event(
    api_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_probe_item_health(**kwargs: object) -> ItemHealthStatus:
        item = kwargs["item"]
        return ItemHealthStatus(
            item_id=item.id,
            ok=True,
            checked_url=str(item.url),
            status_code=200,
            latency_ms=8,
            error=None,
            level="online",
            reason="ok",
            error_kind=None,
        )

    monkeypatch.setattr(dashboard_module, "probe_item_health", fake_probe_item_health)

    async with api_client.stream("GET", "/api/v1/dashboard/health/stream?item_id=svc-link&once=true") as response:
        assert response.status_code == httpx.codes.OK
        chunks = []
        async for chunk in response.aiter_text():
            chunks.append(chunk)
            if "\n\n" in chunk or "\n\n" in "".join(chunks):
                break

    payload = "".join(chunks)
    assert "event: snapshot" in payload
    assert "id:" in payload
    data_lines = [line for line in payload.splitlines() if line.startswith("data: ")]
    assert data_lines
    decoded = json.loads(data_lines[0].removeprefix("data: "))
    assert decoded["items"][0]["item_id"] == "svc-link"


async def test_health_runtime_background_loop_supports_manual_refresh_signal(
    app_container: AppContainer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app_container.settings.health_refresh_sec = 60

    async def fake_probe_item_health(**kwargs: object) -> ItemHealthStatus:
        item = kwargs["item"]
        return ItemHealthStatus(
            item_id=item.id,
            ok=True,
            checked_url=str(item.url),
            status_code=200,
            latency_ms=4,
            error=None,
            level="online",
            reason="ok",
            error_kind=None,
        )

    monkeypatch.setattr(dashboard_module, "probe_item_health", fake_probe_item_health)

    await dashboard_module.start_health_runtime(app_container)
    try:
        # Allow loop to build the initial snapshot.
        await asyncio.sleep(0.05)
        first = dashboard_module._HEALTH_RUNTIME.snapshot()
        assert first is not None

        timed_out_revision = await dashboard_module._HEALTH_RUNTIME.wait_for_revision_after(
            revision=first.revision,
            timeout_sec=0.01,
        )
        assert timed_out_revision == first.revision

        await dashboard_module._HEALTH_RUNTIME.request_refresh()
        updated_revision = await dashboard_module._HEALTH_RUNTIME.wait_for_revision_after(
            revision=first.revision,
            timeout_sec=0.5,
        )
        assert updated_revision > first.revision
    finally:
        await dashboard_module.stop_health_runtime()


async def test_get_dashboard_health_includes_item_status_history(
    api_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen_count: dict[str, int] = {}

    async def fake_probe_item_health(**kwargs: object) -> ItemHealthStatus:
        item = kwargs["item"]
        count = seen_count.get(item.id, 0) + 1
        seen_count[item.id] = count

        if item.id == "svc-link" and count >= 2:
            return ItemHealthStatus(
                item_id=item.id,
                ok=False,
                checked_url=str(item.url),
                status_code=503,
                latency_ms=21,
                error="HTTP 503",
                level="down",
                reason="http_5xx",
                error_kind="http_error",
            )

        return ItemHealthStatus(
            item_id=item.id,
            ok=True,
            checked_url=str(item.url),
            status_code=200,
            latency_ms=9,
            error=None,
            level="online",
            reason="ok",
            error_kind=None,
        )

    monkeypatch.setattr(dashboard_module, "probe_item_health", fake_probe_item_health)

    first = await api_client.get("/api/v1/dashboard/health?item_id=svc-link")
    assert first.status_code == httpx.codes.OK
    assert len(first.json()["items"][0]["history"]) == 1

    second = await api_client.get("/api/v1/dashboard/health?item_id=svc-link")
    assert second.status_code == httpx.codes.OK
    item_payload = second.json()["items"][0]

    assert len(item_payload["history"]) == 2
    assert item_payload["history"][0]["level"] == "online"
    assert item_payload["history"][1]["level"] == "down"
    assert "ts" in item_payload["history"][1]


async def test_get_dashboard_health_persists_health_samples_in_db(
    api_client: AsyncClient,
    app_container: AppContainer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_probe_item_health(**kwargs: object) -> ItemHealthStatus:
        item = kwargs["item"]
        return ItemHealthStatus(
            item_id=item.id,
            ok=True,
            checked_url=str(item.url),
            status_code=200,
            latency_ms=4,
            error=None,
            level="online",
            reason="ok",
            error_kind=None,
        )

    monkeypatch.setattr(dashboard_module, "probe_item_health", fake_probe_item_health)
    response = await api_client.get("/api/v1/dashboard/health?item_id=svc-link")
    assert response.status_code == httpx.codes.OK

    with app_container.db_session_factory() as session:
        samples = session.scalars(select(HealthSample).where(HealthSample.item_id == "svc-link")).all()
    assert len(samples) == 1
    assert samples[0].level == "online"


async def test_get_dashboard_health_hydrates_history_from_db_after_memory_reset(
    api_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sequence = ["online", "down"]
    seen_count = 0

    async def fake_probe_item_health(**kwargs: object) -> ItemHealthStatus:
        nonlocal seen_count
        item = kwargs["item"]

        if item.id != "svc-link":
            return ItemHealthStatus(
                item_id=item.id,
                ok=True,
                checked_url=str(item.url),
                status_code=200,
                latency_ms=5,
                error=None,
                level="online",
                reason="ok",
                error_kind=None,
            )

        seen_count += 1
        level = sequence[min(seen_count - 1, len(sequence) - 1)]
        if level == "online":
            return ItemHealthStatus(
                item_id=item.id,
                ok=True,
                checked_url=str(item.url),
                status_code=200,
                latency_ms=7,
                error=None,
                level="online",
                reason="ok",
                error_kind=None,
            )
        return ItemHealthStatus(
            item_id=item.id,
            ok=False,
            checked_url=str(item.url),
            status_code=503,
            latency_ms=25,
            error="HTTP 503",
            level="down",
            reason="http_5xx",
            error_kind="http_error",
        )

    monkeypatch.setattr(dashboard_module, "probe_item_health", fake_probe_item_health)

    first = await api_client.get("/api/v1/dashboard/health?item_id=svc-link")
    assert first.status_code == httpx.codes.OK
    assert len(first.json()["items"][0]["history"]) == 1

    dashboard_module._HEALTH_HISTORY_BY_ITEM.clear()

    second = await api_client.get("/api/v1/dashboard/health?item_id=svc-link")
    assert second.status_code == httpx.codes.OK
    history = second.json()["items"][0]["history"]
    assert len(history) == 2
    assert [point["level"] for point in history] == ["online", "down"]


async def test_get_dashboard_health_history_respects_max_points(
    api_client: AsyncClient,
    app_container: AppContainer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sequence = ["online", "degraded", "down"]
    seen_count = 0

    async def fake_probe_item_health(**kwargs: object) -> ItemHealthStatus:
        nonlocal seen_count
        item = kwargs["item"]

        if item.id != "svc-link":
            return ItemHealthStatus(
                item_id=item.id,
                ok=True,
                checked_url=str(item.url),
                status_code=200,
                latency_ms=5,
                error=None,
                level="online",
                reason="ok",
                error_kind=None,
            )

        seen_count += 1
        level = sequence[min(seen_count - 1, len(sequence) - 1)]
        if level == "online":
            return ItemHealthStatus(
                item_id=item.id,
                ok=True,
                checked_url=str(item.url),
                status_code=200,
                latency_ms=7,
                error=None,
                level="online",
                reason="ok",
                error_kind=None,
            )
        if level == "degraded":
            return ItemHealthStatus(
                item_id=item.id,
                ok=False,
                checked_url=str(item.url),
                status_code=429,
                latency_ms=1300,
                error="HTTP 429",
                level="degraded",
                reason="http_4xx",
                error_kind="http_error",
            )
        return ItemHealthStatus(
            item_id=item.id,
            ok=False,
            checked_url=str(item.url),
            status_code=503,
            latency_ms=25,
            error="HTTP 503",
            level="down",
            reason="http_5xx",
            error_kind="http_error",
        )

    monkeypatch.setattr(dashboard_module, "_health_history_size", lambda _settings: 2)
    monkeypatch.setattr(dashboard_module, "probe_item_health", fake_probe_item_health)

    await api_client.get("/api/v1/dashboard/health?item_id=svc-link")
    await api_client.get("/api/v1/dashboard/health?item_id=svc-link")
    third = await api_client.get("/api/v1/dashboard/health?item_id=svc-link")
    assert third.status_code == httpx.codes.OK

    history = third.json()["items"][0]["history"]
    assert len(history) == 2
    assert [point["level"] for point in history] == ["degraded", "down"]

    with app_container.db_session_factory() as session:
        rows = session.scalars(
            select(HealthSample)
            .where(HealthSample.item_id == "svc-link")
            .order_by(HealthSample.ts.asc(), HealthSample.id.asc())
        ).all()
    assert len(rows) == 2
    assert [row.level for row in rows] == ["degraded", "down"]


async def test_get_dashboard_health_prunes_history_for_removed_items(
    api_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dashboard_module._HEALTH_HISTORY_BY_ITEM["stale-item"] = deque(maxlen=3)

    async def fake_probe_item_health(**kwargs: object) -> ItemHealthStatus:
        item = kwargs["item"]
        return ItemHealthStatus(
            item_id=item.id,
            ok=True,
            checked_url=str(item.url),
            status_code=200,
            latency_ms=7,
            error=None,
            level="online",
            reason="ok",
            error_kind=None,
        )

    monkeypatch.setattr(dashboard_module, "probe_item_health", fake_probe_item_health)

    response = await api_client.get("/api/v1/dashboard/health?item_id=svc-link")
    assert response.status_code == httpx.codes.OK

    assert "stale-item" not in dashboard_module._HEALTH_HISTORY_BY_ITEM
    assert "svc-link" in dashboard_module._HEALTH_HISTORY_BY_ITEM


async def test_get_dashboard_health_marks_indirect_failure_from_dependencies(
    api_client: AsyncClient,
    app_container: AppContainer,
    dashboard_config: DashboardConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = LinkItemConfig(id="svc-parent", type="link", title="Parent", url="https://parent.local/")
    child = LinkItemConfig(
        id="svc-child",
        type="link",
        title="Child",
        url="https://child.local/",
        depends_on=["svc-parent"],
    )
    config = _config_with_items(dashboard_config, [parent, child])
    monkeypatch.setattr(app_container.config_service, "load", lambda *args, **kwargs: config)

    async def fake_probe_item_health(**kwargs: object) -> ItemHealthStatus:
        item = kwargs["item"]
        if item.id == "svc-parent":
            return ItemHealthStatus(
                item_id=item.id,
                ok=False,
                checked_url=str(item.url),
                status_code=503,
                latency_ms=12,
                error="HTTP 503",
                level="down",
                reason="http_5xx",
                error_kind="http_error",
            )
        return ItemHealthStatus(
            item_id=item.id,
            ok=True,
            checked_url=str(item.url),
            status_code=200,
            latency_ms=8,
            error=None,
            level="online",
            reason="ok",
            error_kind=None,
        )

    monkeypatch.setattr(dashboard_module, "probe_item_health", fake_probe_item_health)
    response = await api_client.get("/api/v1/dashboard/health")
    assert response.status_code == httpx.codes.OK
    payload = {entry["item_id"]: entry for entry in response.json()["items"]}

    assert payload["svc-parent"]["level"] == "down"
    assert payload["svc-child"]["level"] == "indirect_failure"
    assert payload["svc-child"]["reason"] == "indirect_dependency"
    assert "svc-parent" in payload["svc-child"]["error"]


async def test_get_dashboard_health_marks_missing_dependency_as_degraded(
    api_client: AsyncClient,
    app_container: AppContainer,
    dashboard_config: DashboardConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = LinkItemConfig(
        id="svc-child",
        type="link",
        title="Child",
        url="https://child.local/",
        depends_on=["svc-missing"],
    )
    config = _config_with_items(dashboard_config, [item])
    monkeypatch.setattr(app_container.config_service, "load", lambda *args, **kwargs: config)

    async def fake_probe_item_health(**kwargs: object) -> ItemHealthStatus:
        svc = kwargs["item"]
        return ItemHealthStatus(
            item_id=svc.id,
            ok=True,
            checked_url=str(svc.url),
            status_code=200,
            latency_ms=5,
            error=None,
            level="online",
            reason="ok",
            error_kind=None,
        )

    monkeypatch.setattr(dashboard_module, "probe_item_health", fake_probe_item_health)
    response = await api_client.get("/api/v1/dashboard/health")
    assert response.status_code == httpx.codes.OK
    payload = response.json()["items"][0]
    assert payload["level"] == "degraded"
    assert payload["reason"] == "missing_dependency"
    assert payload["error_kind"] is None
    assert "svc-missing" in payload["error"]


async def test_get_dashboard_health_marks_dependency_cycle_as_degraded(
    api_client: AsyncClient,
    app_container: AppContainer,
    dashboard_config: DashboardConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item_a = LinkItemConfig(
        id="svc-a",
        type="link",
        title="A",
        url="https://a.local/",
        depends_on=["svc-b"],
    )
    item_b = LinkItemConfig(
        id="svc-b",
        type="link",
        title="B",
        url="https://b.local/",
        depends_on=["svc-a"],
    )
    config = _config_with_items(dashboard_config, [item_a, item_b])
    monkeypatch.setattr(app_container.config_service, "load", lambda *args, **kwargs: config)

    async def fake_probe_item_health(**kwargs: object) -> ItemHealthStatus:
        item = kwargs["item"]
        return ItemHealthStatus(
            item_id=item.id,
            ok=True,
            checked_url=str(item.url),
            status_code=200,
            latency_ms=10,
            error=None,
            level="online",
            reason="ok",
            error_kind=None,
        )

    monkeypatch.setattr(dashboard_module, "probe_item_health", fake_probe_item_health)
    response = await api_client.get("/api/v1/dashboard/health")
    assert response.status_code == httpx.codes.OK
    payload = {entry["item_id"]: entry for entry in response.json()["items"]}
    assert payload["svc-a"]["level"] == "degraded"
    assert payload["svc-a"]["reason"] == "dependency_cycle"
    assert payload["svc-b"]["level"] == "degraded"
    assert payload["svc-b"]["reason"] == "dependency_cycle"


async def test_get_dashboard_health_item_filter_probes_dependencies_but_returns_requested_only(
    api_client: AsyncClient,
    app_container: AppContainer,
    dashboard_config: DashboardConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent = LinkItemConfig(id="svc-parent", type="link", title="Parent", url="https://parent.local/")
    child = LinkItemConfig(
        id="svc-child",
        type="link",
        title="Child",
        url="https://child.local/",
        depends_on=["svc-parent"],
    )
    config = _config_with_items(dashboard_config, [parent, child])
    monkeypatch.setattr(app_container.config_service, "load", lambda *args, **kwargs: config)

    probed_ids: list[str] = []

    async def fake_probe_item_health(**kwargs: object) -> ItemHealthStatus:
        item = kwargs["item"]
        probed_ids.append(item.id)
        if item.id == "svc-parent":
            return ItemHealthStatus(
                item_id=item.id,
                ok=False,
                checked_url=str(item.url),
                status_code=503,
                latency_ms=9,
                error="HTTP 503",
                level="down",
                reason="http_5xx",
                error_kind="http_error",
            )
        return ItemHealthStatus(
            item_id=item.id,
            ok=True,
            checked_url=str(item.url),
            status_code=200,
            latency_ms=6,
            error=None,
            level="online",
            reason="ok",
            error_kind=None,
        )

    monkeypatch.setattr(dashboard_module, "probe_item_health", fake_probe_item_health)
    response = await api_client.get("/api/v1/dashboard/health?item_id=svc-child")
    assert response.status_code == httpx.codes.OK
    payload = response.json()["items"]

    assert set(probed_ids) == {"svc-parent", "svc-child"}
    assert len(payload) == 1
    assert payload[0]["item_id"] == "svc-child"
    assert payload[0]["level"] == "indirect_failure"
    assert payload[0]["reason"] == "indirect_dependency"


async def test_get_iframe_source_returns_direct_url_for_public_iframe(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/dashboard/iframe/svc-iframe-public/source")
    assert response.status_code == httpx.codes.OK
    payload = response.json()
    assert payload["proxied"] is False
    assert payload["src"].startswith("https://")


async def test_get_iframe_source_for_protected_item_sets_proxy_cookie(
    api_client: AsyncClient,
) -> None:
    authorized = await api_client.get("/api/v1/dashboard/iframe/svc-iframe-protected/source")

    assert authorized.status_code == httpx.codes.OK
    payload = authorized.json()
    assert payload["proxied"] is True
    assert payload["src"] == "/api/v1/dashboard/iframe/svc-iframe-protected/proxy"
    assert any("dashboard_proxy_access=" in cookie for cookie in authorized.headers.get_list("set-cookie"))


async def test_run_lan_scan_message_branches(
    api_client: AsyncClient,
    app_container: AppContainer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def accepted() -> bool:
        return True

    monkeypatch.setattr(app_container.lan_scan_service, "trigger_scan", accepted)
    monkeypatch.setattr(
        app_container.lan_scan_service,
        "state",
        lambda: LanScanStateResponse(enabled=True, running=False, queued=False),
    )
    accepted_response = await api_client.post("/api/v1/dashboard/lan/run")
    assert accepted_response.status_code == httpx.codes.OK
    assert accepted_response.json()["accepted"] is True

    async def queued() -> bool:
        return False

    monkeypatch.setattr(app_container.lan_scan_service, "trigger_scan", queued)
    monkeypatch.setattr(
        app_container.lan_scan_service,
        "state",
        lambda: LanScanStateResponse(enabled=True, running=True, queued=True),
    )
    queued_response = await api_client.post("/api/v1/dashboard/lan/run")
    assert queued_response.status_code == httpx.codes.OK
    assert queued_response.json()["state"]["queued"] is True


async def test_proxy_iframe_requires_access_cookie_for_protected_items(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/dashboard/iframe/svc-iframe-protected/proxy")
    assert response.status_code == httpx.codes.UNAUTHORIZED


async def test_proxy_iframe_streams_and_rewrites_headers(
    api_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeHeaders:
        def __init__(self) -> None:
            self._pairs = [
                ("content-type", "text/plain"),
                ("location", "https://example.local/login"),
                ("set-cookie", "session=abc; Domain=example.local; Path=/; HttpOnly"),
            ]

        def items(self) -> list[tuple[str, str]]:
            return list(self._pairs)

        def get_list(self, key: str) -> list[str]:
            lookup = key.lower()
            return [value for name, value in self._pairs if name.lower() == lookup]

    class FakeUpstreamResponse:
        status_code = 200
        headers = FakeHeaders()

        async def aiter_raw(self) -> AsyncIterator[bytes]:
            yield b"ok"

        async def aclose(self) -> None:
            return None

    class FakeProxyClient:
        def __init__(self, **_: object) -> None:
            self.closed = False

        def build_request(self, method: str, url: str, headers: dict[str, str], content: bytes) -> httpx.Request:
            return httpx.Request(method=method, url=url, headers=headers, content=content)

        async def send(self, _: httpx.Request, *, stream: bool) -> FakeUpstreamResponse:
            assert stream is True
            return FakeUpstreamResponse()

        async def aclose(self) -> None:
            self.closed = True

    monkeypatch.setattr(dashboard_module.httpx, "AsyncClient", FakeProxyClient)

    source = await api_client.get("/api/v1/dashboard/iframe/svc-iframe-protected/source")
    assert source.status_code == httpx.codes.OK

    proxy = await api_client.get("/api/v1/dashboard/iframe/svc-iframe-protected/proxy/path?x=1")
    assert proxy.status_code == httpx.codes.OK
    assert proxy.text == "ok"
    assert proxy.headers["location"].startswith("/api/v1/dashboard/iframe/svc-iframe-protected/proxy/")
    assert "set-cookie" in proxy.headers


async def test_proxy_iframe_returns_502_when_upstream_errors(
    api_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ErrorProxyClient:
        def __init__(self, **_: object) -> None:
            pass

        def build_request(self, method: str, url: str, headers: dict[str, str], content: bytes) -> httpx.Request:
            return httpx.Request(method=method, url=url, headers=headers, content=content)

        async def send(self, _: httpx.Request, *, stream: bool) -> httpx.Response:
            assert stream is True
            raise httpx.ConnectError("boom")

        async def aclose(self) -> None:
            return None

    monkeypatch.setattr(dashboard_module.httpx, "AsyncClient", ErrorProxyClient)
    await api_client.get("/api/v1/dashboard/iframe/svc-iframe-protected/source")
    response = await api_client.get("/api/v1/dashboard/iframe/svc-iframe-protected/proxy")
    assert response.status_code == httpx.codes.BAD_GATEWAY


async def test_get_dashboard_config_version_returns_422_when_service_validation_fails(
    api_client: AsyncClient,
    app_container: AppContainer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_get_version(*_: object, **__: object) -> object:
        raise DashboardConfigValidationError(
            [ValidationIssue(code="schema_error", path="$.version", message="invalid")]
        )

    monkeypatch.setattr(app_container.config_service, "get_version", fail_get_version)
    response = await api_client.get("/api/v1/dashboard/version")
    assert response.status_code == httpx.codes.UNPROCESSABLE_ENTITY


async def test_get_dashboard_last_errors_returns_issues(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/dashboard/errors")
    assert response.status_code == httpx.codes.OK
    assert isinstance(response.json()["issues"], list)


async def test_validate_dashboard_yaml_returns_validation_payload(api_client: AsyncClient) -> None:
    response = await api_client.post("/api/v1/dashboard/validate", json={"yaml": "version: 1\napp:\n  id: demo\n"})
    assert response.status_code == httpx.codes.OK
    assert "valid" in response.json()


async def test_save_dashboard_config_returns_422_when_service_validation_fails(
    api_client: AsyncClient,
    app_container: AppContainer,
    fake: Faker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_save(*_: object, **__: object) -> object:
        raise DashboardConfigValidationError([ValidationIssue(code="schema_error", path="$.groups", message="invalid")])

    monkeypatch.setattr(app_container.config_service, "save", fail_save)
    payload = build_dashboard_config(fake).model_dump(mode="json", exclude_none=True)
    response = await api_client.put("/api/v1/dashboard/config", json=payload)
    assert response.status_code == httpx.codes.UNPROCESSABLE_ENTITY


async def test_download_dashboard_config_backup_returns_422_when_service_validation_fails(
    api_client: AsyncClient,
    app_container: AppContainer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_export(*_: object, **__: object) -> object:
        raise DashboardConfigValidationError([ValidationIssue(code="schema_error", path="$.app", message="invalid")])

    monkeypatch.setattr(app_container.config_service, "export_yaml", fail_export)
    response = await api_client.get("/api/v1/dashboard/config/backup")
    assert response.status_code == httpx.codes.UNPROCESSABLE_ENTITY


async def test_restore_dashboard_config_returns_422_when_service_validation_fails(
    api_client: AsyncClient,
    app_container: AppContainer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_import(*_: object, **__: object) -> object:
        raise DashboardConfigValidationError(
            [ValidationIssue(code="schema_error", path="$.app.title", message="invalid")]
        )

    monkeypatch.setattr(app_container.config_service, "import_yaml", fail_import)
    response = await api_client.post("/api/v1/dashboard/config/restore", json={"yaml": "version: 1"})
    assert response.status_code == httpx.codes.UNPROCESSABLE_ENTITY


async def test_get_dashboard_health_returns_422_when_service_validation_fails(
    api_client: AsyncClient,
    app_container: AppContainer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_load(*_: object, **__: object) -> object:
        raise DashboardConfigValidationError([ValidationIssue(code="schema_error", path="$.groups", message="invalid")])

    monkeypatch.setattr(app_container.config_service, "load", fail_load)
    response = await api_client.get("/api/v1/dashboard/health")
    assert response.status_code == httpx.codes.UNPROCESSABLE_ENTITY


async def test_dashboard_health_stream_returns_422_when_service_validation_fails(
    api_client: AsyncClient,
    app_container: AppContainer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_load(*_: object, **__: object) -> object:
        raise DashboardConfigValidationError([ValidationIssue(code="schema_error", path="$.groups", message="invalid")])

    monkeypatch.setattr(app_container.config_service, "load", fail_load)
    response = await api_client.get("/api/v1/dashboard/health/stream?once=true")
    assert response.status_code == httpx.codes.UNPROCESSABLE_ENTITY


async def test_dashboard_health_stream_emits_keepalive_when_revision_does_not_change(
    app_container: AppContainer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_probe_item_health(**kwargs: object) -> ItemHealthStatus:
        item = kwargs["item"]
        return ItemHealthStatus(
            item_id=item.id,
            ok=True,
            checked_url=str(item.url),
            status_code=200,
            latency_ms=8,
            error=None,
            level="online",
            reason="ok",
            error_kind=None,
        )

    async def same_revision(*, revision: int, timeout_sec: float) -> int:
        _ = timeout_sec
        return revision

    monkeypatch.setattr(dashboard_module, "probe_item_health", fake_probe_item_health)
    monkeypatch.setattr(dashboard_module._HEALTH_RUNTIME, "wait_for_revision_after", same_revision)

    class FakeRequest:
        async def is_disconnected(self) -> bool:
            return False

    response = await health_router_module.stream_dashboard_health(
        request=FakeRequest(),
        config_service=app_container.config_service,
        settings=app_container.settings,
        health_sample_repository=app_container.health_sample_repository,
        item_id=["svc-link"],
        once=False,
    )
    iterator = response.body_iterator
    initial_chunk = await anext(iterator)
    keepalive_chunk = await anext(iterator)
    await iterator.aclose()

    initial_text = initial_chunk.decode() if isinstance(initial_chunk, bytes) else initial_chunk
    keepalive_text = keepalive_chunk.decode() if isinstance(keepalive_chunk, bytes) else keepalive_chunk
    assert "event: snapshot" in initial_text
    assert ": keepalive" in keepalive_text


async def test_dashboard_health_stream_refreshes_when_runtime_snapshot_is_missing(
    app_container: AppContainer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_probe_item_health(**kwargs: object) -> ItemHealthStatus:
        item = kwargs["item"]
        return ItemHealthStatus(
            item_id=item.id,
            ok=True,
            checked_url=str(item.url),
            status_code=200,
            latency_ms=8,
            error=None,
            level="online",
            reason="ok",
            error_kind=None,
        )

    async def increment_revision(*, revision: int, timeout_sec: float) -> int:
        _ = timeout_sec
        return revision + 1

    snapshot_calls = 0
    original_snapshot = dashboard_module._HEALTH_RUNTIME.snapshot

    def snapshot_with_gap() -> object:
        nonlocal snapshot_calls
        snapshot_calls += 1
        if snapshot_calls == 1:
            return None
        return original_snapshot()

    monkeypatch.setattr(dashboard_module, "probe_item_health", fake_probe_item_health)
    monkeypatch.setattr(dashboard_module._HEALTH_RUNTIME, "wait_for_revision_after", increment_revision)
    monkeypatch.setattr(dashboard_module._HEALTH_RUNTIME, "snapshot", snapshot_with_gap)

    class FakeRequest:
        async def is_disconnected(self) -> bool:
            return False

    response = await health_router_module.stream_dashboard_health(
        request=FakeRequest(),
        config_service=app_container.config_service,
        settings=app_container.settings,
        health_sample_repository=app_container.health_sample_repository,
        item_id=["svc-link"],
        once=False,
    )
    iterator = response.body_iterator
    first_chunk = await anext(iterator)
    second_chunk = await anext(iterator)
    await iterator.aclose()

    first_text = first_chunk.decode() if isinstance(first_chunk, bytes) else first_chunk
    second_text = second_chunk.decode() if isinstance(second_chunk, bytes) else second_chunk
    assert "event: snapshot" in first_text
    assert "event: snapshot" in second_text
    assert snapshot_calls >= 1


async def test_get_lan_scan_state_returns_current_state(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/dashboard/lan/state")
    assert response.status_code == httpx.codes.OK
    assert "enabled" in response.json()


async def test_run_lan_scan_returns_disabled_message(
    api_client: AsyncClient,
    app_container: AppContainer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def disabled_trigger() -> bool:
        return False

    monkeypatch.setattr(app_container.lan_scan_service, "trigger_scan", disabled_trigger)
    monkeypatch.setattr(
        app_container.lan_scan_service,
        "state",
        lambda: LanScanStateResponse(enabled=False, running=False, queued=False),
    )

    response = await api_client.post("/api/v1/dashboard/lan/run")
    assert response.status_code == httpx.codes.OK
    assert response.json()["message"] == "Сканирование отключено"
