from __future__ import annotations

from .schemas import ActionContract, EventContract

PLUGIN_NAME = "autodiscover"
PLUGIN_VERSION = "2.0.0"
PLUGIN_DESCRIPTION = (
    "Autodiscover LAN hosts, ports, HTTP metadata and network identity"
)

ACTION_SCAN = "autodiscover.scan"
CAPABILITY_SCAN = "exec.autodiscover.scan"

EVENT_SCAN_STARTED = "feature.autodiscover.scan.started"
EVENT_SCAN_PROGRESS = "feature.autodiscover.scan.progress"
EVENT_HOST_FOUND = "feature.autodiscover.host.found"
EVENT_SERVICE_FOUND = "feature.autodiscover.service.found"
EVENT_SCAN_COMPLETED = "feature.autodiscover.scan.completed"
EVENT_SCAN_FAILED = "feature.autodiscover.scan.failed"

ACTIONS: tuple[ActionContract, ...] = (
    ActionContract(
        type=ACTION_SCAN,
        capability=CAPABILITY_SCAN,
        description="Autodiscover LAN hosts, ports, HTTP metadata and network identity",
        dry_run_supported=True,
    ),
)

EVENTS: tuple[EventContract, ...] = (
    EventContract(type=EVENT_SCAN_STARTED, description="Autodiscover scan started"),
    EventContract(type=EVENT_SCAN_PROGRESS, description="Autodiscover scan progress"),
    EventContract(type=EVENT_HOST_FOUND, description="Autodiscover host discovered"),
    EventContract(type=EVENT_SERVICE_FOUND, description="Autodiscover service discovered"),
    EventContract(type=EVENT_SCAN_COMPLETED, description="Autodiscover scan completed"),
    EventContract(type=EVENT_SCAN_FAILED, description="Autodiscover scan failed"),
)


__all__ = [
    "ACTIONS",
    "ACTION_SCAN",
    "CAPABILITY_SCAN",
    "EVENTS",
    "EVENT_HOST_FOUND",
    "EVENT_SCAN_COMPLETED",
    "EVENT_SCAN_FAILED",
    "EVENT_SCAN_PROGRESS",
    "EVENT_SCAN_STARTED",
    "EVENT_SERVICE_FOUND",
    "PLUGIN_NAME",
    "PLUGIN_DESCRIPTION",
    "PLUGIN_VERSION",
]
