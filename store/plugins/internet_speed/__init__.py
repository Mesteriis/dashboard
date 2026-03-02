from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from time import perf_counter
from typing import Any

import httpx

from .manifest import (
    PLUGIN_CAPABILITIES,
    PLUGIN_DESCRIPTION,
    PLUGIN_LICENSE,
    PLUGIN_NAME,
    PLUGIN_TAGS,
    PLUGIN_VERSION,
)

PLUGIN_MANIFEST = {
    "name": PLUGIN_NAME,
    "version": PLUGIN_VERSION,
    "description": PLUGIN_DESCRIPTION,
    "license": PLUGIN_LICENSE,
    "tags": PLUGIN_TAGS,
    "capabilities": PLUGIN_CAPABILITIES,
}

_SEGMENT_PROBES: tuple[tuple[str, str, str, tuple[dict[str, Any], ...]], ...] = (
    (
        "eu",
        "Европа",
        "🇪🇺",
        (
            {
                "provider": "cloudflare",
                "latency_url": "https://speed.cloudflare.com/cdn-cgi/trace",
                "download_url": "https://speed.cloudflare.com/__down?bytes=900000",
                "download_bytes": 900_000,
                "upload_url": "https://speed.cloudflare.com/__up",
                "upload_bytes": 280_000,
            },
            {
                "provider": "cachefly",
                "latency_url": "https://cachefly.cachefly.net/1mb.test",
                "download_url": "https://cachefly.cachefly.net/1mb.test",
                "download_bytes": 1_048_576,
                "upload_url": "https://httpbin.org/post",
                "upload_bytes": 260_000,
            },
        ),
    ),
    (
        "us",
        "США",
        "🇺🇸",
        (
            {
                "provider": "cachefly",
                "latency_url": "https://cachefly.cachefly.net/1mb.test",
                "download_url": "https://cachefly.cachefly.net/1mb.test",
                "download_bytes": 1_048_576,
                "upload_url": "https://httpbin.org/post",
                "upload_bytes": 260_000,
            },
            {
                "provider": "cloudflare",
                "latency_url": "https://speed.cloudflare.com/cdn-cgi/trace",
                "download_url": "https://speed.cloudflare.com/__down?bytes=900000",
                "download_bytes": 900_000,
                "upload_url": "https://speed.cloudflare.com/__up",
                "upload_bytes": 280_000,
            },
        ),
    ),
)


def setup(**_kwargs: Any) -> None:
    return None


def teardown() -> None:
    return None


def _safe_round(value: float | None, digits: int = 2) -> float | None:
    if value is None:
        return None
    return round(value, digits)


def _format_mbps(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f} Mbps"


def _format_latency(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.0f} ms"


def _speed_display(download_mbps: float | None, upload_mbps: float | None, latency_ms: float | None) -> str:
    return (
        f"↓ {_format_mbps(download_mbps)} · "
        f"↑ {_format_mbps(upload_mbps)} · "
        f"{_format_latency(latency_ms)}"
    )


def _speed_compact(download_mbps: float | None, upload_mbps: float | None, latency_ms: float | None) -> str:
    down = "n/a" if download_mbps is None else f"{download_mbps:.1f}"
    up = "n/a" if upload_mbps is None else f"{upload_mbps:.1f}"
    ping = "n/a" if latency_ms is None else f"{latency_ms:.0f} ms"
    return f"↓ {down} · ↑ {up} Mbps · {ping}"


async def _measure_latency_ms(client: httpx.AsyncClient, url: str) -> float:
    started_at = perf_counter()
    response = await client.get(url, headers={"accept": "*/*"})
    response.raise_for_status()
    _ = response.content[:1]
    return (perf_counter() - started_at) * 1000


async def _measure_download_mbps(
    client: httpx.AsyncClient,
    url: str,
    expected_bytes: int,
) -> float:
    started_at = perf_counter()
    response = await client.get(url, headers={"accept": "*/*", "cache-control": "no-cache"})
    response.raise_for_status()
    payload = response.content
    elapsed_sec = max(perf_counter() - started_at, 0.001)
    measured_bytes = len(payload) or expected_bytes
    return (measured_bytes * 8) / (elapsed_sec * 1_000_000)


async def _measure_upload_mbps(
    client: httpx.AsyncClient,
    url: str,
    payload_bytes: int,
) -> float:
    body = b"x" * max(64_000, payload_bytes)
    started_at = perf_counter()
    response = await client.post(
        url,
        content=body,
        headers={
            "accept": "*/*",
            "content-type": "application/octet-stream",
            "cache-control": "no-cache",
        },
    )
    response.raise_for_status()
    _ = response.content[:1]
    elapsed_sec = max(perf_counter() - started_at, 0.001)
    return (len(body) * 8) / (elapsed_sec * 1_000_000)


