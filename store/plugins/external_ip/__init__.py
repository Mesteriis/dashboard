from __future__ import annotations

import asyncio
import json
import re
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

_SEGMENT_SOURCES: tuple[tuple[str, str, tuple[tuple[str, str], ...]], ...] = (
    (
        "rf",
        "Россия",
        (
            ("myip", "https://api.myip.com"),
            ("seeip", "https://api.seeip.org/jsonip"),
            ("ifconfig.co", "https://ifconfig.co/json"),
            ("ident.me", "https://ident.me"),
        ),
    ),
    (
        "eu",
        "Европа",
        (
            ("ifconfig.co", "https://ifconfig.co/json"),
            ("ident.me", "https://ident.me"),
            ("ipify", "https://api64.ipify.org?format=json"),
        ),
    ),
    (
        "us",
        "США",
        (
            ("ipify", "https://api.ipify.org?format=json"),
            ("ifconfig.me", "https://ifconfig.me/all.json"),
            ("aws-checkip", "https://checkip.amazonaws.com"),
        ),
    ),
    (
        "apac",
        "APAC",
        (
            ("ipify", "https://api64.ipify.org?format=json"),
            ("seeip", "https://api.seeip.org/jsonip"),
            ("ident.me", "https://ident.me"),
        ),
    ),
    (
        "mea",
        "MEA",
        (
            ("seeip", "https://api.seeip.org/jsonip"),
            ("ifconfig.co", "https://ifconfig.co/json"),
            ("icanhazip", "https://icanhazip.com"),
        ),
    ),
    (
        "latam",
        "LATAM",
        (
            ("ifconfig.me", "https://ifconfig.me/ip"),
            ("ipinfo", "https://ipinfo.io/ip"),
            ("myip", "https://api.myip.com"),
        ),
    ),
)

_SEGMENT_FLAGS: dict[str, str] = {
    "rf": "🇷🇺",
    "eu": "🇪🇺",
    "us": "🇺🇸",
    "apac": "🌏",
    "mea": "🌍",
    "latam": "🌎",
}

_IPV4_RE = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"
)
_IPV6_RE = re.compile(
    r"\b(?:[A-Fa-f0-9]{1,4}:){2,7}[A-Fa-f0-9]{1,4}\b"
)


def setup(**_kwargs: Any) -> None:
    return None


def teardown() -> None:
    return None


def _extract_ip(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    for key in ("ip", "query", "address", "ip_addr", "ipAddress", "IP"):
        value = str(payload.get(key, "")).strip()
        if value:
            return value
    return ""


def _extract_ip_from_text(payload: str) -> str:
    token = str(payload or "").strip()
    if not token:
        return ""
    if token.startswith("{") or token.startswith("["):
        try:
            decoded = json.loads(token)
            parsed = _extract_ip(decoded)
            if parsed:
                return parsed
        except Exception:
            pass
    ipv4 = _IPV4_RE.search(token)
    if ipv4:
        return ipv4.group(0)
    ipv6 = _IPV6_RE.search(token)
    if ipv6:
        return ipv6.group(0)
    if "\n" in token:
        token = token.splitlines()[0].strip()
    return token


async def _resolve_segment(
    client: httpx.AsyncClient,
    segment_id: str,
    segment: str,
    sources: tuple[tuple[str, str], ...],
) -> dict[str, Any]:
    flag = _SEGMENT_FLAGS.get(segment_id, "🏳️")
    errors: list[str] = []
    for provider, url in sources:
        started_at = perf_counter()
        try:
            response = await client.get(
                url,
                headers={
                    "accept": "application/json",
                    "user-agent": "oko-external-ip-plugin/1.1",
                },
            )
            response.raise_for_status()
            content_type = str(response.headers.get("content-type", "")).lower()
            if "application/json" in content_type:
                payload: Any = response.json()
                ip = _extract_ip(payload)
            else:
                payload = response.text
                ip = _extract_ip_from_text(payload)
            if not ip:
                errors.append(f"{provider}: ip is missing")
                continue
            latency_ms = int((perf_counter() - started_at) * 1000)
            return {
                "segment_id": segment_id,
                "segment": segment,
                "segment_flag": flag,
                "segment_label": f"{flag} {segment}",
                "ok": True,
                "ip": ip,
                "ip_display": ip,
                "ip_display_compact": f"{flag} {ip}",
                "provider": provider,
                "provider_display": provider,
                "source_url": url,
                "latency_ms": latency_ms,
                "error": None,
            }
        except Exception as exc:
            errors.append(f"{provider}: {exc}")

    return {
        "segment_id": segment_id,
        "segment": segment,
        "segment_flag": flag,
        "segment_label": f"{flag} {segment}",
        "ok": False,
        "ip": None,
        "ip_display": "unavailable",
        "ip_display_compact": f"{flag} unavailable",
        "provider": None,
        "provider_display": "n/a",
        "source_url": None,
        "latency_ms": None,
        "error": "; ".join(errors),
    }


async def get_services() -> dict[str, Any]:
    timeout = httpx.Timeout(5.5, connect=3.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        segment_results = await asyncio.gather(
            *[
                _resolve_segment(client, segment_id, segment, sources)
                for segment_id, segment, sources in _SEGMENT_SOURCES
            ]
        )

    ok_segments = [entry for entry in segment_results if entry.get("ok")]
    ok_ips = [str(entry.get("ip")) for entry in ok_segments if entry.get("ip")]
    unique_ips = sorted(set(ok_ips))
    primary_segment = next(
        (entry for entry in ok_segments if entry.get("segment_id") == "rf"),
        ok_segments[0] if ok_segments else None,
    )
    primary_ip = str(primary_segment.get("ip")) if primary_segment else None
    primary_provider = str(primary_segment.get("provider")) if primary_segment else None
    total = len(segment_results)
    ok_total = len(ok_segments)
    failed_total = total - ok_total
    variance = len(unique_ips) > 1
    variance_badge = "⚠ Расхождение egress IP" if variance else ""
    variance_label = "Разные egress IP" if variance else "Единый egress IP"
    primary_segment_label = (
        str(primary_segment.get("segment_label") or "")
        if primary_segment
        else None
    )

    return {
        "ip": primary_ip,
        "provider": primary_provider,
        "updated_at": datetime.now(UTC).isoformat(),
        "segments": segment_results,
        "summary": {
            "segments_total": total,
            "segments_ok": ok_total,
            "segments_failed": failed_total,
            "unique_ips": unique_ips,
            "variance_detected": variance,
            "variance_label": variance_label,
            "variance_badge": variance_badge,
            "primary_segment": primary_segment.get("segment") if primary_segment else None,
            "primary_segment_label": primary_segment_label,
            "primary_ip": primary_ip,
        },
    }
