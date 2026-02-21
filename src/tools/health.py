from __future__ import annotations

import asyncio
from time import perf_counter

import httpx

from scheme.dashboard import ItemConfig, ItemHealthStatus, LinkItemConfig


async def probe_item_health(
    *,
    item: ItemConfig,
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    default_timeout_sec: float,
) -> ItemHealthStatus:
    checked_url = str(item.url)
    timeout_sec = max(0.2, default_timeout_sec)

    if isinstance(item, LinkItemConfig) and item.healthcheck:
        checked_url = str(item.healthcheck.url)
        timeout_sec = max(0.2, item.healthcheck.timeout_ms / 1000)

    started_at = perf_counter()

    try:
        async with semaphore:
            response = await client.get(checked_url, timeout=timeout_sec)
        latency_ms = int((perf_counter() - started_at) * 1000)
        is_ok = 200 <= response.status_code < 400
        return ItemHealthStatus(
            item_id=item.id,
            ok=is_ok,
            checked_url=checked_url,
            status_code=response.status_code,
            latency_ms=latency_ms,
            error=None if is_ok else f"HTTP {response.status_code}",
        )
    except Exception as exc:
        latency_ms = int((perf_counter() - started_at) * 1000)
        return ItemHealthStatus(
            item_id=item.id,
            ok=False,
            checked_url=checked_url,
            status_code=None,
            latency_ms=latency_ms,
            error=str(exc),
        )