async def _resolve_segment(
    client: httpx.AsyncClient,
    segment_id: str,
    segment: str,
    flag: str,
    providers: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    errors: list[str] = []
    for provider_config in providers:
        provider = str(provider_config.get("provider", "unknown"))
        try:
            latency_ms, download_mbps, upload_mbps = await asyncio.gather(
                _measure_latency_ms(client, str(provider_config["latency_url"])),
                _measure_download_mbps(
                    client,
                    str(provider_config["download_url"]),
                    int(provider_config.get("download_bytes") or 0),
                ),
                _measure_upload_mbps(
                    client,
                    str(provider_config["upload_url"]),
                    int(provider_config.get("upload_bytes") or 0),
                ),
            )
            latency_ms = _safe_round(latency_ms, 1)
            download_mbps = _safe_round(download_mbps, 2)
            upload_mbps = _safe_round(upload_mbps, 2)
            speed_display = _speed_display(download_mbps, upload_mbps, latency_ms)
            speed_compact = _speed_compact(download_mbps, upload_mbps, latency_ms)
            return {
                "segment_id": segment_id,
                "segment": segment,
                "segment_flag": flag,
                "segment_label": f"{flag} {segment}",
                "provider": provider,
                "provider_display": provider,
                "latency_ms": latency_ms,
                "download_mbps": download_mbps,
                "upload_mbps": upload_mbps,
                "speed_display": speed_display,
                "speed_compact": speed_compact,
                "ok": True,
                "error": None,
            }
        except Exception as exc:
            errors.append(f"{provider}: {exc}")

    return {
        "segment_id": segment_id,
        "segment": segment,
        "segment_flag": flag,
        "segment_label": f"{flag} {segment}",
        "provider": None,
        "provider_display": "n/a",
        "latency_ms": None,
        "download_mbps": None,
        "upload_mbps": None,
        "speed_display": _speed_display(None, None, None),
        "speed_compact": _speed_compact(None, None, None),
        "ok": False,
        "error": "; ".join(errors),
    }


async def get_services() -> dict[str, Any]:
    timeout = httpx.Timeout(8.0, connect=4.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        segment_results = await asyncio.gather(
            *[
                _resolve_segment(client, segment_id, segment, flag, providers)
                for segment_id, segment, flag, providers in _SEGMENT_PROBES
            ]
        )

    ok_segments = [entry for entry in segment_results if entry.get("ok")]
    primary_segment = ok_segments[0] if ok_segments else None

    download_values = [
        float(entry["download_mbps"])
        for entry in ok_segments
        if isinstance(entry.get("download_mbps"), (int, float))
    ]
    upload_values = [
        float(entry["upload_mbps"])
        for entry in ok_segments
        if isinstance(entry.get("upload_mbps"), (int, float))
    ]

    spread_pct = 0.0
    if len(download_values) >= 2:
        top = max(download_values)
        low = min(download_values)
        spread_pct = ((top - low) / top * 100.0) if top > 0 else 0.0
    variance_detected = spread_pct >= 25.0
    variance_badge = "⚠ Расхождение скорости по сегментам" if variance_detected else ""

    primary_download = (
        float(primary_segment["download_mbps"])
        if primary_segment and isinstance(primary_segment.get("download_mbps"), (int, float))
        else None
    )
    primary_upload = (
        float(primary_segment["upload_mbps"])
        if primary_segment and isinstance(primary_segment.get("upload_mbps"), (int, float))
        else None
    )
    primary_latency = (
        float(primary_segment["latency_ms"])
        if primary_segment and isinstance(primary_segment.get("latency_ms"), (int, float))
        else None
    )

    return {
        "updated_at": datetime.now(UTC).isoformat(),
        "segments": segment_results,
        "summary": {
            "segments_total": len(segment_results),
            "segments_ok": len(ok_segments),
            "segments_failed": len(segment_results) - len(ok_segments),
            "variance_detected": variance_detected,
            "variance_badge": variance_badge,
            "variance_label": "Скорости заметно различаются" if variance_detected else "Скорости близки",
            "download_spread_pct": _safe_round(spread_pct, 1),
            "primary_segment": primary_segment.get("segment") if primary_segment else None,
            "primary_segment_label": primary_segment.get("segment_label") if primary_segment else None,
            "primary_provider": primary_segment.get("provider") if primary_segment else None,
            "primary_download_mbps": _safe_round(primary_download, 2),
            "primary_upload_mbps": _safe_round(primary_upload, 2),
            "primary_latency_ms": _safe_round(primary_latency, 1),
            "primary_speed_display": _speed_display(primary_download, primary_upload, primary_latency),
            "primary_speed_compact": _speed_compact(primary_download, primary_upload, primary_latency),
            "download_values": [_safe_round(item, 2) for item in download_values],
            "upload_values": [_safe_round(item, 2) for item in upload_values],
        },
    }
