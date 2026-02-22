from __future__ import annotations

from collections.abc import AsyncIterator

import depens.v1.health_runtime as health_runtime
from depens.v1.dashboard_deps import ConfigServiceDep, ProxySignerDep, SettingsDep, validation_exception
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from scheme.dashboard import IframeSourceResponse
from service.config_service import DashboardConfigValidationError
from starlette.background import BackgroundTask
from tools.proxy import (
    PROXY_REQUEST_HEADERS,
    PROXY_RESPONSE_HEADERS,
    build_upstream_url,
    close_upstream_resources,
    filter_cookie_header,
    rewrite_location,
    rewrite_set_cookie,
)

iframe_router = APIRouter(prefix="/dashboard", tags=["dashboard-iframe"])


@iframe_router.get(
    "/iframe/{item_id}/source",
    response_model=IframeSourceResponse,
    summary="Get iframe source URL",
    description=(
        "Returns the source URL for an iframe item. "
        "For protected items, returns a proxy URL with authentication cookie."
    ),
    responses={
        200: {"description": "Iframe source URL"},
        400: {"description": "Item is not an iframe"},
        404: {"description": "Item not found"},
    },
)
async def get_iframe_source(
    item_id: str,
    response: Response,
    request: Request,
    config_service: ConfigServiceDep,
    settings: SettingsDep,
    proxy_signer: ProxySignerDep,
) -> IframeSourceResponse:
    item = health_runtime._load_iframe_item(item_id, config_service)

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


@iframe_router.api_route(
    "/iframe/{item_id}/proxy",
    methods=["GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"],
)
@iframe_router.api_route(
    "/iframe/{item_id}/proxy/{proxy_path:path}",
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
    item = health_runtime._load_iframe_item(item_id, config_service)

    try:
        auth_headers, auth_query = config_service.build_proxy_request(item)
    except DashboardConfigValidationError as exc:
        raise validation_exception(exc) from exc

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

    outgoing_headers = {key: value for key, value in request.headers.items() if key.lower() in PROXY_REQUEST_HEADERS}
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

    client = health_runtime.httpx.AsyncClient(follow_redirects=False, timeout=20.0)
    upstream_request = client.build_request(
        request.method,
        upstream_url,
        headers=outgoing_headers,
        content=body,
    )
    try:
        upstream_response = await client.send(upstream_request, stream=True)
    except health_runtime.httpx.HTTPError as exc:
        await client.aclose()
        raise HTTPException(status_code=502, detail=f"Upstream request failed: {exc}") from exc

    response_headers = {
        key: value for key, value in upstream_response.headers.items() if key.lower() in PROXY_RESPONSE_HEADERS
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


__all__ = ["iframe_router"]
