from __future__ import annotations

from fastapi import APIRouter

from depens.v1.dashboard_deps import LanScanServiceDep
from scheme.dashboard import LanScanStateResponse, LanScanTriggerResponse

lan_router = APIRouter(prefix="/dashboard", tags=["lan-scan"])


@lan_router.get(
    "/lan/state",
    response_model=LanScanStateResponse,
    summary="Get LAN scan state",
    description="Returns the current LAN scan state including running status, last result, and error information.",
)
async def get_lan_scan_state(lan_scan_service: LanScanServiceDep) -> LanScanStateResponse:
    return lan_scan_service.state()


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


__all__ = ["lan_router"]
