from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .constants import PORT_SERVICE_NAMES
from .identity import hostname_from_tls_services


def load_last_result(result_file: Path | None) -> dict[str, Any] | None:
    if result_file is None or not result_file.exists():
        return None

    try:
        data = json.loads(result_file.read_text(encoding="utf-8"))
    except Exception:
        return None

    if not isinstance(data, dict):
        return None

    hosts = data.get("hosts")
    if not isinstance(hosts, list):
        return data

    for host in hosts:
        if not isinstance(host, dict):
            continue

        open_ports = host.get("open_ports")
        if isinstance(open_ports, list):
            for entry in open_ports:
                if not isinstance(entry, dict):
                    continue
                if entry.get("service"):
                    continue
                port = entry.get("port")
                if isinstance(port, int):
                    entry["service"] = PORT_SERVICE_NAMES.get(port)

        if host.get("hostname"):
            continue

        ip = str(host.get("ip", "")).strip()
        services = host.get("http_services")
        if ip and isinstance(services, list):
            service_rows = [svc for svc in services if isinstance(svc, dict)]
            host["hostname"] = hostname_from_tls_services(ip, service_rows)

    return data


def save_result(result_file: Path | None, result: dict[str, Any]) -> None:
    if result_file is None:
        return
    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


__all__ = ["load_last_result", "save_result"]
