from __future__ import annotations

import asyncio
import contextlib
import ipaddress
import json
from datetime import UTC, datetime, timedelta
from time import perf_counter
from typing import Literal

import structlog
from db.repositories import LanScanSnapshotRepository
from scheme.dashboard import (
    LanScanHost,
    LanScanPort,
    LanScanResult,
    LanScanStateResponse,
    LanScanStreamEvent,
)
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

logger = structlog.get_logger()
LAN_SCAN_STOP_TIMEOUT_SEC = 5.0
IMPORTANT_EVENT_PORTS = {
    22,  # ssh
    445,  # smb
    2375,  # docker (unauth)
    3306,  # mysql
    3389,  # rdp
    5432,  # postgres
    5900,  # vnc
    5985,  # winrm
    5986,  # winrm tls
    6379,  # redis
    6443,  # k8s api
    9200,  # elastic
}
LanScanStreamEventType = Literal[
    "snapshot",
    "scan_started",
    "scan_queued",
    "scan_progress",
    "host_found",
    "scan_completed",
    "scan_failed",
]


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _network_host_capacity(network: ipaddress.IPv4Network) -> int:
    if network.prefixlen >= 31:
        return network.num_addresses
    return max(network.num_addresses - 2, 0)


def _candidate_hosts_count(networks: list[ipaddress.IPv4Network]) -> int:
    return sum(_network_host_capacity(network) for network in networks)


def _sorted_hosts(hosts: list[LanScanHost] | tuple[LanScanHost, ...]) -> list[LanScanHost]:
    return sorted(hosts, key=lambda host: ipaddress.ip_address(host.ip))


def _host_is_important(host: LanScanHost) -> bool:
    if host.dashboard_items:
        return True
    return any(entry.port in IMPORTANT_EVENT_PORTS for entry in host.open_ports)


