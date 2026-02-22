from __future__ import annotations

import asyncio
from collections import deque
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

import httpx
import structlog
from config.container import AppContainer
from config.settings import AppSettings
from db.repositories import HealthSampleRepository, HealthSampleWrite
from depens.v1.dashboard_deps import validation_exception as _validation_exception
from fastapi import HTTPException
from scheme.dashboard import (
    AggregateStatus,
    ConfigVersion,
    DashboardConfig,
    DashboardHealthAggregates,
    DashboardHealthResponse,
    GroupHealthAggregate,
    HealthHistoryPoint,
    IframeItemConfig,
    ItemConfig,
    ItemHealthStatus,
    SubgroupHealthAggregate,
)
from service.config_service import DashboardConfigService, DashboardConfigValidationError
from tools.health import probe_item_health

logger = structlog.get_logger()

HealthLevel = Literal["online", "degraded", "down", "unknown", "indirect_failure"]
DependencyResolution = tuple[HealthLevel, str | None, str | None]
_HEALTH_HISTORY_BY_ITEM: dict[str, deque[HealthHistoryPoint]] = {}
CONFIG_CACHE_CONTROL = "private, max-age=0, must-revalidate"
HEALTH_CACHE_CONTROL = "private, max-age=2, stale-while-revalidate=8"
HEALTH_STREAM_CACHE_CONTROL = "no-cache"
HEALTH_STREAM_MEDIA_TYPE = "text/event-stream"


@dataclass(frozen=True)
class HealthSnapshot:
    config: DashboardConfig
    statuses_by_id: dict[str, ItemHealthStatus]
    updated_at: datetime
    revision: int


