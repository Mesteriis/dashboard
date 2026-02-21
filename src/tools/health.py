from __future__ import annotations

import asyncio
import socket
import ssl
from time import perf_counter
from typing import Literal

import httpx

from scheme.dashboard import ItemConfig, ItemHealthStatus, LinkItemConfig

DEFAULT_DEGRADED_LATENCY_MS = 700
DEFAULT_DOWN_LATENCY_MS = 3000
MIN_TIMEOUT_SEC = 0.2

HealthLevel = Literal["online", "degraded", "down", "unknown", "indirect_failure"]
HealthErrorKind = Literal["timeout", "dns_error", "ssl_error", "connection_error", "http_error", "unknown"]


def _health_thresholds(item: ItemConfig) -> tuple[int, int, bool]:
    if isinstance(item, LinkItemConfig) and item.healthcheck and item.healthcheck.thresholds:
        thresholds = item.healthcheck.thresholds
        degraded_latency_ms = thresholds.degraded_latency_ms
        down_latency_ms = max(thresholds.down_latency_ms, degraded_latency_ms)
        return degraded_latency_ms, down_latency_ms, thresholds.degrade_on_http_4xx
    return DEFAULT_DEGRADED_LATENCY_MS, DEFAULT_DOWN_LATENCY_MS, True


def _classify_http_result(
    *,
    status_code: int,
    latency_ms: int,
    degraded_latency_ms: int,
    down_latency_ms: int,
    degrade_on_http_4xx: bool,
) -> tuple[HealthLevel, str, HealthErrorKind | None, str | None]:
    if 500 <= status_code <= 599:
        return "down", "http_5xx", "http_error", f"HTTP {status_code}"

    if 400 <= status_code <= 499:
        if degrade_on_http_4xx:
            return "degraded", "http_4xx", "http_error", f"HTTP {status_code}"
        return "down", "http_4xx", "http_error", f"HTTP {status_code}"

    if not 200 <= status_code < 400:
        return "down", "http_error", "http_error", f"HTTP {status_code}"

    if latency_ms >= down_latency_ms:
        return "down", "latency_above_down_threshold", None, f"Latency {latency_ms} ms"

    if latency_ms >= degraded_latency_ms:
        return "degraded", "latency_above_degraded_threshold", None, f"Latency {latency_ms} ms"

    return "online", "ok", None, None


def _classify_exception(exc: Exception) -> tuple[HealthErrorKind, str]:
    if isinstance(exc, httpx.TimeoutException):
        return "timeout", "timeout"

    if isinstance(exc, httpx.ConnectError):
        cause = exc.__cause__
        if isinstance(cause, ssl.SSLError):
            return "ssl_error", "ssl_error"
        if isinstance(cause, socket.gaierror):
            return "dns_error", "dns_error"
        return "connection_error", "connection_error"

    if isinstance(exc, httpx.NetworkError):
        return "connection_error", "network_error"

    return "unknown", "exception"


def _error_message(exc: Exception) -> str:
    message = str(exc).strip()
    if message:
        return message
    return exc.__class__.__name__


async def probe_item_health(
    *,
    item: ItemConfig,
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    default_timeout_sec: float,
) -> ItemHealthStatus:
    checked_url = str(item.url)
    timeout_sec = max(MIN_TIMEOUT_SEC, default_timeout_sec)
    degraded_latency_ms, down_latency_ms, degrade_on_http_4xx = _health_thresholds(item)

    if isinstance(item, LinkItemConfig) and item.healthcheck:
        checked_url = str(item.healthcheck.url)
        timeout_sec = max(MIN_TIMEOUT_SEC, item.healthcheck.timeout_ms / 1000)

    started_at = perf_counter()

    try:
        async with semaphore:
            response = await client.get(checked_url, timeout=timeout_sec)
        latency_ms = int((perf_counter() - started_at) * 1000)
        level, reason, error_kind, error = _classify_http_result(
            status_code=response.status_code,
            latency_ms=latency_ms,
            degraded_latency_ms=degraded_latency_ms,
            down_latency_ms=down_latency_ms,
            degrade_on_http_4xx=degrade_on_http_4xx,
        )
        return ItemHealthStatus(
            item_id=item.id,
            ok=level == "online",
            checked_url=checked_url,
            status_code=response.status_code,
            latency_ms=latency_ms,
            error=error,
            level=level,
            reason=reason,
            error_kind=error_kind,
        )
    except Exception as exc:
        latency_ms = int((perf_counter() - started_at) * 1000)
        error_kind, reason = _classify_exception(exc)
        return ItemHealthStatus(
            item_id=item.id,
            ok=False,
            checked_url=checked_url,
            status_code=None,
            latency_ms=latency_ms,
            error=_error_message(exc),
            level="down",
            reason=reason,
            error_kind=error_kind,
        )
