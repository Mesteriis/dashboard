from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from config.container import AppContainer
from config.settings import ADMIN_TOKEN_HEADER, AppSettings
from scheme.dashboard import (
    ConfigVersion,
    DashboardConfig,
    DashboardHealthResponse,
    IframeItemConfig,
    IframeSourceResponse,
    LanScanStateResponse,
    LanScanTriggerResponse,
    SaveConfigResponse,
    ValidateRequest,
    ValidateResponse,
)
from service.config_service import DashboardConfigService, DashboardConfigValidationError
from service.lan_scan import LanScanService
from tools.auth import AuthFailure, ProxyAccessSigner, ensure_admin_token
from tools.health import probe_item_health
from tools.proxy import (
    PROXY_REQUEST_HEADERS,
    PROXY_RESPONSE_HEADERS,
    build_upstream_url,
    close_upstream_resources,
    rewrite_location,
    rewrite_set_cookie,
)


def _validation_exception(exc: DashboardConfigValidationError) -> HTTPException:
    return HTTPException(status_code=422, detail=[issue.model_dump() for issue in exc.issues])


def _auth_exception(exc: AuthFailure) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


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


SettingsDep = Annotated[AppSettings, Depends(get_settings)]
ConfigServiceDep = Annotated[DashboardConfigService, Depends(get_config_service)]
LanScanServiceDep = Annotated[LanScanService, Depends(get_lan_scan_service)]
ProxySignerDep = Annotated[ProxyAccessSigner, Depends(get_proxy_signer)]
AdminTokenHeaderDep = Annotated[str | None, Header(alias=ADMIN_TOKEN_HEADER)]


def require_admin_token(
    settings: SettingsDep,
    token: AdminTokenHeaderDep = None,
) -> None:
    try:
        ensure_admin_token(token=token, admin_token=settings.admin_token)
    except AuthFailure as exc:
        raise _auth_exception(exc) from exc


AdminAuthDep = Annotated[None, Depends(require_admin_token)]


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


dashboard_router = APIRouter(prefix="/api/v1")


@dashboard_router.get("/dashboard/config", response_model=DashboardConfig)
async def get_dashboard_config(config_service: ConfigServiceDep) -> DashboardConfig:
    try:
        return config_service.load()
    except DashboardConfigValidationError as exc:
        raise _validation_exception(exc) from exc


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
    _auth: AdminAuthDep,
    config_service: ConfigServiceDep,
) -> SaveConfigResponse:
    del _auth
    try:
        state = config_service.save(payload.model_dump(mode="json", exclude_none=True))
        return SaveConfigResponse(config=state.config, version=state.version)
    except DashboardConfigValidationError as exc:
        raise _validation_exception(exc) from exc


@dashboard_router.get("/dashboard/health", response_model=DashboardHealthResponse)
async def get_dashboard_health(
    config_service: ConfigServiceDep,
    settings: SettingsDep,
    item_id: Annotated[list[str] | None, Query()] = None,
) -> DashboardHealthResponse:
    try:
        items = config_service.list_items()
    except DashboardConfigValidationError as exc:
        raise _validation_exception(exc) from exc

    if item_id:
        requested = set(item_id)
        items = [item for item in items if item.id in requested]

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
                for item in items
            ]
        )

    return DashboardHealthResponse(items=statuses)


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
        try:
            ensure_admin_token(
                token=request.headers.get(settings.admin_token_header),
                admin_token=settings.admin_token,
            )
        except AuthFailure as exc:
            raise _auth_exception(exc) from exc

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
    _auth: AdminAuthDep,
    lan_scan_service: LanScanServiceDep,
) -> LanScanTriggerResponse:
    del _auth
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
        request_query=dict(request.query_params.items()),
        auth_query=auth_query,
    )

    outgoing_headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() in PROXY_REQUEST_HEADERS
    }
    outgoing_headers.update(auth_headers)

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
