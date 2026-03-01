from __future__ import annotations

import ipaddress
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .constants import (
    DEFAULT_CONNECT_TIMEOUT_SEC,
    DEFAULT_MAX_HOSTS,
    DEFAULT_MAX_PARALLEL,
    DEFAULT_PORT_SCAN_MAX,
    DEFAULT_PORTS_RANGE,
    DEFAULT_RESULT_FILE,
)
from .schemas import ScanRequest


def _safe_int(value: object, *, default: int, minimum: int, maximum: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Expected integer value, got: {value}") from exc
    if parsed < minimum or parsed > maximum:
        raise ValueError(f"Integer value out of range: {parsed} (expected {minimum}..{maximum})")
    return parsed


def _safe_float(value: object, *, default: float, minimum: float, maximum: float) -> float:
    if value is None:
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Expected float value, got: {value}") from exc
    if parsed < minimum or parsed > maximum:
        raise ValueError(f"Float value out of range: {parsed} (expected {minimum}..{maximum})")
    return parsed


def _parse_ports(
    raw: object,
    *,
    default_start: int = DEFAULT_PORTS_RANGE[0],
    default_end: int = DEFAULT_PORTS_RANGE[1],
) -> tuple[int, ...]:
    start = max(1, min(DEFAULT_PORT_SCAN_MAX, int(default_start)))
    end = max(1, min(DEFAULT_PORT_SCAN_MAX, int(default_end)))
    if start > end:
        start, end = end, start
    default_ports = tuple(range(start, end + 1))

    if raw is None:
        return default_ports

    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes, bytearray)):
        raw_text = ",".join(str(item) for item in raw)
    else:
        raw_text = str(raw)

    ports: list[int] = []
    for token in raw_text.split(","):
        chunk = token.strip()
        if not chunk:
            continue
        if "-" in chunk:
            left, right = chunk.split("-", 1)
            try:
                start = int(left.strip())
                end = int(right.strip())
            except ValueError:
                continue
            if start > end:
                start, end = end, start
            start = max(1, start)
            end = min(DEFAULT_PORT_SCAN_MAX, end)
            ports.extend(range(start, end + 1))
            continue
        try:
            value = int(chunk)
        except ValueError:
            continue
        if 1 <= value <= DEFAULT_PORT_SCAN_MAX:
            ports.append(value)

    if not ports:
        return default_ports
    return tuple(sorted(set(ports)))


def _parse_port_bounds(start_raw: object, end_raw: object) -> tuple[int, int]:
    start = _safe_int(
        start_raw,
        default=DEFAULT_PORTS_RANGE[0],
        minimum=1,
        maximum=DEFAULT_PORT_SCAN_MAX,
    )
    end = _safe_int(
        end_raw,
        default=DEFAULT_PORTS_RANGE[1],
        minimum=1,
        maximum=DEFAULT_PORT_SCAN_MAX,
    )
    if start > end:
        start, end = end, start
    return start, end


def _parse_cidrs(raw: object) -> tuple[str, ...]:
    if raw is None:
        return ()

    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes, bytearray)):
        raw_text = ",".join(str(item) for item in raw)
    else:
        raw_text = str(raw)

    cidrs: list[str] = []
    for token in raw_text.split(","):
        chunk = token.strip()
        if not chunk:
            continue
        try:
            network = ipaddress.ip_network(chunk, strict=False)
        except ValueError:
            continue
        if isinstance(network, ipaddress.IPv4Network):
            cidrs.append(str(network))

    return tuple(dict.fromkeys(cidrs))


def _normalize_hosts(raw_hosts: object) -> tuple[str, ...]:
    if raw_hosts is None:
        return ()
    if not isinstance(raw_hosts, Sequence) or isinstance(raw_hosts, (str, bytes, bytearray)):
        raise ValueError("Field 'hosts' must be a list of IPv4/IPv6 addresses")

    normalized: list[str] = []
    for value in raw_hosts:
        host = str(value).strip()
        if not host:
            continue
        try:
            ipaddress.ip_address(host)
        except ValueError as exc:
            raise ValueError(f"Invalid host address: {host}") from exc
        normalized.append(host)

    return tuple(dict.fromkeys(normalized))


def normalize_request(payload: Mapping[str, Any]) -> ScanRequest:
    hosts = _normalize_hosts(payload.get("hosts"))
    cidrs = _parse_cidrs(payload.get("cidrs"))
    ports_from, ports_to = _parse_port_bounds(payload.get("ports_from"), payload.get("ports_to"))
    ports = _parse_ports(payload.get("ports"), default_start=ports_from, default_end=ports_to)
    if not ports:
        raise ValueError("Field 'ports' resolved to empty list")

    max_hosts = _safe_int(payload.get("max_hosts"), default=DEFAULT_MAX_HOSTS, minimum=1, maximum=16_384)
    max_parallel = _safe_int(payload.get("max_parallel"), default=DEFAULT_MAX_PARALLEL, minimum=8, maximum=2_048)
    connect_timeout_sec = _safe_float(
        payload.get("connect_timeout_sec"),
        default=DEFAULT_CONNECT_TIMEOUT_SEC,
        minimum=0.05,
        maximum=10.0,
    )

    result_file_raw = payload.get("result_file")
    if result_file_raw is None:
        result_file = DEFAULT_RESULT_FILE
    else:
        token = str(result_file_raw).strip()
        result_file = None if not token else Path(token).expanduser()

    config_snapshot = payload.get("config_snapshot")
    if config_snapshot is not None and not isinstance(config_snapshot, Mapping):
        raise ValueError("Field 'config_snapshot' must be an object")

    include_dashboard_items = bool(payload.get("include_dashboard_items", True))
    include_http_services = bool(payload.get("include_http_services", True))

    return ScanRequest(
        hosts=hosts,
        cidrs=cidrs,
        ports=ports,
        max_hosts=max_hosts,
        max_parallel=max_parallel,
        connect_timeout_sec=connect_timeout_sec,
        http_verify_tls=bool(payload.get("http_verify_tls", True)),
        resolve_hostnames=bool(payload.get("resolve_hostnames", True)),
        resolve_macs=bool(payload.get("resolve_macs", True)),
        include_http_services=include_http_services,
        include_dashboard_items=include_dashboard_items,
        result_file=result_file,
        config_snapshot=config_snapshot,
    )


def _build_request_payload(request: ScanRequest) -> dict[str, Any]:
    ports: list[int] | dict[str, int]
    if (
        len(request.ports) > 256
        and bool(request.ports)
        and request.ports == tuple(range(request.ports[0], request.ports[-1] + 1))
    ):
        ports = {"from": request.ports[0], "to": request.ports[-1], "count": len(request.ports)}
    else:
        ports = list(request.ports)

    return {
        "hosts": list(request.hosts),
        "cidrs": list(request.cidrs),
        "ports": ports,
        "ports_from": request.ports[0],
        "ports_to": request.ports[-1],
        "max_hosts": request.max_hosts,
        "max_parallel": request.max_parallel,
        "connect_timeout_sec": request.connect_timeout_sec,
        "http_verify_tls": request.http_verify_tls,
        "resolve_hostnames": request.resolve_hostnames,
        "resolve_macs": request.resolve_macs,
        "include_http_services": request.include_http_services,
        "include_dashboard_items": request.include_dashboard_items,
        "result_file": str(request.result_file) if request.result_file else None,
    }


__all__ = [
    "_build_request_payload",
    "_parse_cidrs",
    "_parse_ports",
    "normalize_request",
]
