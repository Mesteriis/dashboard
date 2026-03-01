from __future__ import annotations

import asyncio
import contextlib
import html
import re
from itertools import starmap
from typing import Any, Literal

import httpx

from .constants import (
    DESCRIPTION_RE,
    DESCRIPTION_RE_ALT,
    HTTP_EXPECTED_PORTS,
    HTTPS_HINT_PORTS,
    NON_HTTP_PROTOCOL_PORTS,
    TITLE_RE,
)
from .schemas import ScanRequest


def extract_html_metadata(body: str) -> tuple[str | None, str | None]:
    if not body:
        return None, None

    title: str | None = None
    description: str | None = None

    title_match = TITLE_RE.search(body)
    if title_match:
        title = html.unescape(title_match.group(1))
        title = re.sub(r"\s+", " ", title).strip()[:240] or None

    description_match = DESCRIPTION_RE.search(body) or DESCRIPTION_RE_ALT.search(body)
    if description_match:
        description = html.unescape(description_match.group(1))
        description = re.sub(r"\s+", " ", description).strip()[:800] or None

    return title, description


def _http_probe_order(port: int) -> tuple[Literal["http", "https"], Literal["http", "https"]]:
    if port in HTTPS_HINT_PORTS:
        return ("https", "http")
    return ("http", "https")


async def _probe_http_port(client: httpx.AsyncClient, *, ip: str, port: int) -> dict[str, Any] | None:
    errors: list[str] = []
    probe_order = _http_probe_order(port)

    for scheme in probe_order:
        url = f"{scheme}://{ip}:{port}/"
        try:
            response = await client.get(url)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            errors.append(f"{scheme}: {exc.__class__.__name__}")
            continue

        body = ""
        content_type = (response.headers.get("content-type") or "").lower()
        if "text" in content_type or "json" in content_type or "xml" in content_type:
            with contextlib.suppress(Exception):
                body = response.text[:180_000]

        title, description = extract_html_metadata(body)
        return {
            "port": port,
            "scheme": scheme,
            "url": str(response.url),
            "status_code": response.status_code,
            "title": title,
            "description": description,
            "server": response.headers.get("server"),
            "error": None,
        }

    if not errors:
        return None
    if port not in HTTP_EXPECTED_PORTS:
        return None

    primary_scheme = probe_order[0]
    return {
        "port": port,
        "scheme": primary_scheme,
        "url": f"{primary_scheme}://{ip}:{port}/",
        "status_code": None,
        "title": None,
        "description": None,
        "server": None,
        "error": errors[0],
    }


async def probe_http_services(
    open_ports_map: dict[str, list[dict[str, Any]]],
    request: ScanRequest,
) -> dict[str, list[dict[str, Any]]]:
    targets: list[tuple[str, int]] = []
    for ip, ports in open_ports_map.items():
        for entry in ports:
            port = int(entry.get("port", 0))
            if port in NON_HTTP_PROTOCOL_PORTS:
                continue
            targets.append((ip, port))

    if not targets:
        return {}

    timeout = max(0.6, min(3.0, request.connect_timeout_sec * 3))
    semaphore = asyncio.Semaphore(max(16, min(128, request.max_parallel // 2)))
    target_batch_size = max(32, min(384, request.max_parallel * 2))

    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        verify=request.http_verify_tls,
        headers={
            "User-Agent": "oko-autodiscover/2.0",
            "Accept": "text/html,application/xhtml+xml,application/json,*/*;q=0.8",
        },
    ) as client:

        async def probe_target(ip: str, port: int) -> tuple[str, dict[str, Any] | None]:
            async with semaphore:
                return ip, await _probe_http_port(client, ip=ip, port=port)

        probed: list[tuple[str, dict[str, Any] | None]] = []
        for start in range(0, len(targets), target_batch_size):
            batch = targets[start : start + target_batch_size]
            probed.extend(await asyncio.gather(*list(starmap(probe_target, batch))))
            await asyncio.sleep(0)

    grouped: dict[str, list[dict[str, Any]]] = {}
    for ip, service in probed:
        if service is None:
            continue
        grouped.setdefault(ip, []).append(service)

    for services in grouped.values():
        services.sort(key=lambda item: int(item["port"]))

    return grouped


__all__ = ["_probe_http_port", "extract_html_metadata", "probe_http_services"]
