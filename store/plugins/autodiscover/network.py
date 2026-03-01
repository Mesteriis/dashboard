from __future__ import annotations

import asyncio
import contextlib
import inspect
import ipaddress
import logging
import socket
import subprocess  # nosec B404
from collections.abc import Awaitable, Callable
from typing import Any

from .constants import _IFCONFIG_INET_RE, _IP_ADDR_INET_RE, PORT_SERVICE_NAMES
from .schemas import ScanRequest

logger = logging.getLogger("core.plugins.autodiscover")


def _network_from_interface_token(token: str) -> str | None:
    with contextlib.suppress(ValueError):
        interface = ipaddress.ip_interface(token)
        if not isinstance(interface.ip, ipaddress.IPv4Address):
            return None
        if interface.ip.is_loopback or interface.ip.is_link_local:
            return None
        return str(interface.network)
    return None


def _prefix_from_netmask(mask: str) -> int | None:
    mask_token = mask.strip().lower()
    if not mask_token:
        return None

    if mask_token.startswith("0x"):
        with contextlib.suppress(ValueError):
            mask_as_int = int(mask_token, 16)
            dotted = str(ipaddress.IPv4Address(mask_as_int))
            return ipaddress.ip_network(f"0.0.0.0/{dotted}", strict=False).prefixlen
        return None

    with contextlib.suppress(ValueError):
        return ipaddress.ip_network(f"0.0.0.0/{mask_token}", strict=False).prefixlen
    return None


def _detect_cidrs_from_ip_addr() -> tuple[str, ...]:
    try:
        completed = subprocess.run(  # nosec B603
            ("ip", "-o", "-4", "addr", "show", "up"),
            capture_output=True,
            text=True,
            check=False,
            timeout=3.0,
        )
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return ()

    cidrs: list[str] = []
    for line in (completed.stdout or "").splitlines():
        match = _IP_ADDR_INET_RE.search(line)
        if not match:
            continue
        cidr = _network_from_interface_token(match.group("addr"))
        if cidr:
            cidrs.append(cidr)
    return tuple(dict.fromkeys(cidrs))


def _detect_cidrs_from_ifconfig() -> tuple[str, ...]:
    try:
        completed = subprocess.run(  # nosec B603
            ("ifconfig",),
            capture_output=True,
            text=True,
            check=False,
            timeout=3.0,
        )
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return ()

    cidrs: list[str] = []
    for line in (completed.stdout or "").splitlines():
        match = _IFCONFIG_INET_RE.search(line)
        if not match:
            continue

        ip = match.group("ip")
        if not ip:
            continue

        try:
            parsed_ip = ipaddress.ip_address(ip)
        except ValueError:
            continue

        if not isinstance(parsed_ip, ipaddress.IPv4Address):
            continue
        if parsed_ip.is_loopback or parsed_ip.is_link_local:
            continue

        prefix = 24
        mask_token = match.group("mask")
        if mask_token:
            parsed_prefix = _prefix_from_netmask(mask_token)
            if parsed_prefix is not None:
                prefix = parsed_prefix

        cidr = str(ipaddress.ip_network(f"{ip}/{prefix}", strict=False))
        cidrs.append(cidr)

    return tuple(dict.fromkeys(cidrs))


def _detect_cidrs_from_udp_probe() -> tuple[str, ...]:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            local_ip = sock.getsockname()[0]
            network = ipaddress.ip_network(f"{local_ip}/24", strict=False)
            return (str(network),)
    except OSError:
        return ()


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
    if max_hosts <= 0:
        return []

    hosts: list[str] = []
    seen_hosts: set[str] = set()
    host_iters = [iter(network.hosts()) for network in networks]

    while host_iters and len(hosts) < max_hosts:
        next_round: list[Any] = []
        for host_iter in host_iters:
            if len(hosts) >= max_hosts:
                break
            try:
                candidate = str(next(host_iter))
            except StopIteration:
                continue

            next_round.append(host_iter)
            if candidate in seen_hosts:
                continue

            seen_hosts.add(candidate)
            hosts.append(candidate)
        host_iters = next_round

    return hosts


