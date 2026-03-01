from __future__ import annotations

import contextlib
import ipaddress
import re
import socket
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit

_HOSTNAME_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9._-]{1,62}")
_HOSTNAME_STOPWORDS = {
    "api",
    "console",
    "dashboard",
    "host",
    "http",
    "https",
    "server",
    "service",
    "ui",
    "web",
}


def _normalize_hostname_candidate(value: str, ip: str) -> str | None:
    candidate = value.strip().rstrip(".").lower()
    if not candidate:
        return None
    if candidate in _HOSTNAME_STOPWORDS:
        return None
    if candidate == ip:
        return None
    if " " in candidate:
        return None
    with contextlib.suppress(ValueError):
        ipaddress.ip_address(candidate)
        return None
    return candidate


def item_ip(item: Mapping[str, Any], resolve_cache: dict[str, str | None]) -> str | None:
    host = urlsplit(str(item.get("url", ""))).hostname
    if not host:
        return None

    with contextlib.suppress(ValueError):
        parsed_ip = ipaddress.ip_address(host)
        if isinstance(parsed_ip, ipaddress.IPv4Address) and parsed_ip.is_private:
            return str(parsed_ip)
        return None

    if host in resolve_cache:
        return resolve_cache[host]

    resolved_ip: str | None = None
    try:
        candidate = socket.gethostbyname(host)
        parsed_ip = ipaddress.ip_address(candidate)
        if isinstance(parsed_ip, ipaddress.IPv4Address) and parsed_ip.is_private:
            resolved_ip = str(parsed_ip)
    except OSError:
        resolved_ip = None

    resolve_cache[host] = resolved_ip
    return resolved_ip


def _iter_config_items(config_snapshot: Mapping[str, Any]) -> list[dict[str, Any]]:
    groups = config_snapshot.get("groups")
    if not isinstance(groups, list):
        return []

    items: list[dict[str, Any]] = []
    for group in groups:
        if not isinstance(group, Mapping):
            continue
        subgroups = group.get("subgroups")
        if not isinstance(subgroups, list):
            continue
        for subgroup in subgroups:
            if not isinstance(subgroup, Mapping):
                continue
            subgroup_items = subgroup.get("items")
            if not isinstance(subgroup_items, list):
                continue
            for item in subgroup_items:
                if isinstance(item, Mapping):
                    items.append(dict(item))
    return items


def dashboard_services_by_ip(config_snapshot: Mapping[str, Any] | None) -> dict[str, list[dict[str, Any]]]:
    if config_snapshot is None:
        return {}

    mapping: dict[str, list[dict[str, Any]]] = {}
    resolve_cache: dict[str, str | None] = {}

    for item in _iter_config_items(config_snapshot):
        ip = item_ip(item, resolve_cache)
        if ip is None:
            continue

        item_id = str(item.get("id", "")).strip()
        title = str(item.get("title", "")).strip()
        url = str(item.get("url", "")).strip()
        if not item_id or not title or not url:
            continue

        mapping.setdefault(ip, []).append(
            {
                "id": item_id,
                "title": title,
                "url": url,
            }
        )

    for entries in mapping.values():
        entries.sort(key=lambda entry: str(entry.get("title", "")).lower())

    return mapping


def hostname_from_dashboard_items(ip: str, dashboard_items: list[dict[str, Any]]) -> str | None:
    for item in dashboard_items:
        host = urlsplit(str(item.get("url", ""))).hostname
        if host:
            candidate = _normalize_hostname_candidate(host, ip)
            if candidate:
                return candidate

    for item in dashboard_items:
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        for token in _HOSTNAME_TOKEN_RE.findall(title):
            candidate = _normalize_hostname_candidate(token, ip)
            if candidate:
                return candidate
    return None


__all__ = ["dashboard_services_by_ip", "hostname_from_dashboard_items", "item_ip"]
