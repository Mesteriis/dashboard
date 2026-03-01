from __future__ import annotations

import importlib
from pathlib import Path

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.asyncio


DEFAULT_BOOTSTRAP = """\
version: 1
app:
  id: demo
  title: Demo
widgets:
  - type: system.status
"""


def _reload_main_module():
    module = importlib.import_module("main")
    container = getattr(module, "container", None)
    if container is not None:
        container.db_engine.sync_engine.dispose()
    return importlib.reload(module)


def _headers(*capabilities: str) -> dict[str, str]:
    return {
        "X-Oko-Actor": "tester",
        "X-Oko-Capabilities": ",".join(capabilities),
    }


async def _client(main_module):
    async with (
        main_module.app.router.lifespan_context(main_module.app),
        AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://test") as client,
    ):
        yield client


async def test_plugin_manifest_v1_for_autodiscover(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = (tmp_path / "oko.sqlite3").resolve()
    bootstrap = (tmp_path / "bootstrap.yaml").resolve()
    bootstrap.write_text(DEFAULT_BOOTSTRAP, encoding="utf-8")

    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("BROKER_URL", "memory://local")
    monkeypatch.setenv("OKO_BOOTSTRAP_CONFIG_FILE", str(bootstrap))

    main_module = _reload_main_module()
    headers = _headers(
        "read.plugins.list",
        "read.plugins.manifest",
        "read.plugins.services",
    )

    async for client in _client(main_module):
        response = await client.get(
            "/api/v1/plugins/autodiscover/manifest",
            headers=headers,
        )
        assert response.status_code == httpx.codes.OK
        payload = response.json()
        assert payload["plugin_id"] == "autodiscover"
        manifest = payload["manifest"]
        assert manifest["manifest_version"] == "1.0"
        assert manifest["plugin_api_version"] == "1.0"
        assert manifest["page"]["enabled"] is True
        assert manifest["page"]["layout"] == "content-only"
        components = manifest["page"]["components"]
        assert isinstance(components, list)
        table = next((entry for entry in components if entry.get("type") == "data-table"), None)
        assert table is not None
        assert table["groupBy"] == [
            {"field": "host_ip", "label": "Host", "emptyLabel": "Unknown Host"},
            {"field": "service", "label": "Service", "emptyLabel": "Unknown Service"},
        ]
        assert payload["negotiation"]["accepted"] is True
        assert payload["negotiation"]["fallback_used"] is False


async def test_plugin_services_endpoint_for_autodiscover(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = (tmp_path / "oko.sqlite3").resolve()
    bootstrap = (tmp_path / "bootstrap.yaml").resolve()
    bootstrap.write_text(DEFAULT_BOOTSTRAP, encoding="utf-8")

    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("BROKER_URL", "memory://local")
    monkeypatch.setenv("OKO_BOOTSTRAP_CONFIG_FILE", str(bootstrap))

    main_module = _reload_main_module()
    headers = _headers("read.plugins.services")

    async for client in _client(main_module):
        response = await client.get(
            "/api/v1/plugins/autodiscover/services",
            headers=headers,
        )
        assert response.status_code == httpx.codes.OK
        payload = response.json()
        assert payload["plugin_id"] == "autodiscover"
        assert isinstance(payload["services"], list)
        assert payload["total"] == len(payload["services"])
        if payload["services"]:
            first = payload["services"][0]
            assert "host_ip" in first
            assert "port" in first


async def test_plugin_manifest_requires_capability(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = (tmp_path / "oko.sqlite3").resolve()
    bootstrap = (tmp_path / "bootstrap.yaml").resolve()
    bootstrap.write_text(DEFAULT_BOOTSTRAP, encoding="utf-8")

    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("BROKER_URL", "memory://local")
    monkeypatch.setenv("OKO_BOOTSTRAP_CONFIG_FILE", str(bootstrap))

    main_module = _reload_main_module()

    async for client in _client(main_module):
        response = await client.get(
            "/api/v1/plugins/autodiscover/manifest",
            headers=_headers("read.plugins.list"),
        )
        assert response.status_code == httpx.codes.FORBIDDEN
        assert response.json()["code"] == "capability_required"