class LanScanService:
    def __init__(
        self,
        *,
        config_service: DashboardConfigService,
        settings: LanScanSettings,
        snapshot_repository: LanScanSnapshotRepository | None = None,
    ):
        self._config_service = config_service
        self._settings = settings
        self._snapshot_repository = snapshot_repository

        self._running = False
        self._last_started_at: datetime | None = None
        self._last_finished_at: datetime | None = None
        self._next_run_at: datetime | None = None
        self._last_error: str | None = None
        self._last_result: LanScanResult | None = self._load_last_result()

        self._periodic_task: asyncio.Task[None] | None = None
        self._run_task: asyncio.Task[None] | None = None
        self._pending_trigger = False
        self._stream_revision = 0
        self._stream_subscribers: set[asyncio.Queue[LanScanStreamEvent]] = set()
        self._stopping = False

    async def start(self) -> None:
        self._stopping = False
        if not self._settings.enabled:
            await logger.ainfo("lan_scan start_skipped scanner_disabled")
            return
        if self._periodic_task and not self._periodic_task.done():
            await logger.ainfo("lan_scan start_skipped scheduler_already_running")
            return

        self._periodic_task = asyncio.create_task(self._periodic_runner(), name="lan-scan-periodic")
        if self._settings.run_on_startup:
            await self.trigger_scan()

    async def stop(self) -> None:
        self._stopping = True
        await logger.ainfo("lan_scan stop_started")

        if self._periodic_task:
            self._periodic_task.cancel()
            try:
                await asyncio.wait_for(self._periodic_task, timeout=LAN_SCAN_STOP_TIMEOUT_SEC)
            except TimeoutError:
                await logger.awarning("lan_scan stop_timeout periodic_task")
            except asyncio.CancelledError:
                pass
            self._periodic_task = None

        while self._run_task and not self._run_task.done():
            current_task = self._run_task
            current_task.cancel()
            try:
                await asyncio.wait_for(current_task, timeout=LAN_SCAN_STOP_TIMEOUT_SEC)
            except TimeoutError:
                await logger.awarning("lan_scan stop_timeout run_task")
                break
            except asyncio.CancelledError:
                pass

            # If task replaced itself (queued rerun race), cancel the new one too.
            if self._run_task is current_task:
                break

        self._run_task = None
        self._pending_trigger = False
        self._next_run_at = None
        self._running = False
        await logger.ainfo("lan_scan stop_completed")

    async def trigger_scan(self) -> bool:
        if self._stopping:
            await logger.ainfo("lan_scan trigger_skipped shutdown_in_progress")
            return False
        if not self._settings.enabled:
            await logger.ainfo("lan_scan trigger_skipped scanner_disabled")
            self._emit_stream_event(
                event_type="scan_failed",
                message="Сканирование отключено настройкой LAN_SCAN_ENABLED=false",
            )
            return False
        if self._run_task and not self._run_task.done():
            self._pending_trigger = True
            await logger.ainfo("lan_scan trigger_queued run_in_progress")
            self._emit_stream_event(
                event_type="scan_queued",
                message="Сканирование уже выполняется, повторный запуск поставлен в очередь",
            )
            return False
        self._run_task = asyncio.create_task(self._run_scan(), name="lan-scan-run")
        await logger.ainfo("lan_scan trigger_accepted run_scheduled")
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

    def subscribe_events(self) -> asyncio.Queue[LanScanStreamEvent]:
        queue: asyncio.Queue[LanScanStreamEvent] = asyncio.Queue(maxsize=256)
        self._stream_subscribers.add(queue)
        snapshot = self._new_stream_event(
            event_type="snapshot",
            message="Подключение к потоку LAN-сканера установлено",
        )
        with contextlib.suppress(asyncio.QueueFull):
            queue.put_nowait(snapshot)
        return queue

    def unsubscribe_events(self, queue: asyncio.Queue[LanScanStreamEvent]) -> None:
        self._stream_subscribers.discard(queue)

    def _new_stream_event(
        self,
        *,
        event_type: LanScanStreamEventType,
        host: LanScanHost | None = None,
        message: str | None = None,
        important: bool = False,
        is_new: bool = False,
    ) -> LanScanStreamEvent:
        self._stream_revision += 1
        return LanScanStreamEvent(
            type=event_type,
            revision=self._stream_revision,
            timestamp=_utc_now(),
            state=self.state(),
            host=host,
            message=message,
            important=important,
            is_new=is_new,
        )

    def _broadcast_stream_event(self, event: LanScanStreamEvent) -> None:
        for queue in tuple(self._stream_subscribers):
            if queue.full():
                with contextlib.suppress(asyncio.QueueEmpty):
                    queue.get_nowait()
            with contextlib.suppress(asyncio.QueueFull):
                queue.put_nowait(event)

    def _emit_stream_event(
        self,
        *,
        event_type: LanScanStreamEventType,
        host: LanScanHost | None = None,
        message: str | None = None,
        important: bool = False,
        is_new: bool = False,
    ) -> None:
        event = self._new_stream_event(
            event_type=event_type,
            host=host,
            message=message,
            important=important,
            is_new=is_new,
        )
        self._broadcast_stream_event(event)

    async def _periodic_runner(self) -> None:
        interval = max(30, self._settings.interval_sec)
        next_tick = _utc_now() + timedelta(seconds=interval)
        scheduler_message = (
            "lan_scan scheduler_started "
            f"interval_sec={interval} "
            f"ports={len(self._settings.ports)} "
            f"max_hosts={self._settings.max_hosts}"
        )
        await logger.ainfo(
            scheduler_message,
            interval_sec=interval,
            ports_count=len(self._settings.ports),
            max_hosts=self._settings.max_hosts,
            max_parallel=self._settings.max_parallel,
        )
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
        previous_host_ips = {
            host.ip
            for host in (self._last_result.hosts if self._last_result is not None else [])
        }
        stage = "initialize"
        cidr_source = "explicit" if self._settings.cidrs else "auto"
        configured_cidrs = (
            self._settings.cidrs
            if self._settings.cidrs
            else await asyncio.to_thread(detect_default_cidrs)
        )
        scanned_cidrs: list[str] = []
        scanned_hosts_done = 0
        progress_hosts: dict[str, LanScanHost] = {}
        host_ips: list[str] = []

        def refresh_progress_result() -> None:
            elapsed_ms = int((perf_counter() - started_at) * 1000)
            self._last_result = LanScanResult(
                generated_at=_utc_now(),
                duration_ms=max(0, elapsed_ms),
                scanned_hosts=max(0, scanned_hosts_done),
                scanned_ports=max(0, scanned_hosts_done * len(self._settings.ports)),
                scanned_cidrs=list(scanned_cidrs),
                hosts=_sorted_hosts(list(progress_hosts.values())),
                source_file=str(self._settings.result_file),
            )

        refresh_progress_result()
        self._emit_stream_event(
            event_type="scan_started",
            message="Запущено новое сканирование LAN",
        )

        await logger.ainfo(
            f"lan_scan started source={cidr_source} cidrs={len(configured_cidrs)} ports={len(self._settings.ports)}",
            cidr_source=cidr_source,
            configured_cidrs=configured_cidrs,
            ports=self._settings.ports,
            max_hosts=self._settings.max_hosts,
            max_parallel=self._settings.max_parallel,
            connect_timeout_sec=self._settings.connect_timeout_sec,
        )

        try:
            stage = "resolve_networks"
            networks = resolve_networks(configured_cidrs)
            scanned_cidrs = [str(network) for network in networks]
            refresh_progress_result()
            await logger.ainfo(
                f"lan_scan networks_resolved source={cidr_source} count={len(scanned_cidrs)}",
                cidr_source=cidr_source,
                scanned_cidrs=scanned_cidrs,
            )

            stage = "enumerate_hosts"
            candidate_hosts = _candidate_hosts_count(networks)
            host_ips = enumerate_hosts(networks, max_hosts=self._settings.max_hosts)
            hosts_capped = candidate_hosts > len(host_ips)
            hosts_enumerated_message = (
                "lan_scan hosts_enumerated "
                f"selected={len(host_ips)} "
                f"candidates={candidate_hosts} "
                f"capped={hosts_capped}"
            )
            await logger.ainfo(
                hosts_enumerated_message,
                selected_hosts=len(host_ips),
                candidate_hosts=candidate_hosts,
                hosts_capped=hosts_capped,
            )

            stage = "map_dashboard"
            dashboard_map = await asyncio.to_thread(
                dashboard_services_by_ip,
                self._config_service,
            )
            mapped_services_total = sum(len(entries) for entries in dashboard_map.values())
            await logger.ainfo(
                f"lan_scan dashboard_mapping hosts={len(dashboard_map)} items={mapped_services_total}",
                mapped_hosts=len(dashboard_map),
                mapped_items=mapped_services_total,
            )

            async def on_host_scanned(ip: str, open_ports: list[LanScanPort]) -> None:
                nonlocal scanned_hosts_done
                scanned_hosts_done += 1
                mapped_items = dashboard_map.get(ip, [])

                if open_ports or mapped_items:
                    existing = progress_hosts.get(ip)
                    host = LanScanHost(
                        ip=ip,
                        hostname=existing.hostname if existing else None,
                        mac_address=existing.mac_address if existing else None,
                        mac_vendor=existing.mac_vendor if existing else None,
                        device_type=detect_device_type(
                            hostname=existing.hostname if existing else None,
                            vendor=existing.mac_vendor if existing else None,
                            open_ports=open_ports,
                            dashboard_items=mapped_items,
                        ),
                        open_ports=open_ports,
                        http_services=existing.http_services if existing else [],
                        dashboard_items=mapped_items,
                    )
                    progress_hosts[ip] = host
                    refresh_progress_result()

                    is_new = ip not in previous_host_ips
                    important = _host_is_important(host)
                    host_message = (
                        f"Найден новый хост {ip}"
                        if is_new
                        else f"Найден хост {ip}"
                    )
                    self._emit_stream_event(
                        event_type="host_found",
                        host=host,
                        message=host_message,
                        important=important,
                        is_new=is_new,
                    )
                    await logger.ainfo(
                        (
                            "lan_scan host_found "
                            f"ip={ip} "
                            f"open_ports={len(open_ports)} "
                            f"dashboard_items={len(mapped_items)} "
                            f"important={important} "
                            f"is_new={is_new} "
                            f"progress={scanned_hosts_done}/{len(host_ips)}"
                        ),
                        ip=ip,
                        open_ports=len(open_ports),
                        dashboard_items=len(mapped_items),
                        important=important,
                        is_new=is_new,
                        scanned_hosts_done=scanned_hosts_done,
                        total_hosts=len(host_ips),
                    )
                elif scanned_hosts_done % 8 == 0 or scanned_hosts_done == len(host_ips):
                    refresh_progress_result()

                if scanned_hosts_done % 8 == 0 or scanned_hosts_done == len(host_ips):
                    self._emit_stream_event(
                        event_type="scan_progress",
                        message=(
                            f"Проверено {scanned_hosts_done}/{len(host_ips)} IP "
                            f"({len(progress_hosts)} c найденными сервисами)"
                        ),
                    )
                    await logger.ainfo(
                        (
                            "lan_scan progress "
                            f"scanned={scanned_hosts_done}/{len(host_ips)} "
                            f"discovered={len(progress_hosts)}"
                        ),
                        scanned_hosts_done=scanned_hosts_done,
                        total_hosts=len(host_ips),
                        discovered_hosts=len(progress_hosts),
                    )

            stage = "scan_ports"
            open_ports_map = await scan_open_ports(
                host_ips,
                self._settings,
                on_host_scanned=on_host_scanned,
            )
            open_ports_total = sum(len(ports) for ports in open_ports_map.values())
            await logger.ainfo(
                f"lan_scan ports_scanned hosts_with_open_ports={len(open_ports_map)} open_ports={open_ports_total}",
                hosts_with_open_ports=len(open_ports_map),
                open_ports_total=open_ports_total,
            )

            stage = "probe_http"
            http_services_map = await probe_http_services(open_ports_map, self._settings)

            stage = "resolve_metadata"
            discovered_ips = sorted(
                set(open_ports_map.keys()) | set(dashboard_map.keys()),
                key=ipaddress.ip_address,
            )
            hostnames = await resolve_hostnames_with_services(discovered_ips, http_services_map)
            macs = await asyncio.to_thread(resolve_mac_addresses, discovered_ips)
            http_services_total = sum(len(entries) for entries in http_services_map.values())
            metadata_message = (
                "lan_scan metadata_resolved "
                f"hosts={len(discovered_ips)} "
                f"hostnames={len(hostnames)} "
                f"macs={len(macs)} "
                f"http_services={http_services_total}"
            )
            await logger.ainfo(
                metadata_message,
                discovered_hosts=len(discovered_ips),
                resolved_hostnames=len(hostnames),
                resolved_macs=len(macs),
                http_services=http_services_total,
            )

            stage = "build_result"
            hosts: list[LanScanHost] = []
            for index, ip in enumerate(discovered_ips, start=1):
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
                if index % 32 == 0:
                    await asyncio.sleep(0)

            result = LanScanResult(
                generated_at=_utc_now(),
                duration_ms=int((perf_counter() - started_at) * 1000),
                scanned_hosts=len(host_ips),
                scanned_ports=len(host_ips) * len(self._settings.ports),
                scanned_cidrs=scanned_cidrs,
                hosts=hosts,
                source_file=str(self._settings.result_file),
            )
            self._last_result = result
            self._emit_stream_event(
                event_type="scan_completed",
                message=(
                    f"Сканирование завершено: обнаружено {len(hosts)} хостов за "
                    f"{result.duration_ms} ms"
                ),
            )
            stage = "persist_result"
            await asyncio.to_thread(self._save_snapshot_to_db, result)
            await asyncio.to_thread(save_result, self._settings.result_file, result)

            completed_message = (
                "lan_scan completed "
                f"duration_ms={result.duration_ms} "
                f"scanned_hosts={result.scanned_hosts} "
                f"discovered_hosts={len(hosts)}"
            )
            await logger.ainfo(
                completed_message,
                duration_ms=result.duration_ms,
                scanned_hosts=result.scanned_hosts,
                discovered_hosts=len(hosts),
                scanned_ports=result.scanned_ports,
                scanned_cidrs=result.scanned_cidrs,
            )
        except asyncio.CancelledError:
            await logger.ainfo(f"lan_scan cancelled stage={stage}")
            raise
        except Exception as exc:
            self._last_error = f"{stage}: {exc}"
            self._emit_stream_event(
                event_type="scan_failed",
                message=f"Ошибка этапа {stage}: {exc}",
            )
            await logger.aerror(
                f"lan_scan failed stage={stage}",
                stage=stage,
                error=str(exc),
                exc_info=True,
            )
        finally:
            self._running = False
            self._last_finished_at = _utc_now()
            if self._pending_trigger and self._settings.enabled and not self._stopping:
                self._pending_trigger = False
                await logger.ainfo("lan_scan queued_rerun_started")
                self._run_task = asyncio.create_task(self._run_scan(), name="lan-scan-run")
            elif self._pending_trigger and self._stopping:
                self._pending_trigger = False
                await logger.ainfo("lan_scan queued_rerun_skipped shutdown_in_progress")

    def _load_last_result(self) -> LanScanResult | None:
        if self._snapshot_repository is None:
            return load_last_result(self._settings.result_file)

        stored = self._snapshot_repository.fetch_latest()
        if stored is not None:
            with contextlib.suppress(Exception):
                data = json.loads(stored.payload_json)
                result = LanScanResult.model_validate(data)
                result.source_file = str(self._settings.result_file)
                return result

        return load_last_result(self._settings.result_file)

    def _save_snapshot_to_db(self, result: LanScanResult) -> None:
        if self._snapshot_repository is None:
            return
        with contextlib.suppress(Exception):
            payload_json = json.dumps(
                result.model_dump(mode="json"),
                ensure_ascii=False,
                separators=(",", ":"),
            )
            self._snapshot_repository.save_snapshot(
                generated_at=result.generated_at,
                payload_json=payload_json,
            )
            self._snapshot_repository.prune_old(keep_last=20)


__all__ = ["LanScanService"]
