from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

import structlog
from depens.v1.dashboard_deps import LanScanServiceDep
from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from scheme.dashboard import (
    LanScanStateResponse,
    LanScanStreamEvent,
    LanScanTriggerResponse,
)

lan_router = APIRouter(prefix="/dashboard", tags=["lan-scan"])
logger = structlog.get_logger()
LAN_STREAM_KEEPALIVE_SEC = 15.0


def _format_sse_message(event: LanScanStreamEvent) -> str:
    payload = event.model_dump(mode="json")
    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return (
        f"id: {event.revision}\n"
        f"event: {event.type}\n"
        f"data: {serialized}\n\n"
    )


@lan_router.get(
    "/lan/state",
    response_model=LanScanStateResponse,
    summary="Get LAN scan state",
    description="Returns the current LAN scan state including running status, last result, and error information.",
)
async def get_lan_scan_state(lan_scan_service: LanScanServiceDep) -> LanScanStateResponse:
    state = lan_scan_service.state()
    await logger.ainfo(
        f"lan_scan_state_api enabled={state.enabled} running={state.running} queued={state.queued}",
        enabled=state.enabled,
        running=state.running,
        queued=state.queued,
    )
    return state


@lan_router.post(
    "/lan/run",
    response_model=LanScanTriggerResponse,
    summary="Trigger LAN scan",
    description="Triggers a new LAN scan. Returns immediately with queued status if scan is already running.",
    responses={
        200: {"description": "Scan triggered or queued"},
    },
)
async def run_lan_scan(
    lan_scan_service: LanScanServiceDep,
) -> LanScanTriggerResponse:
    await logger.ainfo("lan_scan_trigger_api incoming")
    accepted = await lan_scan_service.trigger_scan()
    state = lan_scan_service.state()
    if accepted:
        message = "Сканирование запущено"
    elif state.queued:
        message = "Сканирование уже выполняется, следующий запуск поставлен в очередь"
    else:
        message = "Сканирование отключено"
    await logger.ainfo(
        (
            "lan_scan_trigger_api "
            f"accepted={accepted} enabled={state.enabled} "
            f"running={state.running} queued={state.queued}"
        ),
        accepted=accepted,
        enabled=state.enabled,
        running=state.running,
        queued=state.queued,
    )
    return LanScanTriggerResponse(
        accepted=accepted,
        message=message,
        state=state,
    )


@lan_router.get(
    "/lan/stream",
    summary="Stream LAN scan updates (SSE)",
    description=(
        "Server-Sent Events stream for incremental LAN scan updates. "
        "Sends host-level events as they are discovered."
    ),
    responses={
        200: {"description": "SSE stream", "content": {"text/event-stream": {}}},
    },
)
async def stream_lan_scan(
    request: Request,
    lan_scan_service: LanScanServiceDep,
    once: bool = Query(default=False, description="Return only one event and close"),
) -> StreamingResponse:
    queue = lan_scan_service.subscribe_events()

    async def _stream() -> AsyncIterator[str]:
        try:
            while True:
                if await request.is_disconnected():
                    return
                try:
                    event = await asyncio.wait_for(
                        queue.get(),
                        timeout=LAN_STREAM_KEEPALIVE_SEC,
                    )
                except TimeoutError:
                    yield ": keepalive\n\n"
                    continue

                yield _format_sse_message(event)
                if once:
                    return
        finally:
            lan_scan_service.unsubscribe_events(queue)

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "cache-control": "no-cache, no-transform",
            "connection": "keep-alive",
            "x-accel-buffering": "no",
        },
    )


__all__ = ["lan_router"]
