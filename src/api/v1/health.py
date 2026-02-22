from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import StreamingResponse

import depens.v1.health_runtime as health_runtime
from depens.v1.dashboard_deps import ConfigServiceDep, HealthSampleRepositoryDep, SettingsDep, validation_exception
from scheme.dashboard import DashboardHealthResponse
from service.config_service import DashboardConfigValidationError

health_router = APIRouter(prefix="/dashboard", tags=["dashboard-health"])


@health_router.get(
    "/health",
    response_model=DashboardHealthResponse,
    summary="Get service health status",
    description=(
        "Returns current health status for all services or filtered by item IDs. "
        "Includes aggregates by group and subgroup."
    ),
)
async def get_dashboard_health(
    config_service: ConfigServiceDep,
    settings: SettingsDep,
    health_sample_repository: HealthSampleRepositoryDep,
    response: Response,
    item_id: Annotated[
        list[str] | None,
        Query(description="Filter by item IDs (can be specified multiple times)"),
    ] = None,
) -> DashboardHealthResponse:
    try:
        snapshot = await health_runtime._ensure_health_snapshot_for_request(
            config_service=config_service,
            settings=settings,
            health_sample_repository=health_sample_repository,
        )
    except DashboardConfigValidationError as exc:
        raise validation_exception(exc) from exc

    response.headers["cache-control"] = health_runtime.HEALTH_CACHE_CONTROL
    return health_runtime._build_health_response_from_snapshot(snapshot=snapshot, item_ids=item_id)


@health_router.get(
    "/health/stream",
    summary="Stream service health updates (SSE)",
    description=(
        "Server-Sent Events stream for real-time health status updates. Reconnects automatically on connection loss."
    ),
    responses={
        200: {"description": "SSE stream", "content": {"text/event-stream": {}}},
    },
)
async def stream_dashboard_health(
    request: Request,
    config_service: ConfigServiceDep,
    settings: SettingsDep,
    health_sample_repository: HealthSampleRepositoryDep,
    item_id: Annotated[
        list[str] | None,
        Query(description="Filter by item IDs"),
    ] = None,
    once: Annotated[
        bool,
        Query(description="Return only initial snapshot and close"),
    ] = False,
) -> StreamingResponse:
    try:
        snapshot = await health_runtime._ensure_health_snapshot_for_request(
            config_service=config_service,
            settings=settings,
            health_sample_repository=health_sample_repository,
        )
    except DashboardConfigValidationError as exc:
        raise validation_exception(exc) from exc

    keepalive_sec = max(2.0, settings.health_sse_keepalive_sec)

    async def _stream() -> AsyncIterator[str]:
        local_revision = snapshot.revision
        initial_payload = health_runtime._build_health_response_from_snapshot(snapshot=snapshot, item_ids=item_id)
        yield health_runtime._format_sse_snapshot_message(payload=initial_payload, revision=local_revision)
        if once:
            return

        while True:
            if await request.is_disconnected():
                return

            revision = await health_runtime._HEALTH_RUNTIME.wait_for_revision_after(
                revision=local_revision,
                timeout_sec=keepalive_sec,
            )
            if await request.is_disconnected():
                return

            if revision <= local_revision:
                # Keep idle streams alive through reverse proxies.
                yield ": keepalive\n\n"
                continue

            current = health_runtime._HEALTH_RUNTIME.snapshot()
            if current is None:
                try:
                    current = await health_runtime._ensure_health_snapshot_for_request(
                        config_service=config_service,
                        settings=settings,
                        health_sample_repository=health_sample_repository,
                    )
                except DashboardConfigValidationError:
                    continue

            local_revision = current.revision
            payload = health_runtime._build_health_response_from_snapshot(snapshot=current, item_ids=item_id)
            yield health_runtime._format_sse_snapshot_message(payload=payload, revision=local_revision)

    return StreamingResponse(
        _stream(),
        media_type=health_runtime.HEALTH_STREAM_MEDIA_TYPE,
        headers={
            "cache-control": health_runtime.HEALTH_STREAM_CACHE_CONTROL,
            "connection": "keep-alive",
            "x-accel-buffering": "no",
        },
    )


__all__ = ["health_router"]
