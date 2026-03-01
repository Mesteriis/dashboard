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
                    "port": port,
                    "service": entry.get("service"),
                    "title": http_meta.get("title"),
                    "description": http_meta.get("description"),
                    "url": http_meta.get("url"),
                    "status": http_meta.get("status"),
                    "server": http_meta.get("server"),
                }
            )

    services.sort(key=lambda row: (str(row.get("host_ip") or ""), int(row.get("port") or 0)))
    return services


__all__ = ["extract_services_from_scan_payload"]
