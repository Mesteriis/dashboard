from __future__ import annotations

import asyncio

import pytest

from scheme.dashboard import HealthcheckConfig, LinkItemConfig
from tools.health import probe_item_health


@pytest.mark.asyncio
async def test_probe_item_health_uses_item_healthcheck_url_and_success_status() -> None:
    class DummyResponse:
        status_code = 200

    class DummyClient:
        def __init__(self) -> None:
            self.last_url: str | None = None
            self.last_timeout: float | None = None

        async def get(self, url: str, timeout: float) -> DummyResponse:
            self.last_url = url
            self.last_timeout = timeout
            return DummyResponse()

    client = DummyClient()
    item = LinkItemConfig(
        id="svc",
        type="link",
        title="Service",
        url="https://example.local/",
        healthcheck=HealthcheckConfig(url="https://health.local/ping", timeout_ms=750),
    )
    result = await probe_item_health(
        item=item,
        client=client,  # type: ignore[arg-type]
        semaphore=asyncio.Semaphore(1),
        default_timeout_sec=4.0,
    )

    assert result.ok is True
    assert result.checked_url == "https://health.local/ping"
    assert result.status_code == 200
    assert client.last_timeout == 0.75


@pytest.mark.asyncio
async def test_probe_item_health_marks_non_2xx_as_failed() -> None:
    class DummyResponse:
        status_code = 503

    class DummyClient:
        async def get(self, url: str, timeout: float) -> DummyResponse:
            return DummyResponse()

    item = LinkItemConfig(
        id="svc",
        type="link",
        title="Service",
        url="https://example.local/",
    )
    result = await probe_item_health(
        item=item,
        client=DummyClient(),  # type: ignore[arg-type]
        semaphore=asyncio.Semaphore(1),
        default_timeout_sec=4.0,
    )

    assert result.ok is False
    assert result.error == "HTTP 503"


@pytest.mark.asyncio
async def test_probe_item_health_captures_client_exception() -> None:
    class FailingClient:
        async def get(self, url: str, timeout: float) -> object:
            raise RuntimeError("network down")

    item = LinkItemConfig(
        id="svc",
        type="link",
        title="Service",
        url="https://example.local/",
    )
    result = await probe_item_health(
        item=item,
        client=FailingClient(),  # type: ignore[arg-type]
        semaphore=asyncio.Semaphore(1),
        default_timeout_sec=4.0,
    )
    assert result.ok is False
    assert result.error == "network down"
