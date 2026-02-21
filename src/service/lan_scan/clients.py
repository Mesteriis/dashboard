from __future__ import annotations

import asyncio
import contextlib
import ipaddress
import json
import os
import re
import socket
import ssl
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

import httpx

from scheme.dashboard import (
    ItemConfig,
    LanHttpService,
    LanScanMappedService,
    LanScanPort,
    LanScanResult,
)
from service.config_service import DashboardConfigService, DashboardConfigValidationError

from .parsers import extract_html_metadata, normalize_mac
from .settings import (
    HTTP_EXPECTED_PORTS,
    HTTPS_HINT_PORTS,
    NON_HTTP_PROTOCOL_PORTS,
    PORT_SERVICE_NAMES,
    LanScanSettings,
)


def detect_default_cidrs() -> tuple[str, ...]:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            local_ip = sock.getsockname()[0]
            network = ipaddress.ip_network(f"{local_ip}/24", strict=False)
            return (str(network),)
    except OSError:
        return ("192.168.1.0/24",)


def resolve_networks(cidr_values: tuple[str, ...]) -> list[ipaddress.IPv4Network]:
    networks: list[ipaddress.IPv4Network] = []
    for cidr in cidr_values:
        with contextlib.suppress(ValueError):
            network = ipaddress.ip_network(cidr, strict=False)
            if isinstance(network, ipaddress.IPv4Network):
                networks.append(network)

    if not networks:
        return [ipaddress.IPv4Network("192.168.1.0/24")]
    return networks


def enumerate_hosts(networks: list[ipaddress.IPv4Network], *, max_hosts: int) -> list[str]:
    hosts: list[str] = []
    for network in networks:
        for ip in network.hosts():
            hosts.append(str(ip))
            if len(hosts) >= max_hosts:
                return hosts
    return hosts