class HealthRuntime:
    def __init__(self) -> None:
        self._snapshot: HealthSnapshot | None = None
        self._snapshot_lock = asyncio.Lock()
        self._revision_condition = asyncio.Condition()
        self._refresh_task: asyncio.Task[None] | None = None
        self._stop_event: asyncio.Event | None = None
        self._wake_event: asyncio.Event | None = None

    def reset_for_tests(self) -> None:
        if self._refresh_task is not None:
            raise RuntimeError("Health runtime cannot be reset while background loop is running")
        self._snapshot = None

    async def start(
        self,
        *,
        config_service: DashboardConfigService,
        settings: AppSettings,
        health_sample_repository: HealthSampleRepository,
    ) -> None:
        if settings.health_refresh_sec <= 0:
            return
        if self._refresh_task is not None and not self._refresh_task.done():
            return

        self._stop_event = asyncio.Event()
        self._wake_event = asyncio.Event()
        self._refresh_task = asyncio.create_task(
            self._run_refresh_loop(
                config_service=config_service,
                settings=settings,
                health_sample_repository=health_sample_repository,
            ),
            name="dashboard-health-refresh-loop",
        )

    async def stop(self) -> None:
        task = self._refresh_task
        if task is None:
            return

        if self._stop_event is not None:
            self._stop_event.set()
        if self._wake_event is not None:
            self._wake_event.set()
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        self._refresh_task = None
        self._stop_event = None
        self._wake_event = None

    async def request_refresh(self) -> None:
        if self._wake_event is not None:
            self._wake_event.set()

    def snapshot(self) -> HealthSnapshot | None:
        return self._snapshot

    async def ensure_snapshot(
        self,
        *,
        config_service: DashboardConfigService,
        settings: AppSettings,
        health_sample_repository: HealthSampleRepository,
        force_refresh: bool,
    ) -> HealthSnapshot:
        current = self._snapshot
        snapshot_stale = (
            current is not None
            and settings.health_refresh_sec > 0
            and ((datetime.now(UTC) - current.updated_at).total_seconds() > settings.health_refresh_sec * 3)
        )

        if force_refresh or current is None or snapshot_stale:
            return await self.refresh_snapshot(
                config_service=config_service,
                settings=settings,
                health_sample_repository=health_sample_repository,
            )
        return current

    async def refresh_snapshot(
        self,
        *,
        config_service: DashboardConfigService,
        settings: AppSettings,
        health_sample_repository: HealthSampleRepository,
    ) -> HealthSnapshot:
        async with self._snapshot_lock:
            config, statuses_by_id = await _probe_health_snapshot(
                config_service=config_service,
                settings=settings,
                health_sample_repository=health_sample_repository,
            )
            current_revision = 0 if self._snapshot is None else self._snapshot.revision
            snapshot = HealthSnapshot(
                config=config,
                statuses_by_id={item_id: status.model_copy(deep=True) for item_id, status in statuses_by_id.items()},
                updated_at=datetime.now(UTC),
                revision=current_revision + 1,
            )
            self._snapshot = snapshot
            async with self._revision_condition:
                self._revision_condition.notify_all()
            return snapshot

    async def wait_for_revision_after(self, *, revision: int, timeout_sec: float) -> int:
        current = self._snapshot
        if current is not None and current.revision > revision:
            return current.revision

        timeout = max(0.1, timeout_sec)
        async with self._revision_condition:
            with suppress(TimeoutError):
                await asyncio.wait_for(
                    self._revision_condition.wait_for(
                        lambda: self._snapshot is not None and self._snapshot.revision > revision
                    ),
                    timeout=timeout,
                )

        latest = self._snapshot
        return 0 if latest is None else latest.revision

    async def _run_refresh_loop(
        self,
        *,
        config_service: DashboardConfigService,
        settings: AppSettings,
        health_sample_repository: HealthSampleRepository,
    ) -> None:
        if self._stop_event is None or self._wake_event is None:
            return

        from datetime import timedelta

        refresh_timeout = max(0.2, settings.health_refresh_sec)
        retention_days = max(1, settings.health_samples_retention_days)
        retention_cutoff = datetime.now(UTC) - timedelta(days=retention_days)
        last_retention_run = datetime.now(UTC)

        await logger.ainfo(
            "health_refresh_loop_started",
            refresh_sec=refresh_timeout,
            retention_days=retention_days,
        )
        while not self._stop_event.is_set():
            try:
                await self.refresh_snapshot(
                    config_service=config_service,
                    settings=settings,
                    health_sample_repository=health_sample_repository,
                )

                now = datetime.now(UTC)
                if (now - last_retention_run).total_seconds() > 3600:
                    deleted = health_sample_repository.delete_samples_older_than(retention_cutoff)
                    last_retention_run = now
                    retention_cutoff = now - timedelta(days=retention_days)
                    if deleted > 0:
                        await logger.ainfo(
                            "health_samples_retention_applied",
                            deleted_count=deleted,
                            retention_days=retention_days,
                        )

            except DashboardConfigValidationError as exc:
                await logger.awarning(
                    "health_refresh_config_validation_error",
                    error=str(exc),
                )
            except Exception as exc:
                await logger.aerror(
                    "health_refresh_unexpected_error",
                    error=str(exc),
                    exc_info=True,
                )

            if self._stop_event.is_set():
                break

            try:
                await asyncio.wait_for(self._wake_event.wait(), timeout=refresh_timeout)
            except TimeoutError:
                continue
            finally:
                self._wake_event.clear()

        await logger.ainfo("health_refresh_loop_stopped")


_HEALTH_RUNTIME = HealthRuntime()


def _config_etag(version: ConfigVersion) -> str:
    return f'"cfg-{version.sha256}"'


def _if_none_match_matches(value: str | None, current_etag: str) -> bool:
    if not value:
        return False

    for candidate in value.split(","):
        etag_candidate = candidate.strip()
        if etag_candidate == "*":
            return True
        if etag_candidate == current_etag:
            return True
        if etag_candidate.startswith("W/") and etag_candidate[2:] == current_etag:
            return True
    return False


