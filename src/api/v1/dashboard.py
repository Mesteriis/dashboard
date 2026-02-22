from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated, Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from config.container import AppContainer
from config.settings import AppSettings
from db.repositories import HealthSampleRepository, HealthSampleWrite
from scheme.dashboard import (
    AggregateStatus,
    ConfigVersion,
    DashboardConfig,
    DashboardHealthAggregates,
    DashboardHealthResponse,
    GroupHealthAggregate,
    HealthHistoryPoint,
    IframeItemConfig,
    IframeSourceResponse,
    ItemConfig,
    ItemHealthStatus,
    LanScanStateResponse,
    LanScanTriggerResponse,
    SaveConfigResponse,
    SubgroupHealthAggregate,
    ValidateRequest,
    ValidateResponse,
)
from service.config_service import DashboardConfigService, DashboardConfigValidationError
from service.lan_scan import LanScanService
from tools.auth import ProxyAccessSigner
from tools.health import probe_item_health
from tools.proxy import (
    PROXY_REQUEST_HEADERS,
    PROXY_RESPONSE_HEADERS,
    build_upstream_url,
    close_upstream_resources,
    filter_cookie_header,
    rewrite_location,
    rewrite_set_cookie,
)


def _validation_exception(exc: DashboardConfigValidationError) -> HTTPException:
    return HTTPException(status_code=422, detail=[issue.model_dump() for issue in exc.issues])


def get_container(request: Request) -> AppContainer:
    container = getattr(request.app.state, "container", None)
    if not isinstance(container, AppContainer):
        raise HTTPException(status_code=500, detail="Application container is not configured")
    return container


def get_settings(container: Annotated[AppContainer, Depends(get_container)]) -> AppSettings:
    return container.settings


def get_config_service(container: Annotated[AppContainer, Depends(get_container)]) -> DashboardConfigService:
    return container.config_service


def get_lan_scan_service(container: Annotated[AppContainer, Depends(get_container)]) -> LanScanService:
    return container.lan_scan_service


def get_proxy_signer(container: Annotated[AppContainer, Depends(get_container)]) -> ProxyAccessSigner:
    return container.proxy_signer


def get_health_sample_repository(
    container: Annotated[AppContainer, Depends(get_container)],
) -> HealthSampleRepository:
    return container.health_sample_repository


SettingsDep = Annotated[AppSettings, Depends(get_settings)]
ConfigServiceDep = Annotated[DashboardConfigService, Depends(get_config_service)]
LanScanServiceDep = Annotated[LanScanService, Depends(get_lan_scan_service)]
ProxySignerDep = Annotated[ProxyAccessSigner, Depends(get_proxy_signer)]
HealthSampleRepositoryDep = Annotated[HealthSampleRepository, Depends(get_health_sample_repository)]
HealthLevel = Literal["online", "degraded", "down", "unknown", "indirect_failure"]
DependencyResolution = tuple[HealthLevel, str | None, str | None]
_HEALTH_HISTORY_BY_ITEM: dict[str, deque[HealthHistoryPoint]] = {}
CONFIG_CACHE_CONTROL = "private, max-age=0, must-revalidate"
HEALTH_CACHE_CONTROL = "private, max-age=2, stale-while-revalidate=8"


def _config_etag(version: ConfigVersion) -> str:
    return f'"cfg-{version.sha256}"'


def _if_none_match_matches(value: str | None, current_etag: str) -> bool:
    if not value:
        return False

    for candidate in value.split(","):
        token = candidate.strip()
        if token == "*":
            return True
        if token == current_etag:
            return True
        if token.startswith("W/") and token[2:] == current_etag:
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
                {
                    dependency_id
                    for dependency_id in item.depends_on
                    if dependency_id not in items_by_id
                }
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
            subgroup_statuses = [
                statuses_by_id[item.id]
                for item in subgroup.items
                if item.id in statuses_by_id
            ]
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


dashboard_router = APIRouter(prefix="/api/v1")


@dashboard_router.get("/dashboard/config", response_model=DashboardConfig)
async def get_dashboard_config(
    request: Request,
    response: Response,
    config_service: ConfigServiceDep,
) -> DashboardConfig | Response:
    try:
        version = config_service.get_version()
        etag = _config_etag(version)

        if _if_none_match_matches(request.headers.get("if-none-match"), etag):
            return Response(
                status_code=304,
                headers={
                    "etag": etag,
                    "cache-control": CONFIG_CACHE_CONTROL,
                },
            )

        config = config_service.load()
    except DashboardConfigValidationError as exc:
        raise _validation_exception(exc) from exc

    response.headers["etag"] = etag
    response.headers["cache-control"] = CONFIG_CACHE_CONTROL
    return config