async def scan_open_ports(
    host_ips: list[str],
    request: ScanRequest,
    *,
    on_host_scanned: Callable[[str, list[dict[str, Any]]], Awaitable[None] | None] | None = None,
    on_service_found: Callable[[str, dict[str, Any]], Awaitable[None] | None] | None = None,
    on_chunk_started: Callable[[str, int, int], Awaitable[None] | None] | None = None,
    on_chunk_scanned: Callable[[str, int, int, int], Awaitable[None] | None] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    # Stage 2: each discovered host gets dedicated chunk tasks: 1-100, 101-200, ...
    chunk_size = 100

    def _chunk_ports(ports: tuple[int, ...], *, size: int) -> list[tuple[int, int, tuple[int, ...]]]:
        if not ports:
            return []
        buckets: dict[int, list[int]] = {}
        for port in ports:
            bucket = (int(port) - 1) // size
            buckets.setdefault(bucket, []).append(int(port))
        chunks: list[tuple[int, int, tuple[int, ...]]] = []
        for bucket in sorted(buckets):
            start_port = bucket * size + 1
            end_port = start_port + size - 1
            chunk_ports = tuple(sorted(set(buckets[bucket])))
            chunks.append((start_port, end_port, chunk_ports))
        return chunks

    port_chunks = _chunk_ports(request.ports, size=chunk_size)
    if not port_chunks:
        return {}

    semaphore = asyncio.Semaphore(max(8, request.max_parallel))
    host_parallel = max(1, min(64, request.max_parallel // 8))
    host_semaphore = asyncio.Semaphore(host_parallel)
    host_batch_size = max(8, min(128, host_parallel * 4))
    chunk_parallel = max(1, min(16, request.max_parallel // 16))

    logger.info(
        "Autodiscover staged port scan hosts=%s chunks_per_host=%s chunk_size=%s host_parallel=%s chunk_parallel=%s",
        len(host_ips),
        len(port_chunks),
        chunk_size,
        host_parallel,
        chunk_parallel,
    )

    async def scan_port(ip: str, port: int) -> bool:
        async with semaphore:
            try:
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection(ip, port),
                    timeout=request.connect_timeout_sec,
                )
            except (TimeoutError, OSError):
                return False

            writer.close()
            with contextlib.suppress(OSError):
                await writer.wait_closed()
            return True

    async def scan_host(ip: str) -> tuple[str, list[dict[str, Any]]]:
        async with host_semaphore:
            logger.info("Autodiscover host scan queued ip=%s chunk_tasks=%s", ip, len(port_chunks))
            open_ports: list[dict[str, Any]] = []
            seen_open_ports: set[int] = set()

            async def _scan_chunk(
                start_port: int,
                end_port: int,
                ports: tuple[int, ...],
            ) -> tuple[int, int, list[dict[str, Any]]]:
                logger.info(
                    "Autodiscover chunk task queued ip=%s range=%s-%s ports=%s",
                    ip,
                    start_port,
                    end_port,
                    len(ports),
                )
                if on_chunk_started is not None:
                    maybe_awaitable = on_chunk_started(ip, start_port, end_port)
                    if inspect.isawaitable(maybe_awaitable):
                        await maybe_awaitable

                async def _scan_port_result(port: int) -> tuple[int, bool]:
                    return port, await scan_port(ip, port)

                chunk_open_ports: list[dict[str, Any]] = []
                tasks = [asyncio.create_task(_scan_port_result(port)) for port in ports]
                try:
                    for completed_task in asyncio.as_completed(tasks):
                        port, is_open = await completed_task
                        if not is_open:
                            continue
                        service_row = {"port": port, "service": PORT_SERVICE_NAMES.get(port)}
                        chunk_open_ports.append(service_row)
                        if on_service_found is not None:
                            maybe_awaitable = on_service_found(ip, service_row)
                            if inspect.isawaitable(maybe_awaitable):
                                await maybe_awaitable
                finally:
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    if tasks:
                        await asyncio.gather(*tasks, return_exceptions=True)

                chunk_open_ports.sort(key=lambda item: int(item["port"]))
                if on_chunk_scanned is not None:
                    maybe_awaitable = on_chunk_scanned(
                        ip,
                        start_port,
                        end_port,
                        len(chunk_open_ports),
                    )
                    if inspect.isawaitable(maybe_awaitable):
                        await maybe_awaitable
                if chunk_open_ports:
                    logger.info(
                        "Autodiscover chunk task completed ip=%s range=%s-%s open_ports=%s",
                        ip,
                        start_port,
                        end_port,
                        len(chunk_open_ports),
                    )
                return start_port, end_port, chunk_open_ports

            for start in range(0, len(port_chunks), chunk_parallel):
                chunk_batch = port_chunks[start : start + chunk_parallel]
                tasks = [
                    asyncio.create_task(
                        _scan_chunk(
                            chunk_start,
                            chunk_end,
                            chunk_ports,
                        )
                    )
                    for chunk_start, chunk_end, chunk_ports in chunk_batch
                ]
                try:
                    for completed_task in asyncio.as_completed(tasks):
                        _, _, chunk_open_ports = await completed_task
                        for service_row in chunk_open_ports:
                            port = int(service_row["port"])
                            if port in seen_open_ports:
                                continue
                            seen_open_ports.add(port)
                            open_ports.append(service_row)
                finally:
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    if tasks:
                        await asyncio.gather(*tasks, return_exceptions=True)
                await asyncio.sleep(0)
            open_ports.sort(key=lambda item: int(item["port"]))
            logger.info("Autodiscover host scan completed ip=%s open_ports=%s", ip, len(open_ports))
            return ip, open_ports

    discovered: dict[str, list[dict[str, Any]]] = {}
    for start in range(0, len(host_ips), host_batch_size):
        batch = host_ips[start : start + host_batch_size]
        tasks = [asyncio.create_task(scan_host(ip)) for ip in batch]
        try:
            for completed_task in asyncio.as_completed(tasks):
                ip, ports = await completed_task
                if on_host_scanned is not None:
                    maybe_awaitable = on_host_scanned(ip, ports)
                    if inspect.isawaitable(maybe_awaitable):
                        await maybe_awaitable
                if ports:
                    discovered[ip] = ports
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        await asyncio.sleep(0)

    return discovered


__all__ = [
    "_detect_cidrs_from_ifconfig",
    "_detect_cidrs_from_ip_addr",
    "_detect_cidrs_from_udp_probe",
    "detect_default_cidrs",
    "enumerate_hosts",
    "resolve_networks",
    "scan_open_ports",
]
