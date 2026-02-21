from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
from faker import Faker
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from support.factories import build_dashboard_config

import api.v1.dashboard as dashboard_module
from api.v1.dashboard import dashboard_router
from config.container import AppContainer
from config.settings import ADMIN_TOKEN_HEADER
from scheme.dashboard import ItemHealthStatus, LanScanStateResponse, ValidationIssue
from service.config_service import DashboardConfigValidationError

pytestmark = pytest.mark.asyncio


async def test_get_dashboard_config_returns_current_model(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/dashboard/config")

    assert response.status_code == httpx.codes.OK
    payload = response.json()
    assert payload["app"]["id"] == "demo"
    assert payload["groups"][0]["id"] == "core"


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


async def test_put_dashboard_config_requires_admin_token(
    api_client: AsyncClient,
    fake: Faker,
) -> None:
    payload = build_dashboard_config(fake, title="Config Without Token").model_dump(mode="json", exclude_none=True)

    response = await api_client.put("/api/v1/dashboard/config", json=payload)
    assert response.status_code == httpx.codes.UNAUTHORIZED


async def test_put_dashboard_config_accepts_valid_admin_token(
    api_client: AsyncClient,
    fake: Faker,
    admin_token: str,
) -> None:
    payload = build_dashboard_config(fake, title="Config With Token").model_dump(mode="json", exclude_none=True)

    response = await api_client.put(
        "/api/v1/dashboard/config",
        json=payload,
        headers={ADMIN_TOKEN_HEADER: admin_token},
    )

    assert response.status_code == httpx.codes.OK
    response_payload = response.json()
    assert response_payload["config"]["app"]["title"] == "Config With Token"
    assert response_payload["version"]["sha256"]


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
    assert len(response.json()["items"]) == 1
    assert response.json()["items"][0]["item_id"] == "svc-link"


async def test_get_iframe_source_returns_direct_url_for_public_iframe(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/dashboard/iframe/svc-iframe-public/source")
    assert response.status_code == httpx.codes.OK
    payload = response.json()
    assert payload["proxied"] is False
    assert payload["src"].startswith("https://")


async def test_get_iframe_source_for_protected_item_sets_proxy_cookie(
    api_client: AsyncClient,
    admin_token: str,
) -> None:
    unauthorized = await api_client.get("/api/v1/dashboard/iframe/svc-iframe-protected/source")
    assert unauthorized.status_code == httpx.codes.UNAUTHORIZED

    authorized = await api_client.get(
        "/api/v1/dashboard/iframe/svc-iframe-protected/source",
        headers={ADMIN_TOKEN_HEADER: admin_token},
    )

    assert authorized.status_code == httpx.codes.OK
    payload = authorized.json()
    assert payload["proxied"] is True
    assert payload["src"] == "/api/v1/dashboard/iframe/svc-iframe-protected/proxy"
    assert any("dashboard_proxy_access=" in cookie for cookie in authorized.headers.get_list("set-cookie"))


async def test_run_lan_scan_message_branches(
    api_client: AsyncClient,
    app_container: AppContainer,
    admin_token: str,
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
    accepted_response = await api_client.post("/api/v1/dashboard/lan/run", headers={ADMIN_TOKEN_HEADER: admin_token})
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
    queued_response = await api_client.post("/api/v1/dashboard/lan/run", headers={ADMIN_TOKEN_HEADER: admin_token})
    assert queued_response.status_code == httpx.codes.OK
    assert queued_response.json()["state"]["queued"] is True


async def test_proxy_iframe_requires_access_cookie_for_protected_items(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/dashboard/iframe/svc-iframe-protected/proxy")
    assert response.status_code == httpx.codes.UNAUTHORIZED


async def test_proxy_iframe_streams_and_rewrites_headers(
    api_client: AsyncClient,
    admin_token: str,
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

    source = await api_client.get(
        "/api/v1/dashboard/iframe/svc-iframe-protected/source",
        headers={ADMIN_TOKEN_HEADER: admin_token},
    )
    assert source.status_code == httpx.codes.OK

    proxy = await api_client.get("/api/v1/dashboard/iframe/svc-iframe-protected/proxy/path?x=1")
    assert proxy.status_code == httpx.codes.OK
    assert proxy.text == "ok"
    assert proxy.headers["location"].startswith("/api/v1/dashboard/iframe/svc-iframe-protected/proxy/")
    assert "set-cookie" in proxy.headers


async def test_proxy_iframe_returns_502_when_upstream_errors(
    api_client: AsyncClient,
    admin_token: str,
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
    await api_client.get(
        "/api/v1/dashboard/iframe/svc-iframe-protected/source",
        headers={ADMIN_TOKEN_HEADER: admin_token},
    )
    response = await api_client.get("/api/v1/dashboard/iframe/svc-iframe-protected/proxy")
    assert response.status_code == httpx.codes.BAD_GATEWAY