@dashboard_router.get("/dashboard/version", response_model=ConfigVersion)
async def get_dashboard_config_version(config_service: ConfigServiceDep) -> ConfigVersion:
    try:
        return config_service.get_version()
    except DashboardConfigValidationError as exc:
        raise _validation_exception(exc) from exc


@dashboard_router.get("/dashboard/errors")
async def get_dashboard_last_errors(config_service: ConfigServiceDep) -> dict[str, list[dict[str, str]]]:
    return {"issues": [issue.model_dump() for issue in config_service.last_issues]}


@dashboard_router.post("/dashboard/validate", response_model=ValidateResponse)
async def validate_dashboard_yaml(payload: ValidateRequest, config_service: ConfigServiceDep) -> ValidateResponse:
    config, issues = config_service.validate_yaml(payload.yaml)
    return ValidateResponse(valid=not issues, issues=issues, config=config)


@dashboard_router.put("/dashboard/config", response_model=SaveConfigResponse)
async def save_dashboard_config(
    payload: DashboardConfig,
    config_service: ConfigServiceDep,
) -> SaveConfigResponse:
    try:
        state = config_service.save(payload.model_dump(mode="json", exclude_none=True), source="api")
        return SaveConfigResponse(config=state.config, version=state.version)
    except DashboardConfigValidationError as exc:
        raise _validation_exception(exc) from exc


@dashboard_router.get("/dashboard/config/backup")
async def download_dashboard_config_backup(config_service: ConfigServiceDep) -> Response:
    try:
        backup_yaml = config_service.export_yaml()
    except DashboardConfigValidationError as exc:
        raise _validation_exception(exc) from exc

    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return Response(
        content=backup_yaml,
        media_type="application/x-yaml",
        headers={
            "content-disposition": f'attachment; filename=\"dashboard-backup-{timestamp}.yaml\"',
            "cache-control": CONFIG_CACHE_CONTROL,
        },
    )


@dashboard_router.post("/dashboard/config/restore", response_model=SaveConfigResponse)
async def restore_dashboard_config(
    payload: ValidateRequest,
    config_service: ConfigServiceDep,
) -> SaveConfigResponse:
    try:
        state = config_service.import_yaml(payload.yaml, source="restore")
        return SaveConfigResponse(config=state.config, version=state.version)
    except DashboardConfigValidationError as exc:
        raise _validation_exception(exc) from exc


@dashboard_router.get("/dashboard/health", response_model=DashboardHealthResponse)
async def get_dashboard_health(
    config_service: ConfigServiceDep,
    settings: SettingsDep,
    health_sample_repository: HealthSampleRepositoryDep,
    response: Response,
    item_id: Annotated[list[str] | None, Query()] = None,
) -> DashboardHealthResponse:
    try:
        config = config_service.load()
    except DashboardConfigValidationError as exc:
        raise _validation_exception(exc) from exc

    all_items = [
        item
        for group in config.groups
        for subgroup in group.subgroups
        for item in subgroup.items
    ]

    items_by_id = {item.id: item for item in all_items}
    _prune_health_history(
        set(items_by_id),
        health_sample_repository=health_sample_repository,
    )
    requested_ids: set[str] | None = None
    probe_ids: set[str] | None = None

    if item_id:
        requested_ids = set(item_id)
        probe_ids = _expand_requested_with_dependencies(requested_ids, items_by_id)

    items_to_probe = all_items if probe_ids is None else [item for item in all_items if item.id in probe_ids]

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
                for item in items_to_probe
            ]
        )

    statuses_by_id = {status.item_id: status for status in statuses}
    _apply_dependency_awareness(items_to_probe, statuses_by_id)
    _record_health_history(
        statuses_by_id=statuses_by_id,
        max_points=_health_history_size(settings),
        health_sample_repository=health_sample_repository,
    )

    if requested_ids is not None:
        statuses = [
            statuses_by_id[item.id]
            for item in all_items
            if item.id in requested_ids and item.id in statuses_by_id
        ]
    else:
        statuses = [statuses_by_id[item.id] for item in all_items if item.id in statuses_by_id]

    _attach_health_history(statuses)
    status_subset_by_id = {status.item_id: status for status in statuses}
    aggregates = _build_health_aggregates(
        config=config,
        statuses_by_id=status_subset_by_id,
    )
    response.headers["cache-control"] = HEALTH_CACHE_CONTROL
    return DashboardHealthResponse(items=statuses, aggregates=aggregates)


