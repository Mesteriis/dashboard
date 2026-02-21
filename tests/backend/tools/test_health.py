from __future__ import annotations

import asyncio

import httpx
import pytest

import tools.health as health_module
from scheme.dashboard import HealthcheckConfig, HealthcheckThresholds, LinkItemConfig
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
    assert result.level == "online"
    assert result.reason == "ok"
    assert result.error_kind is None
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
    assert result.level == "down"
    assert result.reason == "http_5xx"
    assert result.error_kind == "http_error"
    assert result.error == "HTTP 503"


@pytest.mark.asyncio
async def test_probe_item_health_marks_http_4xx_as_degraded_by_default() -> None:
    class DummyResponse:
        status_code = 404

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
    assert result.level == "degraded"
    assert result.reason == "http_4xx"
    assert result.error_kind == "http_error"
    assert result.error == "HTTP 404"


@pytest.mark.asyncio
async def test_probe_item_health_marks_high_latency_as_degraded(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyResponse:
        status_code = 200

    class DummyClient:
        async def get(self, url: str, timeout: float) -> DummyResponse:
            return DummyResponse()

    timer_values = iter([10.0, 10.3])
    monkeypatch.setattr(health_module, "perf_counter", lambda: next(timer_values))

    item = LinkItemConfig(
        id="svc",
        type="link",
        title="Service",
        url="https://example.local/",
        healthcheck=HealthcheckConfig(
            url="https://health.local/ping",
            thresholds=HealthcheckThresholds(
                degraded_latency_ms=200,
                down_latency_ms=2000,
                degrade_on_http_4xx=True,
            ),
        ),
    )
    result = await probe_item_health(
        item=item,
        client=DummyClient(),  # type: ignore[arg-type]
        semaphore=asyncio.Semaphore(1),
        default_timeout_sec=4.0,
    )

    assert result.ok is False
    assert result.level == "degraded"
    assert result.reason == "latency_above_degraded_threshold"
    assert result.error_kind is None
    assert result.error == "Latency 300 ms"


@pytest.mark.asyncio
async def test_probe_item_health_classifies_timeout_exception() -> None:
    class FailingClient:
        async def get(self, url: str, timeout: float) -> object:
            raise httpx.ReadTimeout("timed out")

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
    assert result.level == "down"
    assert result.reason == "timeout"
    assert result.error_kind == "timeout"
    assert result.error == "timed out"


@pytest.mark.asyncio
async def test_probe_item_health_captures_unknown_exception_kind() -> None:
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
    assert result.level == "down"
    assert result.reason == "exception"
    assert result.error_kind == "unknown"
    assert result.error == "network down"
