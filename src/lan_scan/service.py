from __future__ import annotations

import asyncio
import contextlib
import html
import ipaddress
import json
import os
import re
import socket
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import perf_counter
from urllib.parse import urlsplit

import httpx

from src.dashboard_config.models import (
    LanHttpService,
    LanScanHost,
    LanScanMappedService,
    LanScanPort,
    LanScanResult,
    LanScanStateResponse,
    ItemConfig,
)
from src.dashboard_config.service import DashboardConfigService, DashboardConfigValidationError

DEFAULT_PORT_SCAN_MAX = 20_000
DEFAULT_SCAN_PORTS: tuple[int, ...] = tuple(range(1, DEFAULT_PORT_SCAN_MAX + 1))

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
    8000: "app-8000",
    8006: "proxmox",
    8080: "http-alt",
    8081: "http-alt",
    8086: "influxdb",
    8096: "jellyfin",
    8123: "home-assistant",
    8443: "https-alt",
    9000: "portainer",
    9042: "cassandra",
    9090: "prometheus",
    9091: "prometheus-pushgateway",
    9100: "node-exporter",
    9200: "elasticsearch",
    9300: "elasticsearch-transport",
    9443: "https-alt",
    10000: "webmin",
}

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
    8000,
    8080,
    8081,
    8086,
    8096,
    8123,
    8443,
    9000,
    9090,
    9091,
    9200,
    9300,
    9443,
    10000,
}

TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
DESCRIPTION_RE = re.compile(
    r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
    re.IGNORECASE | re.DOTALL,
)
DESCRIPTION_RE_ALT = re.compile(
    r'<meta[^>]+content=["\'](.*?)["\'][^>]+name=["\']description["\']',
    re.IGNORECASE | re.DOTALL,
)

MAC_OUI_VENDORS = {
    "000C29": "VMware",
    "000569": "VMware",
    "005056": "VMware",
    "0003FF": "Microsoft Hyper-V",
    "00155D": "Microsoft Hyper-V",
    "080027": "Oracle VirtualBox",
    "525400": "QEMU/KVM",
    "0242AC": "Docker",
    "B827EB": "Raspberry Pi Foundation",
    "DCA632": "Raspberry Pi Trading",
    "E45F01": "Raspberry Pi Trading",
    "F4F26D": "Ubiquiti",
    "24A43C": "Ubiquiti",
    "FCECDA": "Ubiquiti",
    "D850E6": "TP-Link",
    "AC84C6": "TP-Link",
    "E894F6": "TP-Link",
    "8C3B4A": "MikroTik",
    "4C5E0C": "MikroTik",
    "FC3497": "Asus",
    "F07959": "Asus",
    "F8FFCF": "Apple",
    "3C22FB": "Apple",
    "A4C361": "Apple",
    "D8BB2C": "Apple",
    "3CD92B": "Hewlett Packard",
    "0025B3": "Dell",
    "F8B156": "Dell",
    "F4CE46": "Intel",
    "A44CC8": "Intel",
    "001A8C": "Cisco",
    "58D56E": "Huawei",
    "94D9B3": "Xiaomi",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


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
        return DEFAULT_SCAN_PORTS

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
            end = min(65_535, end)
            ports.extend(range(start, end + 1))
            continue

        try:
            value = int(token)
        except ValueError:
            continue
        if 1 <= value <= 65535:
            ports.append(value)

    if not ports:
        return DEFAULT_SCAN_PORTS
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


def _detect_default_cidrs() -> tuple[str, ...]:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            local_ip = sock.getsockname()[0]
            network = ipaddress.ip_network(f"{local_ip}/24", strict=False)
            return (str(network),)
    except OSError:
        return ("192.168.1.0/24",)


@dataclass(frozen=True)
class LanScanSettings:
    enabled: bool
    run_on_startup: bool
    interval_sec: int
    connect_timeout_sec: float
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
        enabled=_env_bool("LAN_SCAN_ENABLED", True),
        run_on_startup=_env_bool("LAN_SCAN_RUN_ON_STARTUP", True),
        interval_sec=_env_int("LAN_SCAN_INTERVAL_SEC", 1020, minimum=30),
        connect_timeout_sec=_env_float("LAN_SCAN_CONNECT_TIMEOUT_SEC", 0.25, minimum=0.1),
        max_parallel=_env_int("LAN_SCAN_MAX_PARALLEL", 384, minimum=16),
        max_hosts=_env_int("LAN_SCAN_MAX_HOSTS", 1024, minimum=32),
        ports=_parse_ports(os.getenv("LAN_SCAN_PORTS")),
        cidrs=_parse_cidrs(os.getenv("LAN_SCAN_CIDRS")),
        result_file=result_file,
    )


