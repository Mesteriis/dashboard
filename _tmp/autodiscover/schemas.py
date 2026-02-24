from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ActionContract:
    type: str
    capability: str
    description: str
    dry_run_supported: bool = True


@dataclass(frozen=True)
class EventContract:
    type: str
    description: str


@dataclass(frozen=True)
class ScanRequest:
    hosts: tuple[str, ...]
    cidrs: tuple[str, ...]
    ports: tuple[int, ...]
    max_hosts: int
    max_parallel: int
    connect_timeout_sec: float
    http_verify_tls: bool
    resolve_hostnames: bool
    resolve_macs: bool
    include_http_services: bool
    include_dashboard_items: bool
    result_file: Path | None
    config_snapshot: Mapping[str, Any] | None


ProgressCallback = Callable[[str, dict[str, Any]], Awaitable[None] | None]


__all__ = [
    "ActionContract",
    "EventContract",
    "ProgressCallback",
    "ScanRequest",
]
