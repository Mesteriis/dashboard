from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import depens.v1.health_runtime as dashboard_module
from api.v1.metrics import metrics_router
from config.container import AppContainer
from scheme.dashboard import ItemHealthStatus, LanScanHost, LanScanResult, LanScanStateResponse

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def clear_metrics_runtime_state() -> None:
    dashboard_module.reset_health_runtime_state()


@pytest.fixture()
def metrics_app(app_container: AppContainer) -> FastAPI:
    app = FastAPI()
    app.state.container = app_container
    app.include_router(metrics_router)
    return app


@pytest_asyncio.fixture()
async def metrics_client(metrics_app: FastAPI) -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=metrics_app), base_url="http://testserver") as client:
        yield client


async def test_metrics_endpoint_returns_prometheus_payload_with_dashboard_snapshot(
    metrics_client: AsyncClient,
    app_container: AppContainer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = app_container.config_service.load()
    item = config.groups[0].subgroups[0].items[0]
    status = ItemHealthStatus(
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

    dashboard_module._HEALTH_RUNTIME._snapshot = dashboard_module.HealthSnapshot(
        config=config,
        statuses_by_id={item.id: status},
        updated_at=datetime.now(UTC),
        revision=7,
    )

    now = datetime.now(UTC)
    monkeypatch.setattr(
        app_container.lan_scan_service,
        "state",
        lambda: LanScanStateResponse(
            enabled=True,
            running=False,
            queued=False,
            last_finished_at=now,
            result=LanScanResult(
                generated_at=now,
                duration_ms=11,
                scanned_hosts=1,
                hosts=[LanScanHost(ip="10.0.0.1")],
            ),
        ),
    )

    response = await metrics_client.get("/metrics")
    assert response.status_code == httpx.codes.OK
    assert "text/plain" in response.headers["content-type"]
    assert "oko_dashboard_info" in response.text
    assert "oko_config_revision" in response.text
    assert "oko_health_status" in response.text
    assert "oko_lan_scan_hosts_discovered" in response.text


async def test_metrics_endpoint_swallow_errors_from_metric_collection(
    metrics_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_snapshot() -> object:
        raise RuntimeError("boom")

    monkeypatch.setattr(dashboard_module._HEALTH_RUNTIME, "snapshot", fail_snapshot)

    response = await metrics_client.get("/metrics/")
    assert response.status_code == httpx.codes.OK
    assert "oko_dashboard_info" in response.text
