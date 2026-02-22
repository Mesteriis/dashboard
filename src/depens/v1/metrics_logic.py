"""Prometheus metrics collection for dashboard monitoring."""

from __future__ import annotations

from contextlib import suppress
from datetime import UTC, datetime

from prometheus_client import REGISTRY, Gauge, Info, generate_latest

import depens.v1.health_runtime as dashboard_module
from config.container import AppContainer

INFO_METRIC = Info(
    name="oko_dashboard",
    documentation="OKO Dashboard instance information",
)

HEALTH_SAMPLES_TOTAL = Gauge(
    name="oko_health_samples_total",
    documentation="Total number of health samples stored",
    labelnames=["item_id"],
)

HEALTH_STATUS = Gauge(
    name="oko_health_status",
    documentation="Current health status of services (1=online, 0.5=degraded, 0=down)",
    labelnames=["item_id", "group_id", "subgroup_id"],
)

HEALTH_LATENCY_MS = Gauge(
    name="oko_health_latency_ms",
    documentation="Last health check latency in milliseconds",
    labelnames=["item_id"],
)

HEALTH_LAST_CHECK = Gauge(
    name="oko_health_last_check_timestamp",
    documentation="Timestamp of the last health check",
    labelnames=["item_id"],
)

LAN_SCAN_LAST_SUCCESS = Gauge(
    name="oko_lan_scan_last_success_timestamp",
    documentation="Timestamp of the last successful LAN scan",
)

LAN_SCAN_HOSTS_DISCOVERED = Gauge(
    name="oko_lan_scan_hosts_discovered",
    documentation="Number of hosts discovered in the last LAN scan",
)

CONFIG_REVISION = Gauge(
    name="oko_config_revision",
    documentation="Current dashboard configuration revision",
)


def collect_metrics_payload(container: AppContainer) -> bytes:
    """Update metric gauges and return Prometheus text payload."""
    with suppress(Exception):
        INFO_METRIC.info(
            {
                "version": "0.1.0",
                "python_version": "3.14",
            }
        )

        snapshot = dashboard_module._HEALTH_RUNTIME.snapshot()
        if snapshot is not None:
            CONFIG_REVISION.set(snapshot.revision)
            config = snapshot.config

            for item_id, status in snapshot.statuses_by_id.items():
                group_id = ""
                subgroup_id = ""

                for group in config.groups:
                    for subgroup in group.subgroups:
                        if any(item.id == item_id for item in subgroup.items):
                            group_id = group.id
                            subgroup_id = subgroup.id
                            break
                    if group_id:
                        break

                status_value = 1.0 if status.level == "online" else (0.5 if status.level == "degraded" else 0.0)
                HEALTH_STATUS.labels(item_id=item_id, group_id=group_id, subgroup_id=subgroup_id).set(status_value)

                if status.latency_ms is not None:
                    HEALTH_LATENCY_MS.labels(item_id=item_id).set(status.latency_ms)

                HEALTH_LAST_CHECK.labels(item_id=item_id).set(datetime.now(UTC).timestamp())

        lan_state = container.lan_scan_service.state()
        if lan_state.last_finished_at:
            LAN_SCAN_LAST_SUCCESS.set(lan_state.last_finished_at.timestamp())
        if lan_state.result:
            LAN_SCAN_HOSTS_DISCOVERED.set(len(lan_state.result.hosts))

    return generate_latest(REGISTRY)


__all__ = [
    "collect_metrics_payload",
]