def _load_iframe_item(item_id: str, config_service: DashboardConfigService) -> IframeItemConfig:
    try:
        item = config_service.get_iframe_item(item_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown item id: {item_id}") from exc
    except TypeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DashboardConfigValidationError as exc:
        raise _validation_exception(exc) from exc
    return item


def _status_level(status: ItemHealthStatus) -> HealthLevel:
    level = str(status.level or "").lower()
    if level == "online":
        return "online"
    if level == "degraded":
        return "degraded"
    if level == "down":
        return "down"
    if level == "unknown":
        return "unknown"
    if level == "indirect_failure":
        return "indirect_failure"
    if status.ok:
        return "online"
    return "down"


def _coerce_health_level(level: str | None) -> HealthLevel:
    normalized = str(level or "").lower()
    if normalized == "online":
        return "online"
    if normalized == "degraded":
        return "degraded"
    if normalized == "down":
        return "down"
    if normalized == "indirect_failure":
        return "indirect_failure"
    return "unknown"


def _expand_requested_with_dependencies(requested_ids: set[str], items_by_id: dict[str, ItemConfig]) -> set[str]:
    expanded: set[str] = set()
    stack = list(requested_ids)

    while stack:
        item_id = stack.pop()
        if item_id in expanded:
            continue
        expanded.add(item_id)
        item = items_by_id.get(item_id)
        if not item:
            continue
        for dependency_id in item.depends_on:
            if dependency_id not in expanded:
                stack.append(dependency_id)

    return expanded


def _apply_dependency_awareness(items: list[ItemConfig], statuses_by_id: dict[str, ItemHealthStatus]) -> None:
    items_by_id = {item.id: item for item in items}
    memo: dict[str, DependencyResolution] = {}
    visiting: set[str] = set()

    def resolve(item_id: str) -> DependencyResolution:
        if item_id in memo:
            return memo[item_id]

        status = statuses_by_id.get(item_id)
        if not status:
            result: DependencyResolution = ("unknown", None, None)
            memo[item_id] = result
            return result

        if item_id in visiting:
            result = ("degraded", "dependency_cycle", "Dependency cycle detected")
            memo[item_id] = result
            return result

        item = items_by_id.get(item_id)
        base_level = _status_level(status)
        if not item or base_level == "down":
            result = (base_level, status.reason, status.error)
            memo[item_id] = result
            return result

        visiting.add(item_id)
        try:
            missing_dependencies = sorted(
                {dependency_id for dependency_id in item.depends_on if dependency_id not in items_by_id}
            )
            if missing_dependencies:
                result = (
                    "degraded",
                    "missing_dependency",
                    f"Missing dependency: {', '.join(missing_dependencies)}",
                )
                memo[item_id] = result
                return result

            for dependency_id in item.depends_on:
                dependency_level, dependency_reason, _dependency_error = resolve(dependency_id)

                if dependency_reason == "dependency_cycle":
                    result = ("degraded", "dependency_cycle", "Dependency cycle detected")
                    memo[item_id] = result
                    return result

                if dependency_level in {"down", "indirect_failure"}:
                    result = ("indirect_failure", "indirect_dependency", f"Blocked by dependency: {dependency_id}")
                    memo[item_id] = result
                    return result

            result = (base_level, status.reason, status.error)
            memo[item_id] = result
            return result
        finally:
            visiting.discard(item_id)

    for item in items:
        status = statuses_by_id.get(item.id)
        if not status:
            continue
        level, reason, error = resolve(item.id)
        status.level = level
        status.reason = reason
        status.ok = level == "online"

        if reason in {"missing_dependency", "dependency_cycle", "indirect_dependency"}:
            status.error = error
            status.error_kind = None


def _build_aggregate_status(statuses: list[ItemHealthStatus]) -> AggregateStatus:
    counts = {
        "online": 0,
        "degraded": 0,
        "down": 0,
        "unknown": 0,
        "indirect_failure": 0,
    }

    for status in statuses:
        item_level = _status_level(status)
        counts[item_level] += 1

    total = len(statuses)
    level: Literal["online", "degraded", "down", "unknown"] = "unknown"
    if total > 0:
        if counts["down"] > 0:
            level = "down"
        elif counts["degraded"] > 0 or counts["indirect_failure"] > 0:
            level = "degraded"
        elif counts["online"] == total:
            level = "online"

    return AggregateStatus(
        total=total,
        online=counts["online"],
        degraded=counts["degraded"],
        down=counts["down"],
        unknown=counts["unknown"],
        indirect_failure=counts["indirect_failure"],
        level=level,
    )


def _build_health_aggregates(
    *,
    config: DashboardConfig,
    statuses_by_id: dict[str, ItemHealthStatus],
) -> DashboardHealthAggregates:
    group_aggregates: list[GroupHealthAggregate] = []
    subgroup_aggregates: list[SubgroupHealthAggregate] = []

    for group in config.groups:
        group_statuses: list[ItemHealthStatus] = []

        for subgroup in group.subgroups:
            subgroup_statuses = [statuses_by_id[item.id] for item in subgroup.items if item.id in statuses_by_id]
            if not subgroup_statuses:
                continue

            subgroup_aggregates.append(
                SubgroupHealthAggregate(
                    group_id=group.id,
                    subgroup_id=subgroup.id,
                    status=_build_aggregate_status(subgroup_statuses),
                )
            )
            group_statuses.extend(subgroup_statuses)

        if group_statuses:
            group_aggregates.append(
                GroupHealthAggregate(
                    group_id=group.id,
                    status=_build_aggregate_status(group_statuses),
                )
            )

    return DashboardHealthAggregates(groups=group_aggregates, subgroups=subgroup_aggregates)


def _health_history_size(settings: AppSettings) -> int:
    return max(1, settings.health_history_size)


def _record_health_history(
    *,
    statuses_by_id: dict[str, ItemHealthStatus],
    max_points: int,
    health_sample_repository: HealthSampleRepository | None = None,
) -> None:
    timestamp = datetime.now(UTC)
    persisted_samples: list[HealthSampleWrite] = []

    for status in statuses_by_id.values():
        history_buffer = _HEALTH_HISTORY_BY_ITEM.get(status.item_id)
        if history_buffer is None:
            history_buffer = deque(maxlen=max_points)
            _HEALTH_HISTORY_BY_ITEM[status.item_id] = history_buffer
        elif history_buffer.maxlen != max_points:
            history_buffer = deque(history_buffer, maxlen=max_points)
            _HEALTH_HISTORY_BY_ITEM[status.item_id] = history_buffer

        history_buffer.append(
            HealthHistoryPoint(
                ts=timestamp,
                level=_status_level(status),
                latency_ms=status.latency_ms,
                status_code=status.status_code,
            )
        )
        persisted_samples.append(
            HealthSampleWrite(
                item_id=status.item_id,
                ts=timestamp,
                level=_status_level(status),
                latency_ms=status.latency_ms,
                status_code=status.status_code,
            )
        )

    if health_sample_repository is None:
        return
    try:
        health_sample_repository.append_samples(persisted_samples)
        health_sample_repository.trim_samples_per_item(
            item_ids=statuses_by_id.keys(),
            limit_per_item=max_points,
        )
    except Exception:
        # Health endpoint should still return live probe data even if persistence fails.
        return


def _attach_health_history(statuses: list[ItemHealthStatus]) -> None:
    for status in statuses:
        history_buffer = _HEALTH_HISTORY_BY_ITEM.get(status.item_id)
        status.history = list(history_buffer) if history_buffer else []


def _prune_health_history(
    valid_item_ids: set[str],
    *,
    health_sample_repository: HealthSampleRepository | None = None,
) -> None:
    stale_item_ids = [item_id for item_id in _HEALTH_HISTORY_BY_ITEM if item_id not in valid_item_ids]
    for item_id in stale_item_ids:
        _HEALTH_HISTORY_BY_ITEM.pop(item_id, None)

    if health_sample_repository is None:
        return
    try:
        health_sample_repository.delete_samples_not_in_item_ids(valid_item_ids)
    except Exception:
        return


def _hydrate_health_history_from_db(
    *,
    item_ids: set[str],
    max_points: int,
    health_sample_repository: HealthSampleRepository | None = None,
) -> None:
    if health_sample_repository is None:
        return

    missing_item_ids = {item_id for item_id in item_ids if item_id not in _HEALTH_HISTORY_BY_ITEM}
    if not missing_item_ids:
        return

    try:
        persisted = health_sample_repository.list_recent_by_item_ids(
            item_ids=missing_item_ids,
            limit_per_item=max_points,
        )
    except Exception:
        return

    for item_id, samples in persisted.items():
        buffer: deque[HealthHistoryPoint] = deque(maxlen=max_points)
        for sample in samples:
            buffer.append(
                HealthHistoryPoint(
                    ts=sample.ts,
                    level=_coerce_health_level(sample.level),
                    latency_ms=sample.latency_ms,
                    status_code=sample.status_code,
                )
            )
        _HEALTH_HISTORY_BY_ITEM[item_id] = buffer


def _all_config_items(config: DashboardConfig) -> list[ItemConfig]:
    return [item for group in config.groups for subgroup in group.subgroups for item in subgroup.items]


async def _probe_health_snapshot(
    *,
    config_service: DashboardConfigService,
    settings: AppSettings,
    health_sample_repository: HealthSampleRepository,
) -> tuple[DashboardConfig, dict[str, ItemHealthStatus]]:
    config = config_service.load()
    all_items = _all_config_items(config)
    items_by_id = {item.id: item for item in all_items}
    _prune_health_history(
        set(items_by_id),
        health_sample_repository=health_sample_repository,
    )
    _hydrate_health_history_from_db(
        item_ids=set(items_by_id),
        max_points=_health_history_size(settings),
        health_sample_repository=health_sample_repository,
    )

    semaphore = asyncio.Semaphore(max(1, settings.healthcheck_max_parallel))
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=max(0.2, settings.healthcheck_timeout_sec),
        verify=settings.healthcheck_verify_tls,
    ) as client:
        statuses = await asyncio.gather(
            *[
                probe_item_health(
                    item=item,
                    client=client,
                    semaphore=semaphore,
                    default_timeout_sec=settings.healthcheck_timeout_sec,
                )
                for item in all_items
            ]
        )

    statuses_by_id = {status.item_id: status for status in statuses}
    _apply_dependency_awareness(all_items, statuses_by_id)
    _record_health_history(
        statuses_by_id=statuses_by_id,
        max_points=_health_history_size(settings),
        health_sample_repository=health_sample_repository,
    )
    return config, statuses_by_id


