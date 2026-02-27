from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from uuid import UUID

from apps.health.model.contracts import HealthCheckRequestedV1, MonitoredService
from apps.health.service.config_sync import extract_service_specs_from_config
from apps.health.service.repository import HealthRepository
from core.bus.client import BusClient
from core.contracts.bus import BusMessageV1
from core.storage.repositories import ConfigRepository

LOGGER = logging.getLogger(__name__)


class HealthScheduler:
    def __init__(
        self,
        *,
        bus_client: BusClient,
        repository: HealthRepository,
        config_repository: ConfigRepository,
        tick_sec: float,
        window_size: int,
        retention_days: int,
        default_interval_sec: int,
        default_timeout_ms: int,
        default_latency_threshold_ms: int,
        heartbeat_sec: float,
    ) -> None:
        self._bus_client = bus_client
        self._repository = repository
        self._config_repository = config_repository
        self._tick_sec = max(0.2, tick_sec)
        self._window_size = max(1, window_size)
        self._retention_days = max(1, retention_days)
        self._default_interval_sec = max(1, default_interval_sec)
        self._default_timeout_ms = max(100, default_timeout_ms)
        self._default_latency_threshold_ms = max(1, default_latency_threshold_ms)
        self._heartbeat_sec = max(5.0, heartbeat_sec)
        self._task: asyncio.Task[None] | None = None
        self._stopping = asyncio.Event()
        self._next_due: dict[UUID, datetime] = {}
        self._next_retention_at = datetime.now(UTC)
        self._next_heartbeat_at = datetime.now(UTC)

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._stopping.clear()
        self._task = asyncio.create_task(self._run(), name="health-scheduler")

    async def stop(self) -> None:
        self._stopping.set()
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None

    async def _run(self) -> None:
        while not self._stopping.is_set():
            try:
                now = datetime.now(UTC)
                await self._sync_services_from_active_config()
                services = await self._repository.list_enabled_services()
                enabled_ids = {service.id for service in services}
                due_now_item_ids: list[str] = []
                emitted_count = 0
                retention_pruned = 0

                for service in services:
                    due_at = self._next_due.get(service.id, now)
                    if due_at > now:
                        continue
                    due_now_item_ids.append(service.item_id)
                    await self._bus_client.emit(
                        message=BusMessageV1(
                            type="health.check.request",
                            plugin_id="core.health",
                            payload=HealthCheckRequestedV1(
                                service_id=service.id,
                                item_id=service.item_id,
                                check_type=service.check_type,
                                target=service.target,
                                timeout_ms=service.timeout_ms,
                                latency_threshold_ms=service.latency_threshold_ms,
                                tls_verify=service.tls_verify,
                                window_size=self._window_size,
                                ts=now,
                            ).model_dump(mode="json"),
                        ),
                        routing_key="health.check.request",
                    )
                    self._next_due[service.id] = now + timedelta(seconds=service.interval_sec)
                    emitted_count += 1

                for service_id in list(self._next_due):
                    if service_id not in enabled_ids:
                        self._next_due.pop(service_id, None)

                if now >= self._next_retention_at:
                    cutoff = now - timedelta(days=self._retention_days)
                    retention_pruned = await self._repository.delete_samples_older_than(cutoff)
                    self._next_retention_at = now + timedelta(minutes=10)

                if now >= self._next_heartbeat_at:
                    schedule_preview = self._format_schedule_preview(now=now, services=services)
                    LOGGER.info(
                        "Health scheduler heartbeat enabled=%d due_now=%d emitted=%d pruned=%d next=%s",
                        len(services),
                        len(due_now_item_ids),
                        emitted_count,
                        retention_pruned,
                        schedule_preview,
                    )
                    if due_now_item_ids:
                        LOGGER.info(
                            "Health scheduler due items: %s",
                            ", ".join(due_now_item_ids[:20]),
                        )
                    self._next_heartbeat_at = now + timedelta(seconds=self._heartbeat_sec)
            except Exception:
                LOGGER.exception("Health scheduler tick failed")

            try:
                await asyncio.wait_for(self._stopping.wait(), timeout=self._tick_sec)
            except TimeoutError:
                continue

    async def _sync_services_from_active_config(self) -> None:
        snapshot = await self._config_repository.fetch_active()
        payload = snapshot.revision.payload if snapshot is not None else {}
        specs = extract_service_specs_from_config(
            config_payload=payload,
            default_interval_sec=self._default_interval_sec,
            default_timeout_ms=self._default_timeout_ms,
            default_latency_threshold_ms=self._default_latency_threshold_ms,
        )
        await self._repository.sync_services(specs)

    def _format_schedule_preview(self, *, now: datetime, services: Sequence[MonitoredService]) -> str:
        if not services:
            return "-"
        entries: list[tuple[int, str]] = []
        for service in services:
            due_at = self._next_due.get(service.id, now)
            remaining = max(0, int((due_at - now).total_seconds()))
            entries.append((remaining, service.item_id))
        entries.sort(key=lambda item: (item[0], item[1]))
        return ", ".join(f"{item_id}:{seconds}s" for seconds, item_id in entries[:8])


__all__ = ["HealthScheduler"]
