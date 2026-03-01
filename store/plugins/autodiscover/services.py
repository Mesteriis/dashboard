from __future__ import annotations

from typing import Any


def extract_services_from_scan_payload(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []

    result_payload = payload.get("result")
    if isinstance(result_payload, dict):
        scan_result = result_payload
    else:
        scan_result = payload

    hosts = scan_result.get("hosts")
    if not isinstance(hosts, list):
        return []

    services: list[dict[str, Any]] = []
    for host in hosts:
        if not isinstance(host, dict):
            continue
        ip = str(host.get("ip", "")).strip() or None
        hostname_raw = host.get("hostname")
        hostname = str(hostname_raw).strip() if isinstance(hostname_raw, str) else None
        host_mac_raw = host.get("host_mac") or host.get("mac_address")
        host_mac = str(host_mac_raw).strip() if isinstance(host_mac_raw, str) else None
        mac_vendor_raw = host.get("mac_vendor") or host.get("vendor")
        mac_vendor = str(mac_vendor_raw).strip() if isinstance(mac_vendor_raw, str) else None
        device_type_raw = host.get("device_type")
        device_type = str(device_type_raw).strip() if isinstance(device_type_raw, str) else None
        http_by_port: dict[int, dict[str, Any]] = {}
        http_services = host.get("http_services")
        if isinstance(http_services, list):
            for entry in http_services:
                if not isinstance(entry, dict):
                    continue
                port = entry.get("port")
                if isinstance(port, int):
                    http_by_port[port] = entry

        open_ports = host.get("open_ports")
        if not isinstance(open_ports, list):
            continue
        for entry in open_ports:
            if not isinstance(entry, dict):
                continue
            port = entry.get("port")
            if not isinstance(port, int):
                continue
            http_meta = http_by_port.get(port, {})
            services.append(
                {
                    "host_ip": ip,
                    "hostname": hostname,
                    "host_mac": host_mac,
                    "mac_vendor": mac_vendor,
                    "device_type": device_type,
                    "port": port,
                    "service": entry.get("service"),
                    "title": http_meta.get("title"),
                    "description": http_meta.get("description"),
                    "url": http_meta.get("url"),
                    "scheme": http_meta.get("scheme"),
                    "status": http_meta.get("status"),
                    "server": http_meta.get("server"),
                }
            )

    services.sort(key=lambda row: (str(row.get("host_ip") or ""), int(row.get("port") or 0)))
    return services


__all__ = ["extract_services_from_scan_payload"]
