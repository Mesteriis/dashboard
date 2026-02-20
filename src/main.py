from __future__ import annotations

import asyncio
import os
from pathlib import Path
from time import perf_counter
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from src.dashboard_config.models import (
    ConfigVersion,
    DashboardConfig,
    DashboardHealthResponse,
    IframeSourceResponse,
    LanScanStateResponse,
    LanScanTriggerResponse,
    ItemHealthStatus,
    LinkItemConfig,
    SaveConfigResponse,
    ValidateRequest,
    ValidateResponse,
)
from src.dashboard_config.service import DashboardConfigService, DashboardConfigValidationError
from src.lan_scan import LanScanService, lan_scan_settings_from_env

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
INDEX_FILE = BASE_DIR / "templates" / "index.html"
CONFIG_FILE = Path(os.getenv("DASHBOARD_CONFIG_FILE", str(BASE_DIR.parent / "dashboard.yaml")))
HEALTHCHECK_TIMEOUT_SEC = float(os.getenv("DASHBOARD_HEALTHCHECK_TIMEOUT_SEC", "4"))
HEALTHCHECK_MAX_PARALLEL = int(os.getenv("DASHBOARD_HEALTHCHECK_MAX_PARALLEL", "8"))

PROXY_REQUEST_HEADERS = {
    "accept",
    "accept-language",
    "cache-control",
    "pragma",
    "range",
    "user-agent",
}

PROXY_RESPONSE_HEADERS = {
    "content-type",
    "cache-control",
    "etag",
    "expires",
    "last-modified",
    "content-range",
    "accept-ranges",
    "location",
}