def _build_health_response_from_snapshot(
    *,
    snapshot: HealthSnapshot,
    item_ids: list[str] | None = None,
) -> DashboardHealthResponse:
    all_items = _all_config_items(snapshot.config)
    requested_ids = set(item_ids or [])

    if requested_ids:
        statuses = [
            snapshot.statuses_by_id[item.id].model_copy(deep=True)
            for item in all_items
            if item.id in requested_ids and item.id in snapshot.statuses_by_id
        ]
    else:
        statuses = [
            snapshot.statuses_by_id[item.id].model_copy(deep=True)
            for item in all_items
            if item.id in snapshot.statuses_by_id
        ]

    _attach_health_history(statuses)
    status_subset_by_id = {status.item_id: status for status in statuses}
    aggregates = _build_health_aggregates(
        config=snapshot.config,
        statuses_by_id=status_subset_by_id,
    )
    return DashboardHealthResponse(items=statuses, aggregates=aggregates)


def _format_sse_snapshot_message(*, payload: DashboardHealthResponse, revision: int) -> str:
    body = payload.model_dump_json(exclude_none=True)
    return f"id: {revision}\nevent: snapshot\ndata: {body}\n\n"


async def _ensure_health_snapshot_for_request(
    *,
    config_service: DashboardConfigService,
    settings: AppSettings,
    health_sample_repository: HealthSampleRepository,
) -> HealthSnapshot:
    force_refresh = settings.health_refresh_sec <= 0
    return await _HEALTH_RUNTIME.ensure_snapshot(
        config_service=config_service,
        settings=settings,
        health_sample_repository=health_sample_repository,
        force_refresh=force_refresh,
    )


async def start_health_runtime(container: AppContainer) -> None:
    await _HEALTH_RUNTIME.start(
        config_service=container.config_service,
        settings=container.settings,
        health_sample_repository=container.health_sample_repository,
    )


async def stop_health_runtime() -> None:
    await _HEALTH_RUNTIME.stop()


def reset_health_runtime_state() -> None:
    _HEALTH_RUNTIME.reset_for_tests()
    _HEALTH_HISTORY_BY_ITEM.clear()


__all__ = [
    "CONFIG_CACHE_CONTROL",
    "HEALTH_CACHE_CONTROL",
    "HEALTH_STREAM_CACHE_CONTROL",
    "HEALTH_STREAM_MEDIA_TYPE",
    "_HEALTH_RUNTIME",
    "HealthRuntime",
    "HealthSnapshot",
    "_build_health_response_from_snapshot",
    "_config_etag",
    "_ensure_health_snapshot_for_request",
    "_format_sse_snapshot_message",
    "_if_none_match_matches",
    "_load_iframe_item",
    "httpx",
    "probe_item_health",
    "reset_health_runtime_state",
    "start_health_runtime",
    "stop_health_runtime",
]
