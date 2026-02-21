from __future__ import annotations

import asyncio
import contextlib
import ipaddress
from datetime import UTC, datetime, timedelta
from time import perf_counter

from scheme.dashboard import LanScanHost, LanScanResult, LanScanStateResponse
from service.config_service import DashboardConfigService

from .clients import (
    dashboard_services_by_ip,
    detect_default_cidrs,
    enumerate_hosts,
    load_last_result,
    probe_http_services,
    resolve_hostnames_with_services,
    resolve_mac_addresses,
    resolve_networks,
    save_result,
    scan_open_ports,
)
from .parsers import detect_device_type, mac_vendor
from .settings import LanScanSettings


def _utc_now() -> datetime:
    return datetime.now(UTC)


class LanScanService:
    def __init__(self, *, config_service: DashboardConfigService, settings: LanScanSettings):
        self._config_service = config_service
        self._settings = settings

        self._running = False
        self._last_started_at: datetime | None = None
        self._last_finished_at: datetime | None = None
        self._next_run_at: datetime | None = None
        self._last_error: str | None = None
        self._last_result: LanScanResult | None = load_last_result(settings.result_file)

        self._periodic_task: asyncio.Task[None] | None = None
        self._run_task: asyncio.Task[None] | None = None
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
            networks = resolve_networks(self._settings.cidrs or detect_default_cidrs())
            host_ips = enumerate_hosts(networks, max_hosts=self._settings.max_hosts)

            open_ports_map = await scan_open_ports(host_ips, self._settings)
            http_services_map = await probe_http_services(open_ports_map, self._settings)
            dashboard_map = await asyncio.to_thread(dashboard_services_by_ip, self._config_service)

            discovered_ips = sorted(
                set(open_ports_map.keys()) | set(dashboard_map.keys()),
                key=lambda raw: ipaddress.ip_address(raw),
            )
            hostnames = await resolve_hostnames_with_services(discovered_ips, http_services_map)
            macs = await asyncio.to_thread(resolve_mac_addresses, discovered_ips)

            hosts: list[LanScanHost] = []
            for ip in discovered_ips:
                open_ports = open_ports_map.get(ip, [])
                mapped_items = dashboard_map.get(ip, [])
                mac_address = macs.get(ip)
                vendor = mac_vendor(mac_address)

                hosts.append(
                    LanScanHost(
                        ip=ip,
                        hostname=hostnames.get(ip),
                        mac_address=mac_address,
                        mac_vendor=vendor,
                        device_type=detect_device_type(
                            hostname=hostnames.get(ip),
                            vendor=vendor,
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
            save_result(self._settings.result_file, result)
        except Exception as exc:
            self._last_error = str(exc)
        finally:
            self._running = False
            self._last_finished_at = _utc_now()
            if self._pending_trigger and self._settings.enabled:
                self._pending_trigger = False
                self._run_task = asyncio.create_task(self._run_scan(), name="lan-scan-run")


__all__ = ["LanScanService"]