app = FastAPI(title="oko-dashboard")
config_service = DashboardConfigService(config_path=CONFIG_FILE)
lan_scan_service = LanScanService(
    config_service=config_service,
    settings=lan_scan_settings_from_env(BASE_DIR),
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def root() -> Response:
    if not INDEX_FILE.exists():
        return PlainTextResponse(
            "Frontend build not found. Build frontend first (npm run build).",
            status_code=503,
        )
    return FileResponse(INDEX_FILE)


@app.on_event("startup")
async def on_startup() -> None:
    await lan_scan_service.start()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await lan_scan_service.stop()


@app.get("/api/v1/dashboard/config", response_model=DashboardConfig)
async def get_dashboard_config() -> DashboardConfig:
    try:
        return config_service.load()
    except DashboardConfigValidationError as exc:
        raise HTTPException(status_code=422, detail=[issue.model_dump() for issue in exc.issues]) from exc


@app.get("/api/v1/dashboard/version", response_model=ConfigVersion)
async def get_dashboard_config_version() -> ConfigVersion:
    try:
        return config_service.get_version()
    except DashboardConfigValidationError as exc:
        raise HTTPException(status_code=422, detail=[issue.model_dump() for issue in exc.issues]) from exc


@app.get("/api/v1/dashboard/errors")
async def get_dashboard_last_errors() -> dict[str, list[dict[str, str]]]:
    return {"issues": [issue.model_dump() for issue in config_service.last_issues]}


@app.post("/api/v1/dashboard/validate", response_model=ValidateResponse)
async def validate_dashboard_yaml(payload: ValidateRequest) -> ValidateResponse:
    config, issues = config_service.validate_yaml(payload.yaml)
    return ValidateResponse(valid=not issues, issues=issues, config=config)


@app.put("/api/v1/dashboard/config", response_model=SaveConfigResponse)
async def save_dashboard_config(payload: DashboardConfig) -> SaveConfigResponse:
    try:
        state = config_service.save(payload.model_dump(mode="json", exclude_none=True))
        return SaveConfigResponse(config=state.config, version=state.version)
    except DashboardConfigValidationError as exc:
        raise HTTPException(status_code=422, detail=[issue.model_dump() for issue in exc.issues]) from exc


@app.get("/api/v1/dashboard/health", response_model=DashboardHealthResponse)
async def get_dashboard_health(item_id: list[str] | None = Query(default=None)) -> DashboardHealthResponse:
    try:
        items = config_service.list_items()
    except DashboardConfigValidationError as exc:
        raise HTTPException(status_code=422, detail=[issue.model_dump() for issue in exc.issues]) from exc

    if item_id:
        requested = set(item_id)
        items = [item for item in items if item.id in requested]

    semaphore = asyncio.Semaphore(max(1, HEALTHCHECK_MAX_PARALLEL))
    async with httpx.AsyncClient(follow_redirects=True, timeout=max(0.2, HEALTHCHECK_TIMEOUT_SEC), verify=False) as client:
        statuses = await asyncio.gather(
            *[_probe_item_health(item=item, client=client, semaphore=semaphore) for item in items]
        )

    return DashboardHealthResponse(items=statuses)


@app.get("/api/v1/dashboard/iframe/{item_id}/source", response_model=IframeSourceResponse)
async def get_iframe_source(item_id: str) -> IframeSourceResponse:
    try:
        item = config_service.get_iframe_item(item_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown item id: {item_id}") from exc
    except TypeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DashboardConfigValidationError as exc:
        raise HTTPException(status_code=422, detail=[issue.model_dump() for issue in exc.issues]) from exc

    if item.auth_profile:
        src = f"/api/v1/dashboard/iframe/{item_id}/proxy"
        return IframeSourceResponse(item_id=item.id, src=src, proxied=True, auth_profile=item.auth_profile)

    return IframeSourceResponse(item_id=item.id, src=str(item.url), proxied=False, auth_profile=None)


@app.get("/api/v1/dashboard/lan/state", response_model=LanScanStateResponse)
async def get_lan_scan_state() -> LanScanStateResponse:
    return lan_scan_service.state()


@app.post("/api/v1/dashboard/lan/run", response_model=LanScanTriggerResponse)
async def run_lan_scan() -> LanScanTriggerResponse:
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


@app.api_route(
    "/api/v1/dashboard/iframe/{item_id}/proxy",
    methods=["GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"],
)
@app.api_route(
    "/api/v1/dashboard/iframe/{item_id}/proxy/{proxy_path:path}",
    methods=["GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy_iframe(request: Request, item_id: str, proxy_path: str = "") -> Response:
    try:
        item = config_service.get_iframe_item(item_id)
        auth_headers, auth_query = config_service.build_proxy_request(item)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown item id: {item_id}") from exc
    except TypeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DashboardConfigValidationError as exc:
        raise HTTPException(status_code=422, detail=[issue.model_dump() for issue in exc.issues]) from exc

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

    async with httpx.AsyncClient(follow_redirects=False, timeout=20.0) as client:
        try:
            upstream_response = await client.request(
                request.method,
                upstream_url,
                headers=outgoing_headers,
                content=body,
            )
        except httpx.HTTPError as exc:
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

    response = Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=response_headers,
    )

    for cookie in upstream_response.headers.get_list("set-cookie"):
        response.headers.append("set-cookie", cookie)

    return response


def build_upstream_url(base_url: str, proxy_path: str, request_query: dict[str, str], auth_query: dict[str, str]) -> str:
    parsed = urlsplit(base_url)
    base_path = parsed.path.rstrip("/")
    target_path = f"{base_path}/{proxy_path}" if proxy_path else base_path

    merged_query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    merged_query.update(request_query)
    merged_query.update(auth_query)

    return urlunsplit((parsed.scheme, parsed.netloc, target_path or "/", urlencode(merged_query), ""))


def rewrite_location(location: str, item_url: str, item_id: str) -> str:
    proxy_base = f"/api/v1/dashboard/iframe/{item_id}/proxy"
    item_parsed = urlsplit(item_url)
    item_origin = f"{item_parsed.scheme}://{item_parsed.netloc}"

    if location.startswith(item_origin):
        suffix = location[len(item_origin) :]
        return f"{proxy_base}{suffix if suffix.startswith('/') else '/' + suffix}"

    if location.startswith("/"):
        return f"{proxy_base}{location}"

    return f"{proxy_base}/{location}"


async def _probe_item_health(item, client: httpx.AsyncClient, semaphore: asyncio.Semaphore) -> ItemHealthStatus:
    checked_url = str(item.url)
    timeout_sec = max(0.2, HEALTHCHECK_TIMEOUT_SEC)

    if isinstance(item, LinkItemConfig) and item.healthcheck:
        checked_url = str(item.healthcheck.url)
        timeout_sec = max(0.2, item.healthcheck.timeout_ms / 1000)

    started_at = perf_counter()

    try:
        async with semaphore:
            response = await client.get(checked_url, timeout=timeout_sec)
        latency_ms = int((perf_counter() - started_at) * 1000)
        is_ok = 200 <= response.status_code < 400
        return ItemHealthStatus(
            item_id=item.id,
            ok=is_ok,
            checked_url=checked_url,
            status_code=response.status_code,
            latency_ms=latency_ms,
            error=None if is_ok else f"HTTP {response.status_code}",
        )
    except Exception as exc:  # noqa: BLE001 - health checks should never fail the endpoint
        latency_ms = int((perf_counter() - started_at) * 1000)
        return ItemHealthStatus(
            item_id=item.id,
            ok=False,
            checked_url=checked_url,
            status_code=None,
            latency_ms=latency_ms,
            error=str(exc),
        )
