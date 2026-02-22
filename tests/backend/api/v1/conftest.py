from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from faker import Faker
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from support.factories import build_dashboard_config, write_dashboard_yaml

from api.v1.dashboard import dashboard_router
from config.container import AppContainer, build_container
from scheme.dashboard import DashboardConfig
from tools.events import build_lifespan


@pytest.fixture()
def dashboard_config(fake: Faker) -> DashboardConfig:
    return build_dashboard_config(fake)


@pytest.fixture()
def dashboard_config_path(tmp_path: Path, dashboard_config: DashboardConfig) -> Path:
    config_path = (tmp_path / "dashboard.yaml").resolve()
    return write_dashboard_yaml(config_path, dashboard_config)


@pytest.fixture()
def app_container(
    project_root: Path,
    tmp_path: Path,
    dashboard_config_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> AppContainer:
    db_path = (tmp_path / "dashboard.sqlite3").resolve()
    monkeypatch.setenv("DASHBOARD_CONFIG_FILE", str(dashboard_config_path.resolve()))
    monkeypatch.setenv("DASHBOARD_DB_FILE", str(db_path))
    monkeypatch.setenv("DASHBOARD_PROXY_TOKEN_SECRET", "test-proxy-secret")
    monkeypatch.setenv("LAN_SCAN_ENABLED", "false")

    return build_container(base_dir=(project_root / "src").resolve())


@pytest.fixture()
def api_app(app_container: AppContainer) -> FastAPI:
    app = FastAPI(
        lifespan=build_lifespan(
            app_container.lan_scan_service,
            shutdown_callbacks=[app_container.db_engine.dispose],
        )
    )
    app.state.container = app_container
    app.include_router(dashboard_router)
    return app


@pytest_asyncio.fixture()
async def api_client(api_app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=api_app)
    async with (
        api_app.router.lifespan_context(api_app),
        AsyncClient(transport=transport, base_url="http://testserver") as client,
    ):
        yield client
