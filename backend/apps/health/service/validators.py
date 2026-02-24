from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse

from apps.health.model.contracts import HealthCheckType
from core.contracts.errors import ApiError

_HOSTNAME_RE = re.compile(r"^[A-Za-z0-9.-]+$")


def clamp_interval_sec(value: int) -> int:
    return max(1, min(3600, int(value)))


def clamp_timeout_ms(value: int) -> int:
    return max(100, min(120_000, int(value)))


def clamp_latency_threshold_ms(value: int) -> int:
    return max(1, min(120_000, int(value)))


def validate_target(*, check_type: HealthCheckType, target: str) -> str:
    normalized_target = str(target or "").strip()
    if not normalized_target:
        raise ApiError(status_code=422, code="health_target_invalid", message="Target is required")

    if check_type == "http":
        return _validate_http_target(normalized_target)
    if check_type == "tcp":
        return _validate_tcp_target(normalized_target)
    if check_type == "icmp":
        return _validate_icmp_target(normalized_target)
    raise ApiError(status_code=422, code="health_check_type_invalid", message=f"Unsupported check_type: {check_type}")


def parse_tcp_target(target: str) -> tuple[str, int]:
    normalized = target.strip()
    if normalized.startswith("[") and "]" in normalized:
        closing = normalized.index("]")
        host = normalized[1:closing]
        suffix = normalized[closing + 1 :]
        if not suffix.startswith(":"):
            raise ApiError(status_code=422, code="health_target_invalid", message="TCP target must be host:port")
        port = suffix[1:]
    else:
        if ":" not in normalized:
            raise ApiError(status_code=422, code="health_target_invalid", message="TCP target must be host:port")
        host, port = normalized.rsplit(":", 1)

    host = host.strip()
    if not host:
        raise ApiError(status_code=422, code="health_target_invalid", message="TCP host is required")
    try:
        port_num = int(port)
    except ValueError as exc:
        raise ApiError(status_code=422, code="health_target_invalid", message="TCP port must be an integer") from exc
    if port_num < 1 or port_num > 65535:
        raise ApiError(status_code=422, code="health_target_invalid", message="TCP port must be in range 1..65535")
    return host, port_num


def _validate_http_target(target: str) -> str:
    parsed = urlparse(target)
    if parsed.scheme not in {"http", "https"}:
        raise ApiError(
            status_code=422,
            code="health_target_invalid",
            message="HTTP target scheme must be http or https",
        )
    if not parsed.netloc:
        raise ApiError(status_code=422, code="health_target_invalid", message="HTTP target host is required")
    return target


def _validate_tcp_target(target: str) -> str:
    _ = parse_tcp_target(target)
    return target


def _validate_icmp_target(target: str) -> str:
    if any(char.isspace() for char in target):
        raise ApiError(
            status_code=422,
            code="health_target_invalid",
            message="ICMP target must not contain whitespace",
        )
    try:
        _ = ipaddress.ip_address(target)
        return target
    except ValueError:
        pass

    if not _HOSTNAME_RE.match(target):
        raise ApiError(
            status_code=422,
            code="health_target_invalid",
            message="ICMP target must be a hostname or IP address",
        )
    return target


__all__ = [
    "clamp_interval_sec",
    "clamp_latency_threshold_ms",
    "clamp_timeout_ms",
    "parse_tcp_target",
    "validate_target",
]