async def scan_open_ports(host_ips: list[str], settings: LanScanSettings) -> dict[str, list[LanScanPort]]:
    semaphore = asyncio.Semaphore(max(8, settings.max_parallel))
    host_parallel = max(1, min(64, settings.max_parallel // 8))
    host_semaphore = asyncio.Semaphore(host_parallel)
    batch_size = max(128, min(1024, settings.max_parallel * 2))

    async def scan_port(ip: str, port: int) -> bool:
        async with semaphore:
            try:
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection(ip, port),
                    timeout=settings.connect_timeout_sec,
                )
            except (TimeoutError, OSError):
                return False
            writer.close()
            with contextlib.suppress(OSError):
                await writer.wait_closed()
            return True

    async def scan_host(ip: str) -> tuple[str, list[LanScanPort]]:
        async with host_semaphore:
            open_ports: list[LanScanPort] = []
            for start in range(0, len(settings.ports), batch_size):
                batch = settings.ports[start : start + batch_size]
                results = await asyncio.gather(*[scan_port(ip, port) for port in batch])
                for port, is_open in zip(batch, results, strict=True):
                    if is_open:
                        open_ports.append(LanScanPort(port=port, service=PORT_SERVICE_NAMES.get(port)))
            return ip, open_ports

    scanned = await asyncio.gather(*[scan_host(ip) for ip in host_ips])
    return {ip: ports for ip, ports in scanned if ports}


def _http_probe_order(port: int) -> tuple[Literal["http", "https"], Literal["http", "https"]]:
    if port in HTTPS_HINT_PORTS:
        return ("https", "http")
    return ("http", "https")


async def _probe_http_port(
    client: httpx.AsyncClient,
    *,
    ip: str,
    port: int,
) -> LanHttpService | None:
    errors: list[str] = []
    probe_order = _http_probe_order(port)

    for scheme in probe_order:
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

        title, description = extract_html_metadata(body)

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

    primary_scheme = probe_order[0]
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


async def probe_http_services(
    open_ports_map: dict[str, list[LanScanPort]],
    settings: LanScanSettings,
) -> dict[str, list[LanHttpService]]:
    targets: list[tuple[str, int]] = []
    for ip, ports in open_ports_map.items():
        for entry in ports:
            if entry.port in NON_HTTP_PROTOCOL_PORTS:
                continue
            targets.append((ip, entry.port))

    if not targets:
        return {}

    timeout = max(0.6, min(3.0, settings.connect_timeout_sec * 3))
    semaphore = asyncio.Semaphore(max(16, min(128, settings.max_parallel // 2)))

    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        verify=settings.http_verify_tls,
        headers={
            "User-Agent": "oko-lan-scan/1.0",
            "Accept": "text/html,application/xhtml+xml,application/json,*/*;q=0.8",
        },
    ) as client:

        async def probe_target(ip: str, port: int) -> tuple[str, LanHttpService | None]:
            async with semaphore:
                return ip, await _probe_http_port(client, ip=ip, port=port)

        probed = await asyncio.gather(*[probe_target(ip, port) for ip, port in targets])

    grouped: dict[str, list[LanHttpService]] = {}
    for ip, service in probed:
        if service is None:
            continue
        grouped.setdefault(ip, []).append(service)

    for services in grouped.values():
        services.sort(key=lambda item: item.port)

    return grouped


async def resolve_hostnames(ips: list[str]) -> dict[str, str]:
    return await resolve_hostnames_with_services(ips, {})


async def resolve_hostnames_with_services(
    ips: list[str],
    http_services_map: dict[str, list[LanHttpService]],
) -> dict[str, str]:
    semaphore = asyncio.Semaphore(24)

    async def resolve(ip: str) -> tuple[str, str | None]:
        async with semaphore:
            return ip, await asyncio.to_thread(safe_reverse_dns, ip)

    resolved = await asyncio.gather(*[resolve(ip) for ip in ips])
    hostnames = {ip: hostname for ip, hostname in resolved if hostname}

    tls_semaphore = asyncio.Semaphore(8)

    async def resolve_tls(ip: str) -> tuple[str, str | None]:
        services = http_services_map.get(ip, [])
        if not services:
            return ip, None
        async with tls_semaphore:
            return ip, await asyncio.to_thread(hostname_from_tls_services, ip, services)

    unresolved_ips = [ip for ip in ips if ip not in hostnames]
    if unresolved_ips:
        tls_resolved = await asyncio.gather(*[resolve_tls(ip) for ip in unresolved_ips])
        for ip, hostname in tls_resolved:
            if hostname:
                hostnames[ip] = hostname

    return hostnames


def safe_reverse_dns(ip: str) -> str | None:
    try:
        hostname, *_ = socket.gethostbyaddr(ip)
        return hostname
    except OSError:
        return None


def _normalize_hostname(value: str, ip: str) -> str | None:
    candidate = value.strip().rstrip(".").lower()
    if not candidate:
        return None
    if candidate in {"localhost", "localhost.localdomain"}:
        return None
    if candidate == ip:
        return None
    if " " in candidate:
        return None
    with contextlib.suppress(ValueError):
        if ipaddress.ip_address(candidate):
            return None
    return candidate


def hostname_from_tls_services(ip: str, services: list[LanHttpService]) -> str | None:
    ports = sorted(
        {
            entry.port
            for entry in services
            if entry.scheme == "https"
        }
    )
    for port in ports:
        candidate = hostname_from_tls_certificate(ip, port)
        if candidate:
            return candidate
    return None


def hostname_from_tls_certificate(ip: str, port: int) -> str | None:
    cert_file_path: str | None = None
    try:
        pem_certificate = ssl.get_server_certificate((ip, port), timeout=1.5)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".pem", delete=False) as cert_file:
            cert_file.write(pem_certificate)
            cert_file_path = cert_file.name

        ssl_private = getattr(ssl, "_ssl", None)
        decode_certificate = getattr(ssl_private, "_test_decode_cert", None)
        if not callable(decode_certificate):
            return None
        decoded_any = decode_certificate(cert_file_path)
        if not isinstance(decoded_any, dict):
            return None
        decoded: dict[str, Any] = decoded_any
    except Exception:
        return None
    finally:
        if cert_file_path and os.path.exists(cert_file_path):
            with contextlib.suppress(OSError):
                os.unlink(cert_file_path)

    for rdns in decoded.get("subject", ()):
        for key, value in rdns:
            if key != "commonName":
                continue
            candidate = _normalize_hostname(value, ip)
            if candidate:
                return candidate

    for key, value in decoded.get("subjectAltName", ()):
        if key != "DNS":
            continue
        candidate = _normalize_hostname(value, ip)
        if candidate:
            return candidate

    return None


def read_arp_table() -> dict[str, str]:
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
            match = re.search(
                r"(?P<ip>\d+\.\d+\.\d+\.\d+)\s+dev\s+\S+\s+lladdr\s+(?P<mac>[0-9a-fA-F:.-]{11,20})",
                line,
            )
            if not match:
                match = re.search(
                    r"\((?P<ip>\d+\.\d+\.\d+\.\d+)\)\s+at\s+(?P<mac>[0-9a-fA-F:.-]{11,20})",
                    line,
                )
            if not match:
                continue

            mac = normalize_mac(match.group("mac"))
            if not mac:
                continue
            result[match.group("ip")] = mac

    return result


def resolve_mac_addresses(ips: list[str]) -> dict[str, str]:
    if not ips:
        return {}
    table = read_arp_table()
    return {ip: table[ip] for ip in ips if ip in table}


def item_ip(item: ItemConfig, resolve_cache: dict[str, str | None]) -> str | None:
    host = urlsplit(str(item.url)).hostname
    if not host:
        return None

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


def dashboard_services_by_ip(config_service: DashboardConfigService) -> dict[str, list[LanScanMappedService]]:
    try:
        items = config_service.list_items()
    except DashboardConfigValidationError:
        return {}

    mapping: dict[str, list[LanScanMappedService]] = {}
    resolve_cache: dict[str, str | None] = {}

    for item in items:
        ip = item_ip(item, resolve_cache)
        if ip is None:
            continue
        mapping.setdefault(ip, []).append(
            LanScanMappedService(id=item.id, title=item.title, url=item.url)
        )

    for entries in mapping.values():
        entries.sort(key=lambda entry: entry.title.lower())

    return mapping


def load_last_result(result_file: Path) -> LanScanResult | None:
    if not result_file.exists():
        return None
    try:
        data = json.loads(result_file.read_text(encoding="utf-8"))
        result = LanScanResult.model_validate(data)
        for host in result.hosts:
            for port in host.open_ports:
                if port.service:
                    continue
                port.service = PORT_SERVICE_NAMES.get(port.port)
            if not host.hostname:
                host.hostname = hostname_from_tls_services(host.ip, host.http_services)
        result.source_file = str(result_file)
        return result
    except Exception:
        return None


def save_result(result_file: Path, result: LanScanResult) -> None:
    payload = result.model_dump(mode="json")
    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


__all__ = [
    "dashboard_services_by_ip",
    "detect_default_cidrs",
    "enumerate_hosts",
    "load_last_result",
    "probe_http_services",
    "resolve_hostnames",
    "resolve_mac_addresses",
    "resolve_networks",
    "save_result",
    "scan_open_ports",
]
