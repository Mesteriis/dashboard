from __future__ import annotations

import contextlib
import ipaddress
import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PORT_SCAN_MAX = 65_535
SAFE_DEFAULT_SCAN_PORTS: tuple[int, ...] = ()

PORT_SERVICE_NAMES = {
    21: "ftp",
    22: "ssh",
    23: "telnet",
    25: "smtp",
    53: "dns",
    67: "dhcp-server",
    68: "dhcp-client",
    80: "http",
    81: "http-alt",
    88: "kerberos",
    110: "pop3",
    111: "rpcbind",
    123: "ntp",
    135: "rpc",
    137: "netbios-ns",
    138: "netbios-dgm",
    139: "netbios",
    143: "imap",
    161: "snmp",
    389: "ldap",
    443: "https",
    445: "smb",
    465: "smtps",
    500: "isakmp",
    514: "syslog",
    515: "lpd",
    587: "submission",
    631: "ipp",
    873: "rsync",
    993: "imaps",
    995: "pop3s",
    1080: "socks",
    1433: "mssql",
    1521: "oracle",
    1723: "pptp",
    1883: "mqtt",
    2049: "nfs",
    2375: "docker",
    2376: "docker-tls",
    25565: "minecraft",
    3000: "app-3000",
    3001: "app-3001",
    3002: "app-3002",
    3128: "proxy",
    3306: "mysql",
    3389: "rdp",
    5000: "app-5000",
    5001: "app-5001",
    5432: "postgres",
    5601: "kibana",
    5672: "amqp",
    5900: "vnc",
    5985: "winrm",
    5986: "winrm-tls",
    6379: "redis",
    6443: "k8s-api",
    7001: "weblogic",
    7002: "weblogic-ssl",
    7199: "cassandra-jmx",
    7443: "https-alt",
    7575: "homarr",
    7878: "radarr",
    8000: "app-8000",
    8006: "proxmox",
    8080: "http-alt",
    8081: "http-alt",
    8086: "influxdb",
    8096: "jellyfin",
    8123: "home-assistant",
    8191: "flaresolverr",
    8265: "tdarr",
    8266: "tdarr-node",
    8443: "https-alt",
    8686: "lidarr",
    8787: "readarr",
    8989: "sonarr",
    9000: "portainer",
    9042: "cassandra",
    9090: "prometheus",
    9091: "prometheus-pushgateway",
    9100: "node-exporter",
    9696: "prowlarr",
    11434: "ollama",
    13378: "audiobookshelf",
    19999: "netdata",
    6333: "qdrant",
    9200: "elasticsearch",
    9300: "elasticsearch-transport",
    9443: "https-alt",
    10000: "webmin",
}

SAFE_DEFAULT_SCAN_PORTS = tuple(sorted(PORT_SERVICE_NAMES))

NON_HTTP_PROTOCOL_PORTS = {
    21,
    22,
    23,
    25,
    53,
    67,
    68,
    88,
    110,
    111,
    123,
    135,
    137,
    138,
    139,
    143,
    161,
    389,
    445,
    465,
    500,
    514,
    515,
    587,
    631,
    873,
    993,
    995,
    1433,
    1521,
    1723,
    1883,
    2049,
    2375,
    2376,
    3306,
    3389,
    5432,
    5672,
    5900,
    5985,
    5986,
    6379,
    7199,
    9042,
}

HTTPS_HINT_PORTS = {443, 2376, 5986, 7002, 7443, 8443, 9443}
HTTP_EXPECTED_PORTS = {
    80,
    81,
    443,
    3000,
    3001,
    3002,
    3128,
    5000,
    5001,
    5601,
    7001,
    7002,
    7443,
    7575,
    7878,
    8000,
    8080,
    8081,
    8086,
    8096,
    8123,
    8191,
    8265,
    8266,
    8443,
    8686,
    8787,
    8989,
    9000,
    9090,
    9091,
    9696,
    11434,
    13378,
    19999,
    6333,
    9200,
    9300,
    9443,
    10000,
}


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_bool_any(names: tuple[str, ...], default: bool) -> bool:
    for name in names:
        raw = os.getenv(name)
        if raw is not None:
            return raw.strip().lower() in {"1", "true", "yes", "on"}
    return default


def _env_int(name: str, default: int, *, minimum: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, value)


def _env_float(name: str, default: float, *, minimum: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return max(minimum, value)


def _parse_ports(raw: str | None) -> tuple[int, ...]:
    if not raw:
        return SAFE_DEFAULT_SCAN_PORTS

    ports: list[int] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            left, right = token.split("-", 1)
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
            value = int(token)
        except ValueError:
            continue
        if 1 <= value <= DEFAULT_PORT_SCAN_MAX:
            ports.append(value)

    if not ports:
        return SAFE_DEFAULT_SCAN_PORTS
    return tuple(sorted(set(ports)))


def _parse_cidrs(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return ()

    cidrs: list[str] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        with contextlib.suppress(ValueError):
            network = ipaddress.ip_network(token, strict=False)
            if isinstance(network, ipaddress.IPv4Network):
                cidrs.append(str(network))

    return tuple(dict.fromkeys(cidrs))


@dataclass(frozen=True)
class LanScanSettings:
    enabled: bool
    run_on_startup: bool
    interval_sec: int
    connect_timeout_sec: float
    http_verify_tls: bool
    max_parallel: int
    max_hosts: int
    ports: tuple[int, ...]
    cidrs: tuple[str, ...]
    result_file: Path


def lan_scan_settings_from_env(base_dir: Path) -> LanScanSettings:
    result_file = Path(
        os.getenv("LAN_SCAN_RESULT_FILE", str(base_dir.parent / "data" / "lan_scan_result.json"))
    )
    return LanScanSettings(
        enabled=_env_bool_any(("LAN_SCAN_ENABLED", "DASHBOARD_ENABLE_LAN_SCAN"), False),
        run_on_startup=_env_bool("LAN_SCAN_RUN_ON_STARTUP", False),
        interval_sec=_env_int("LAN_SCAN_INTERVAL_SEC", 1020, minimum=30),
        connect_timeout_sec=_env_float("LAN_SCAN_CONNECT_TIMEOUT_SEC", 0.25, minimum=0.1),
        http_verify_tls=_env_bool("LAN_SCAN_HTTP_VERIFY_TLS", True),
        max_parallel=_env_int("LAN_SCAN_MAX_PARALLEL", 128, minimum=16),
        max_hosts=_env_int("LAN_SCAN_MAX_HOSTS", 512, minimum=32),
        ports=_parse_ports(os.getenv("LAN_SCAN_PORTS")),
        cidrs=_parse_cidrs(os.getenv("LAN_SCAN_CIDRS")),
        result_file=result_file,
    )


__all__ = [
    "HTTPS_HINT_PORTS",
    "HTTP_EXPECTED_PORTS",
    "NON_HTTP_PROTOCOL_PORTS",
    "PORT_SERVICE_NAMES",
    "SAFE_DEFAULT_SCAN_PORTS",
    "LanScanSettings",
    "lan_scan_settings_from_env",
]
