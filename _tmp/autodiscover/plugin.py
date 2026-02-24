from __future__ import annotations

import asyncio
import inspect
import ipaddress
from datetime import UTC, datetime
from time import perf_counter
from typing import Any

from .constants import IMPORTANT_EVENT_PORTS
from .http_probe import _probe_http_port, extract_html_metadata, probe_http_services
from .identity import (
    detect_device_type,
    hostname_from_tls_services,
    mac_vendor,
    normalize_mac,
    resolve_hostnames_with_services,
    resolve_mac_addresses,
    safe_reverse_dns,
)
from .manifest import (
    ACTION_SCAN,
    ACTIONS,
    CAPABILITY_SCAN,
    EVENT_HOST_FOUND,
    EVENT_SCAN_COMPLETED,
    EVENT_SCAN_FAILED,
    EVENT_SCAN_PROGRESS,
    EVENT_SCAN_STARTED,
    EVENT_SERVICE_FOUND,
    EVENTS,
    PLUGIN_NAME,
    PLUGIN_VERSION,
)
from .mapping import dashboard_services_by_ip, hostname_from_dashboard_items, item_ip
from .network import (
    _detect_cidrs_from_ifconfig,
    _detect_cidrs_from_ip_addr,
    _detect_cidrs_from_udp_probe,
    enumerate_hosts,
    resolve_networks,
    scan_open_ports,
)
from .parsing import _build_request_payload, _parse_cidrs, _parse_ports, normalize_request
from .schemas import ProgressCallback
from .storage import load_last_result, save_result


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _ip_sort_key(value: str) -> tuple[int, int]:
    address = ipaddress.ip_address(value)
    return (address.version, int(address))


async def _emit_progress(callback: ProgressCallback | None, event_type: str, payload: dict[str, Any]) -> None:
    if callback is None:
        return
    maybe_awaitable = callback(event_type, payload)
    if inspect.isawaitable(maybe_awaitable):
        await maybe_awaitable


def _is_important_host(host: dict[str, Any]) -> bool:
    dashboard_items = host.get("dashboard_items")
    if isinstance(dashboard_items, list) and dashboard_items:
        return True

    open_ports = host.get("open_ports")
    if not isinstance(open_ports, list):
        return False

    for entry in open_ports:
        if not isinstance(entry, dict):
            continue
        port = entry.get("port")
        if isinstance(port, int) and port in IMPORTANT_EVENT_PORTS:
            return True
    return False