@dashboard_router.get("/dashboard/iframe/{item_id}/source", response_model=IframeSourceResponse)
async def get_iframe_source(
    item_id: str,
    response: Response,
    request: Request,
    config_service: ConfigServiceDep,
    settings: SettingsDep,
    proxy_signer: ProxySignerDep,
) -> IframeSourceResponse:
    item = _load_iframe_item(item_id, config_service)

    if item.auth_profile:
        src = f"/api/v1/dashboard/iframe/{item_id}/proxy"
        proxy_token = proxy_signer.build_token(item_id=item_id)
        if proxy_token:
            response.set_cookie(
                key=settings.proxy_access_cookie,
                value=proxy_token,
                max_age=settings.proxy_token_ttl_sec,
                httponly=True,
                secure=request.url.scheme == "https",
                samesite="lax",
                path=src,
            )
        return IframeSourceResponse(
            item_id=item.id,
            src=src,
            proxied=True,
            auth_profile=item.auth_profile,
        )

    return IframeSourceResponse(item_id=item.id, src=str(item.url), proxied=False, auth_profile=None)


@dashboard_router.get("/dashboard/lan/state", response_model=LanScanStateResponse)
async def get_lan_scan_state(lan_scan_service: LanScanServiceDep) -> LanScanStateResponse:
    return lan_scan_service.state()


@dashboard_router.post("/dashboard/lan/run", response_model=LanScanTriggerResponse)
async def run_lan_scan(
    lan_scan_service: LanScanServiceDep,
) -> LanScanTriggerResponse:
    accepted = await lan_scan_service.trigger_scan()
    state = lan_scan_service.state()
    if accepted:
        message = "Сканирование запущено"
    elif state.queued:
        message = "Сканирование уже выполняется, следующий запуск поставлен в очередь"
    else:
        message = "Сканирование отключено"
    return LanScanTriggerResponse(
        accepted=accepted,
        message=message,
        state=state,
    )


@dashboard_router.api_route(
    "/dashboard/iframe/{item_id}/proxy",
    methods=["GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"],
)
@dashboard_router.api_route(
    "/dashboard/iframe/{item_id}/proxy/{proxy_path:path}",
    methods=["GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy_iframe(
    request: Request,
    item_id: str,
    config_service: ConfigServiceDep,
    settings: SettingsDep,
    proxy_signer: ProxySignerDep,
    proxy_path: str = "",
) -> Response:
    item = _load_iframe_item(item_id, config_service)

    try:
        auth_headers, auth_query = config_service.build_proxy_request(item)
    except DashboardConfigValidationError as exc:
        raise _validation_exception(exc) from exc

    if item.auth_profile and not proxy_signer.is_valid(
        token=request.cookies.get(settings.proxy_access_cookie),
        item_id=item_id,
    ):
        raise HTTPException(status_code=401, detail="Proxy access denied")

    upstream_url = build_upstream_url(
        base_url=str(item.url),
        proxy_path=proxy_path,
        request_query=list(request.query_params.multi_items()),
        auth_query=auth_query,
    )

    outgoing_headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() in PROXY_REQUEST_HEADERS
    }
    outgoing_headers.update(auth_headers)

    filtered_cookie_header = filter_cookie_header(
        outgoing_headers.get("cookie"),
        blocked_cookie_names={settings.proxy_access_cookie} if settings.proxy_access_cookie else set(),
    )
    if filtered_cookie_header:
        outgoing_headers["cookie"] = filtered_cookie_header
    else:
        outgoing_headers.pop("cookie", None)

    body = await request.body()

    client = httpx.AsyncClient(follow_redirects=False, timeout=20.0)
    upstream_request = client.build_request(
        request.method,
        upstream_url,
        headers=outgoing_headers,
        content=body,
    )
    try:
        upstream_response = await client.send(upstream_request, stream=True)
    except httpx.HTTPError as exc:
        await client.aclose()
        raise HTTPException(status_code=502, detail=f"Upstream request failed: {exc}") from exc

    response_headers = {
        key: value
        for key, value in upstream_response.headers.items()
        if key.lower() in PROXY_RESPONSE_HEADERS
    }

    if "location" in response_headers:
        response_headers["location"] = rewrite_location(
            location=response_headers["location"],
            item_url=str(item.url),
            item_id=item_id,
        )

    async def _stream_body() -> AsyncIterator[bytes]:
        async for chunk in upstream_response.aiter_raw():
            yield chunk

    response = StreamingResponse(
        _stream_body(),
        status_code=upstream_response.status_code,
        headers=response_headers,
        background=BackgroundTask(close_upstream_resources, upstream_response, client),
    )

    for cookie in upstream_response.headers.get_list("set-cookie"):
        for rewritten_cookie in rewrite_set_cookie(cookie, item_id):
            response.headers.append("set-cookie", rewritten_cookie)

    return response


__all__ = ["dashboard_router"]