class LanScanService:
    def __init__(self, *, config_service: DashboardConfigService, settings: LanScanSettings):
        self._config_service = config_service
        self._settings = settings

        self._running = False
        self._last_started_at: datetime | None = None
        self._last_finished_at: datetime | None = None
        self._next_run_at: datetime | None = None
        self._last_error: str | None = None
        self._last_result: LanScanResult | None = self._load_last_result()

        self._periodic_task: asyncio.Task | None = None
        self._run_task: asyncio.Task | None = None
        self._pending_trigger = False

    async def start(self) -> None:
        if not self._settings.enabled:
            return
        if self._periodic_task and not self._periodic_task.done():
            return

        self._periodic_task = asyncio.create_task(self._periodic_runner(), name="lan-scan-periodic")
        if self._settings.run_on_startup:
            await self.trigger_scan()

    async def stop(self) -> None:
        if self._periodic_task:
            self._periodic_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._periodic_task
            self._periodic_task = None

        if self._run_task and not self._run_task.done():
            self._run_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._run_task
        self._run_task = None
        self._pending_trigger = False
        self._next_run_at = None

    async def trigger_scan(self) -> bool:
        if not self._settings.enabled:
            return False
        if self._run_task and not self._run_task.done():
            self._pending_trigger = True
            return False
        self._run_task = asyncio.create_task(self._run_scan(), name="lan-scan-run")
        return True

    def state(self) -> LanScanStateResponse:
        return LanScanStateResponse(
            enabled=self._settings.enabled,
            scheduler="asyncio",
            interval_sec=self._settings.interval_sec,
            running=self._running,
            queued=self._pending_trigger,
            last_started_at=self._last_started_at,
            last_finished_at=self._last_finished_at,
            next_run_at=self._next_run_at,
            last_error=self._last_error,
            result=self._last_result,
        )

    async def _periodic_runner(self) -> None:
        interval = max(30, self._settings.interval_sec)
        next_tick = _utc_now() + timedelta(seconds=interval)
        while True:
            self._next_run_at = next_tick
            sleep_for = max((next_tick - _utc_now()).total_seconds(), 0.2)
            await asyncio.sleep(sleep_for)
            await self.trigger_scan()
            next_tick = _utc_now() + timedelta(seconds=interval)

    async def _run_scan(self) -> None:
        started = _utc_now()
        started_at = perf_counter()
        self._running = True
        self._last_started_at = started
        self._last_error = None

        try:
            networks = self._resolve_networks()
            host_ips = self._enumerate_hosts(networks)

            open_ports_map = await self._scan_open_ports(host_ips)
            http_services_map = await self._probe_http_services(open_ports_map)
            dashboard_map = await asyncio.to_thread(self._dashboard_services_by_ip)

            discovered_ips = sorted(
                set(open_ports_map.keys()) | set(dashboard_map.keys()),
                key=lambda raw: ipaddress.ip_address(raw),
            )
            hostnames = await self._resolve_hostnames(discovered_ips)
            macs = await asyncio.to_thread(self._resolve_mac_addresses, discovered_ips)

            hosts: list[LanScanHost] = []
            for ip in discovered_ips:
                open_ports = open_ports_map.get(ip, [])
                mapped_items = dashboard_map.get(ip, [])
                mac_address = macs.get(ip)
                mac_vendor = self._mac_vendor(mac_address)
                hosts.append(
                    LanScanHost(
                        ip=ip,
                        hostname=hostnames.get(ip),
                        mac_address=mac_address,
                        mac_vendor=mac_vendor,
                        device_type=self._detect_device_type(
                            hostname=hostnames.get(ip),
                            vendor=mac_vendor,
                            open_ports=open_ports,
                            dashboard_items=mapped_items,
                        ),
                        open_ports=open_ports,
                        http_services=http_services_map.get(ip, []),
                        dashboard_items=mapped_items,
                    )
                )

            result = LanScanResult(
                generated_at=_utc_now(),
                duration_ms=int((perf_counter() - started_at) * 1000),
                scanned_hosts=len(host_ips),
                scanned_ports=len(host_ips) * len(self._settings.ports),
                scanned_cidrs=[str(network) for network in networks],
                hosts=hosts,
                source_file=str(self._settings.result_file),
            )
            self._last_result = result
            self._save_result(result)
        except Exception as exc:  # noqa: BLE001
            self._last_error = str(exc)
        finally:
            self._running = False
            self._last_finished_at = _utc_now()
            if self._pending_trigger and self._settings.enabled:
                self._pending_trigger = False
                self._run_task = asyncio.create_task(self._run_scan(), name="lan-scan-run")

    def _resolve_networks(self) -> list[ipaddress.IPv4Network]:
        cidr_values = self._settings.cidrs or _detect_default_cidrs()
        networks: list[ipaddress.IPv4Network] = []
        for cidr in cidr_values:
            with contextlib.suppress(ValueError):
                network = ipaddress.ip_network(cidr, strict=False)
                if isinstance(network, ipaddress.IPv4Network):
                    networks.append(network)

        if not networks:
            networks = [ipaddress.ip_network("192.168.1.0/24", strict=False)]
        return networks

    def _enumerate_hosts(self, networks: list[ipaddress.IPv4Network]) -> list[str]:
        hosts: list[str] = []
        for network in networks:
            for ip in network.hosts():
                hosts.append(str(ip))
                if len(hosts) >= self._settings.max_hosts:
                    return hosts
        return hosts

    async def _scan_open_ports(self, host_ips: list[str]) -> dict[str, list[LanScanPort]]:
        semaphore = asyncio.Semaphore(max(8, self._settings.max_parallel))
        host_parallel = max(1, min(64, self._settings.max_parallel // 8))
        host_semaphore = asyncio.Semaphore(host_parallel)
        batch_size = max(128, min(1024, self._settings.max_parallel * 2))

        async def scan_port(ip: str, port: int) -> bool:
            async with semaphore:
                try:
                    _, writer = await asyncio.wait_for(
                        asyncio.open_connection(ip, port),
                        timeout=self._settings.connect_timeout_sec,
                    )
                except (asyncio.TimeoutError, OSError):
                    return False
                writer.close()
                with contextlib.suppress(OSError):
                    await writer.wait_closed()
                return True

        async def scan_host(ip: str) -> tuple[str, list[LanScanPort]]:
            async with host_semaphore:
                open_ports: list[LanScanPort] = []
                for start in range(0, len(self._settings.ports), batch_size):
                    batch = self._settings.ports[start : start + batch_size]
                    results = await asyncio.gather(*[scan_port(ip, port) for port in batch])
                    for port, is_open in zip(batch, results, strict=True):
                        if is_open:
                            open_ports.append(LanScanPort(port=port, service=PORT_SERVICE_NAMES.get(port)))
                return ip, open_ports

        scanned = await asyncio.gather(*[scan_host(ip) for ip in host_ips])
        return {ip: ports for ip, ports in scanned if ports}

    async def _probe_http_services(
        self,
        open_ports_map: dict[str, list[LanScanPort]],
    ) -> dict[str, list[LanHttpService]]:
        targets: list[tuple[str, int]] = []
        for ip, ports in open_ports_map.items():
            for entry in ports:
                if entry.port in NON_HTTP_PROTOCOL_PORTS:
                    continue
                targets.append((ip, entry.port))

        if not targets:
            return {}

        timeout = max(0.6, min(3.0, self._settings.connect_timeout_sec * 3))
        semaphore = asyncio.Semaphore(max(16, min(128, self._settings.max_parallel // 2)))

        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            verify=False,
            headers={
                "User-Agent": "oko-lan-scan/1.0",
                "Accept": "text/html,application/xhtml+xml,application/json,*/*;q=0.8",
            },
        ) as client:
            async def probe_target(ip: str, port: int) -> tuple[str, LanHttpService | None]:
                async with semaphore:
                    return ip, await self._probe_http_port(client, ip, port)

            probed = await asyncio.gather(*[probe_target(ip, port) for ip, port in targets])

        grouped: dict[str, list[LanHttpService]] = {}
        for ip, service in probed:
            if service is None:
                continue
            grouped.setdefault(ip, []).append(service)

        for services in grouped.values():
            services.sort(key=lambda item: item.port)

        return grouped

    async def _probe_http_port(
        self,
        client: httpx.AsyncClient,
        ip: str,
        port: int,
    ) -> LanHttpService | None:
        errors: list[str] = []

        for scheme in self._http_probe_order(port):
            url = f"{scheme}://{ip}:{port}/"
            try:
                response = await client.get(url)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                errors.append(f"{scheme}: {exc.__class__.__name__}")
                continue

            body = ""
            content_type = (response.headers.get("content-type") or "").lower()
            if "text" in content_type or "json" in content_type or "xml" in content_type:
                with contextlib.suppress(Exception):
                    body = response.text[:180_000]

            title, description = self._extract_html_metadata(body)

            return LanHttpService(
                port=port,
                scheme=scheme,
                url=str(response.url),
                status_code=response.status_code,
                title=title,
                description=description,
                server=response.headers.get("server"),
                error=None,
            )

        if not errors:
            return None

        if port not in HTTP_EXPECTED_PORTS:
            return None

        primary_scheme = self._http_probe_order(port)[0]
        return LanHttpService(
            port=port,
            scheme=primary_scheme,
            url=f"{primary_scheme}://{ip}:{port}/",
            status_code=None,
            title=None,
            description=None,
            server=None,
            error=errors[0],
        )

    @staticmethod
    def _http_probe_order(port: int) -> tuple[str, ...]:
        if port in HTTPS_HINT_PORTS:
            return ("https", "http")
        return ("http", "https")

    @staticmethod
    def _extract_html_metadata(body: str) -> tuple[str | None, str | None]:
        if not body:
            return None, None

        title: str | None = None
        description: str | None = None

        title_match = TITLE_RE.search(body)
        if title_match:
            title = html.unescape(title_match.group(1))
            title = re.sub(r"\s+", " ", title).strip()[:240] or None

        description_match = DESCRIPTION_RE.search(body) or DESCRIPTION_RE_ALT.search(body)
        if description_match:
            description = html.unescape(description_match.group(1))
            description = re.sub(r"\s+", " ", description).strip()[:800] or None

        return title, description

    async def _resolve_hostnames(self, ips: list[str]) -> dict[str, str]:
        semaphore = asyncio.Semaphore(24)

        async def resolve(ip: str) -> tuple[str, str | None]:
            async with semaphore:
                return ip, await asyncio.to_thread(self._safe_reverse_dns, ip)

        resolved = await asyncio.gather(*[resolve(ip) for ip in ips])
        return {ip: hostname for ip, hostname in resolved if hostname}

    @staticmethod
    def _safe_reverse_dns(ip: str) -> str | None:
        try:
            hostname, *_ = socket.gethostbyaddr(ip)
            return hostname
        except OSError:
            return None

    def _resolve_mac_addresses(self, ips: list[str]) -> dict[str, str]:
        if not ips:
            return {}
        table = self._read_arp_table()
        return {ip: table[ip] for ip in ips if ip in table}

    @staticmethod
    def _read_arp_table() -> dict[str, str]:
        result: dict[str, str] = {}

        commands = (
            ("ip", "neigh", "show"),
            ("arp", "-an"),
        )

        for command in commands:
            try:
                completed = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=3.0,
                )
            except (FileNotFoundError, OSError, subprocess.SubprocessError):
                continue

            output = completed.stdout or ""
            if not output:
                continue

            for line in output.splitlines():
                # Linux iproute2 format: 192.168.1.1 dev eth0 lladdr aa:bb:cc:dd:ee:ff REACHABLE
                match = re.search(
                    r"(?P<ip>\d+\.\d+\.\d+\.\d+)\s+dev\s+\S+\s+lladdr\s+(?P<mac>[0-9a-fA-F:.-]{11,20})",
                    line,
                )
                if not match:
                    # BSD/macOS arp format: ? (192.168.1.1) at aa:bb:cc:dd:ee:ff on en0 ...
                    match = re.search(
                        r"\((?P<ip>\d+\.\d+\.\d+\.\d+)\)\s+at\s+(?P<mac>[0-9a-fA-F:.-]{11,20})",
                        line,
                    )
                if not match:
                    continue

                mac = LanScanService._normalize_mac(match.group("mac"))
                if not mac:
                    continue
                result[match.group("ip")] = mac

        return result

    @staticmethod
    def _normalize_mac(raw_mac: str | None) -> str | None:
        if not raw_mac:
            return None
        clean = re.sub(r"[^0-9a-fA-F]", "", raw_mac)
        if len(clean) != 12:
            return None
        chunks = [clean[index : index + 2].upper() for index in range(0, 12, 2)]
        return ":".join(chunks)

    @staticmethod
    def _mac_vendor(mac_address: str | None) -> str | None:
        if not mac_address:
            return None
        prefix = mac_address.replace(":", "")[:6].upper()
        vendor = MAC_OUI_VENDORS.get(prefix)
        if vendor:
            return vendor

        first_octet = int(prefix[:2], 16)
        if first_octet & 0b10:
            return "Locally Administered"
        return None

    @staticmethod
    def _detect_device_type(
        *,
        hostname: str | None,
        vendor: str | None,
        open_ports: list[LanScanPort],
        dashboard_items: list[LanScanMappedService],
    ) -> str:
        ports = {entry.port for entry in open_ports}
        text = " ".join([hostname or "", *[item.title for item in dashboard_items]]).lower()
        vendor_text = (vendor or "").lower()

        if 8006 in ports or "proxmox" in text:
            return "Hypervisor"
        if 3389 in ports or 5985 in ports or 5986 in ports:
            return "Windows PC"
        if 8123 in ports or "home assistant" in text:
            return "IoT Hub"
        if 445 in ports and 139 in ports:
            return "NAS/File Server"
        if 25565 in ports:
            return "Game Server"
        if 5432 in ports or 3306 in ports or 9042 in ports:
            return "Database Server"
        if 9200 in ports or 9300 in ports:
            return "Search Cluster"
        if any(port in ports for port in (80, 443, 8080, 8443)) and len(ports) <= 3:
            return "Web Device"
        if 22 in ports:
            return "Linux/Unix Host"
        if any(key in vendor_text for key in ("mikrotik", "ubiquiti", "tp-link", "cisco", "huawei", "asus")):
            return "Network Device"
        if "raspberry" in vendor_text:
            return "SBC/IoT Device"
        if ports:
            return "Server/Host"
        return "Unknown"

    def _dashboard_services_by_ip(self) -> dict[str, list[LanScanMappedService]]:
        try:
            items = self._config_service.list_items()
        except DashboardConfigValidationError:
            return {}

        mapping: dict[str, list[LanScanMappedService]] = {}
        resolve_cache: dict[str, str | None] = {}

        for item in items:
            ip = self._item_ip(item, resolve_cache)
            if ip is None:
                continue
            mapping.setdefault(ip, []).append(
                LanScanMappedService(id=item.id, title=item.title, url=item.url)
            )

        for entries in mapping.values():
            entries.sort(key=lambda entry: entry.title.lower())

        return mapping

    @staticmethod
    def _item_ip(item: ItemConfig, resolve_cache: dict[str, str | None]) -> str | None:
        host = urlsplit(str(item.url)).hostname
        if not host:
            return None

        # Fast path: host already is an IP address.
        with contextlib.suppress(ValueError):
            parsed_ip = ipaddress.ip_address(host)
            if isinstance(parsed_ip, ipaddress.IPv4Address) and parsed_ip.is_private:
                return str(parsed_ip)
            return None

        if host in resolve_cache:
            return resolve_cache[host]

        resolved_ip: str | None = None
        try:
            candidate = socket.gethostbyname(host)
            parsed_ip = ipaddress.ip_address(candidate)
            if isinstance(parsed_ip, ipaddress.IPv4Address) and parsed_ip.is_private:
                resolved_ip = str(parsed_ip)
        except OSError:
            resolved_ip = None

        resolve_cache[host] = resolved_ip
        return resolved_ip

    def _load_last_result(self) -> LanScanResult | None:
        path = self._settings.result_file
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            result = LanScanResult.model_validate(data)
            result.source_file = str(path)
            return result
        except Exception:  # noqa: BLE001
            return None

    def _save_result(self, result: LanScanResult) -> None:
        payload = result.model_dump(mode="json")
        path = self._settings.result_file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
