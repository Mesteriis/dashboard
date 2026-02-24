from __future__ import annotations

import asyncio
import contextlib
import ipaddress
import re
import socket
import ssl
import subprocess  # nosec B404
import tempfile
from pathlib import Path
from typing import Any

from .constants import MAC_OUI_VENDORS

_HOSTNAME_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9._-]{1,62}")
_HOSTNAME_TOKEN_BLACKLIST = {
    "apache",
    "cloudflare",
    "http",
    "https",
    "microsoft-iis",
    "nginx",
    "openresty",
    "server",
}


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
        if cert_file_path and Path(cert_file_path).exists():
            with contextlib.suppress(OSError):
                Path(cert_file_path).unlink()

    for rdns in decoded.get("subject", ()):  # type: ignore[assignment]
        for key, value in rdns:
            if key != "commonName":
                continue
            candidate = _normalize_hostname(value, ip)
            if candidate:
                return candidate

    for key, value in decoded.get("subjectAltName", ()):  # type: ignore[assignment]
        if key != "DNS":
            continue
        candidate = _normalize_hostname(value, ip)
        if candidate:
            return candidate

    return None


def hostname_from_tls_services(ip: str, services: list[dict[str, Any]]) -> str | None:
    ports = sorted({int(entry["port"]) for entry in services if entry.get("scheme") == "https"})
    for port in ports:
        candidate = hostname_from_tls_certificate(ip, port)
        if candidate:
            return candidate
    return None


async def resolve_hostnames_with_services(
    ips: list[str],
    http_services_map: dict[str, list[dict[str, Any]]],
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
        unresolved_ips = [ip for ip in ips if ip not in hostnames]

    if unresolved_ips:
        arp_hostnames = await asyncio.to_thread(resolve_hostnames_from_arp, unresolved_ips)
        hostnames.update(arp_hostnames)
        unresolved_ips = [ip for ip in ips if ip not in hostnames]

    if unresolved_ips:
        for ip in unresolved_ips:
            fallback = hostname_from_http_metadata(ip, http_services_map.get(ip, []))
            if fallback:
                hostnames[ip] = fallback

    return hostnames


def normalize_mac(raw_mac: str | None) -> str | None:
    if not raw_mac:
        return None

    text = raw_mac.strip()
    if not text:
        return None

    separated_parts = [chunk for chunk in re.split(r"[:-]", text) if chunk]
    if len(separated_parts) == 6 and all(re.fullmatch(r"[0-9a-fA-F]{1,2}", chunk) for chunk in separated_parts):
        return ":".join(f"{int(chunk, 16):02X}" for chunk in separated_parts)

    dotted_parts = text.split(".")
    if len(dotted_parts) == 3 and all(re.fullmatch(r"[0-9a-fA-F]{1,4}", chunk) for chunk in dotted_parts):
        clean = "".join(chunk.zfill(4) for chunk in dotted_parts)
    else:
        clean = re.sub(r"[^0-9a-fA-F]", "", text)

    if len(clean) != 12:
        return None

    chunks = [clean[index : index + 2].upper() for index in range(0, 12, 2)]
    return ":".join(chunks)


def read_arp_table() -> dict[str, str]:
    result: dict[str, str] = {}
    commands = (("ip", "neigh", "show"), ("arp", "-an"))

    for command in commands:
        try:
            completed = subprocess.run(  # nosec B603
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


def resolve_hostnames_from_arp(ips: list[str]) -> dict[str, str]:
    if not ips:
        return {}
    target_ips = set(ips)
    hostnames: dict[str, str] = {}

    try:
        completed = subprocess.run(  # nosec B603
            ("arp", "-an"),
            capture_output=True,
            text=True,
            check=False,
            timeout=3.0,
        )
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return {}

    output = completed.stdout or ""
    if not output:
        return {}

    for line in output.splitlines():
        match = re.search(
            r"(?P<name>\S+)\s+\((?P<ip>\d+\.\d+\.\d+\.\d+)\)\s+at\s+(?P<mac>[0-9a-fA-F:.-]{2,20}|\(incomplete\))",
            line,
        )
        if not match:
            continue
        ip = match.group("ip")
        if ip not in target_ips:
            continue
        name = match.group("name")
        if name == "?":
            continue
        candidate = _normalize_hostname(name, ip)
        if candidate:
            hostnames[ip] = candidate
    return hostnames


def hostname_from_http_metadata(ip: str, services: list[dict[str, Any]]) -> str | None:
    for service in services:
        if not isinstance(service, dict):
            continue
        for field in ("title", "server", "description"):
            value = service.get(field)
            if not isinstance(value, str) or not value.strip():
                continue
            for token in _HOSTNAME_TOKEN_RE.findall(value):
                candidate = _normalize_hostname(token, ip)
                if not candidate:
                    continue
                if candidate in _HOSTNAME_TOKEN_BLACKLIST:
                    continue
                return candidate
    return None


def mac_vendor(mac_address: str | None) -> str | None:
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


def detect_device_type(
    *,
    hostname: str | None,
    vendor: str | None,
    open_ports: list[dict[str, Any]],
    dashboard_items: list[dict[str, Any]],
) -> str:
    ports = {int(entry["port"]) for entry in open_ports}
    text = " ".join([hostname or "", *[str(item.get("title", "")) for item in dashboard_items]]).lower()
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


__all__ = [
    "detect_device_type",
    "hostname_from_http_metadata",
    "hostname_from_tls_services",
    "mac_vendor",
    "normalize_mac",
    "resolve_hostnames_from_arp",
    "resolve_hostnames_with_services",
    "resolve_mac_addresses",
    "safe_reverse_dns",
]