def _merge_open_ports(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_port: dict[int, dict[str, Any]] = {}
    for group in groups:
        for entry in group:
            if not isinstance(entry, dict):
                continue
            port = entry.get("port")
            if not isinstance(port, int):
                continue
            service = entry.get("service")
            existing = by_port.get(port)
            if existing is None:
                by_port[port] = {
                    "port": port,
                    "service": service if isinstance(service, str) and service else None,
                }
                continue
            if existing.get("service") is None and isinstance(service, str) and service:
                existing["service"] = service

    return [by_port[port] for port in sorted(by_port)]


def detect_default_cidrs() -> tuple[str, ...]:
    detected: list[str] = []
    for cidrs in (
        _detect_cidrs_from_ip_addr(),
        _detect_cidrs_from_ifconfig(),
        _detect_cidrs_from_udp_probe(),
    ):
        for cidr in cidrs:
            if cidr not in detected:
                detected.append(cidr)
    if detected:
        return tuple(detected)
    return ("192.168.1.0/24",)


async def execute_scan(
    *,
    payload: dict[str, Any] | None = None,
    dry_run: bool = False,
    progress_callback: ProgressCallback | None = None,
) -> dict[str, Any]:
    request = normalize_request(payload or {})
    started_at = perf_counter()

    configured_cidrs = request.cidrs
    if not configured_cidrs and not request.hosts:
        configured_cidrs = detect_default_cidrs()

    if not configured_cidrs and request.hosts:
        networks: list[ipaddress.IPv4Network] = []
    else:
        networks = resolve_networks(configured_cidrs)

    scanned_cidrs = [str(network) for network in networks]
    enumerated_hosts = enumerate_hosts(networks, max_hosts=request.max_hosts)
    merged_hosts = tuple(dict.fromkeys((*request.hosts, *tuple(enumerated_hosts))))
    host_ips = list(merged_hosts[: request.max_hosts])

    if request.include_dashboard_items:
        full_dashboard_map = dashboard_services_by_ip(request.config_snapshot)
        if host_ips:
            host_ip_set = set(host_ips)
            dashboard_map = {ip: entries for ip, entries in full_dashboard_map.items() if ip in host_ip_set}
        else:
            dashboard_map = full_dashboard_map
    else:
        dashboard_map = {}

    discovered_ips_for_dry_run = sorted(
        set(host_ips) | set(dashboard_map.keys()),
        key=_ip_sort_key,
    )

    if dry_run:
        duration_ms = max(0, int((perf_counter() - started_at) * 1000))
        return {
            "plugin": PLUGIN_NAME,
            "version": PLUGIN_VERSION,
            "action": ACTION_SCAN,
            "dry_run": True,
            "request": _build_request_payload(request),
            "summary": {
                "targets_total": len(host_ips),
                "targets_scanned": 0,
                "discovered_hosts": len(discovered_ips_for_dry_run),
                "hosts_with_open_ports": 0,
                "scanned_ports": len(host_ips) * len(request.ports),
                "duration_ms": duration_ms,
            },
            "result": {
                "generated_at": _utc_now().isoformat(),
                "duration_ms": duration_ms,
                "scanned_hosts": len(host_ips),
                "scanned_ports": len(host_ips) * len(request.ports),
                "scanned_cidrs": scanned_cidrs,
                "hosts": [],
                "source_file": str(request.result_file) if request.result_file else None,
            },
            "hosts": [],
        }

    previous_result = load_last_result(request.result_file)
    previous_host_ips = {
        str(host.get("ip"))
        for host in (previous_result.get("hosts", []) if isinstance(previous_result, dict) else [])
        if isinstance(host, dict) and host.get("ip")
    }

    progress_hosts: dict[str, dict[str, Any]] = {}
    scanned_hosts_done = 0
    services_found_total = 0

    async def on_service_found(ip: str, service_row: dict[str, Any]) -> None:
        nonlocal services_found_total
        services_found_total += 1
        mapped_items = dashboard_map.get(ip, [])
        existing = progress_hosts.get(ip, {})
        merged_open_ports = _merge_open_ports(existing.get("open_ports", []), [service_row])
        host = {
            "ip": ip,
            "hostname": existing.get("hostname"),
            "mac_address": existing.get("mac_address"),
            "mac_vendor": existing.get("mac_vendor"),
            "device_type": detect_device_type(
                hostname=existing.get("hostname"),
                vendor=existing.get("mac_vendor"),
                open_ports=merged_open_ports,
                dashboard_items=mapped_items,
            ),
            "open_ports": merged_open_ports,
            "http_services": existing.get("http_services", []),
            "dashboard_items": mapped_items,
        }
        progress_hosts[ip] = host
        await _emit_progress(
            progress_callback,
            "service_found",
            {
                "ip": ip,
                "service": service_row,
                "progress": {
                    "scanned_hosts": scanned_hosts_done,
                    "total_hosts": len(host_ips),
                    "discovered_hosts": len(progress_hosts),
                    "discovered_services": services_found_total,
                },
            },
        )

    async def on_host_scanned(ip: str, open_ports: list[dict[str, Any]]) -> None:
        nonlocal scanned_hosts_done
        scanned_hosts_done += 1
        mapped_items = dashboard_map.get(ip, [])

        if open_ports or mapped_items:
            existing = progress_hosts.get(ip, {})
            merged_open_ports = _merge_open_ports(existing.get("open_ports", []), open_ports)
            host = {
                "ip": ip,
                "hostname": existing.get("hostname"),
                "mac_address": existing.get("mac_address"),
                "mac_vendor": existing.get("mac_vendor"),
                "device_type": detect_device_type(
                    hostname=existing.get("hostname"),
                    vendor=existing.get("mac_vendor"),
                    open_ports=merged_open_ports,
                    dashboard_items=mapped_items,
                ),
                "open_ports": merged_open_ports,
                "http_services": existing.get("http_services", []),
                "dashboard_items": mapped_items,
            }
            progress_hosts[ip] = host

            is_new = ip not in previous_host_ips
            important = _is_important_host(host)
            await _emit_progress(
                progress_callback,
                "host_found",
                {
                    "host": host,
                    "is_new": is_new,
                    "important": important,
                    "progress": {
                        "scanned_hosts": scanned_hosts_done,
                        "total_hosts": len(host_ips),
                        "discovered_hosts": len(progress_hosts),
                        "discovered_services": services_found_total,
                    },
                },
            )

        if scanned_hosts_done % 8 == 0 or scanned_hosts_done == len(host_ips):
            await _emit_progress(
                progress_callback,
                "scan_progress",
                {
                    "scanned_hosts": scanned_hosts_done,
                    "total_hosts": len(host_ips),
                    "discovered_hosts": len(progress_hosts),
                    "discovered_services": services_found_total,
                },
            )

    open_ports_map = await scan_open_ports(
        host_ips,
        request,
        on_host_scanned=on_host_scanned,
        on_service_found=on_service_found,
    )

    if request.include_http_services:
        http_services_map = await probe_http_services(open_ports_map, request)
    else:
        http_services_map = {}

    discovered_ips = sorted(
        set(open_ports_map.keys()) | set(dashboard_map.keys()),
        key=_ip_sort_key,
    )

    if request.resolve_hostnames:
        hostnames = await resolve_hostnames_with_services(discovered_ips, http_services_map)
    else:
        hostnames = {}

    macs = await asyncio.to_thread(resolve_mac_addresses, discovered_ips) if request.resolve_macs else {}

    hosts: list[dict[str, Any]] = []
    for ip in discovered_ips:
        open_ports = open_ports_map.get(ip, [])
        mapped_items = dashboard_map.get(ip, [])
        hostname = hostnames.get(ip) or hostname_from_dashboard_items(ip, mapped_items)
        mac_address = macs.get(ip)
        vendor = mac_vendor(mac_address)

        hosts.append(
            {
                "ip": ip,
                "hostname": hostname,
                "mac_address": mac_address,
                "mac_vendor": vendor,
                "device_type": detect_device_type(
                    hostname=hostname,
                    vendor=vendor,
                    open_ports=open_ports,
                    dashboard_items=mapped_items,
                ),
                "open_ports": open_ports,
                "http_services": http_services_map.get(ip, []),
                "dashboard_items": mapped_items,
            }
        )

    duration_ms = max(0, int((perf_counter() - started_at) * 1000))
    hosts_with_open_ports = sum(1 for host in hosts if host.get("open_ports"))

    result_payload = {
        "generated_at": _utc_now().isoformat(),
        "duration_ms": duration_ms,
        "scanned_hosts": len(host_ips),
        "scanned_ports": len(host_ips) * len(request.ports),
        "scanned_cidrs": scanned_cidrs,
        "hosts": hosts,
        "source_file": str(request.result_file) if request.result_file else None,
    }
    save_result(request.result_file, result_payload)

    return {
        "plugin": PLUGIN_NAME,
        "version": PLUGIN_VERSION,
        "action": ACTION_SCAN,
        "dry_run": False,
        "request": _build_request_payload(request),
        "summary": {
            "targets_total": len(host_ips),
            "targets_scanned": len(host_ips),
            "discovered_hosts": len(hosts),
            "hosts_with_open_ports": hosts_with_open_ports,
            "scanned_ports": len(host_ips) * len(request.ports),
            "duration_ms": duration_ms,
        },
        "result": result_payload,
        "hosts": hosts,
    }


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
    "PLUGIN_VERSION",
    "_detect_cidrs_from_ifconfig",
    "_detect_cidrs_from_ip_addr",
    "_detect_cidrs_from_udp_probe",
    "_parse_cidrs",
    "_parse_ports",
    "_probe_http_port",
    "dashboard_services_by_ip",
    "detect_default_cidrs",
    "detect_device_type",
    "enumerate_hosts",
    "execute_scan",
    "extract_html_metadata",
    "hostname_from_dashboard_items",
    "hostname_from_tls_services",
    "item_ip",
    "load_last_result",
    "mac_vendor",
    "normalize_mac",
    "probe_http_services",
    "resolve_hostnames_with_services",
    "resolve_mac_addresses",
    "resolve_networks",
    "safe_reverse_dns",
    "save_result",
    "scan_open_ports",
]
