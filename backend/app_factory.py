from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from api.v1 import v1_router
from config.container import AppContainer
from config.settings import AppSettings
from core.contracts.errors import ApiError, ErrorModel
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger("core.http")


def _register_plugin_routes(app: FastAPI, container: AppContainer) -> None:
    if not container.plugin_service:
        return
    if getattr(app.state, "_plugin_routes_registered", False):
        return
    app.include_router(container.plugin_service.router.get_router())
    app.include_router(container.plugin_service.router.get_api_router())
    app.state._plugin_routes_registered = True


@asynccontextmanager
async def build_lifespan(
    app: FastAPI,
    *,
    container_factory: Callable[[], AppContainer],
    init_logging: Callable[[], None],
) -> AsyncIterator[None]:
    init_logging()
    container = container_factory()
    app.state.container = container
    _register_plugin_routes(app, container)
    await container.startup()
    try:
        yield
    finally:
        await container.shutdown()


async def handle_cancelled_request(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    try:
        return await call_next(request)
    except asyncio.CancelledError:
        logger.info(
            "Request cancelled by client method=%s path=%s",
            request.method,
            request.url.path,
        )
        return Response(status_code=499)


async def handle_api_error(_: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, ApiError):
        raise exc
    return JSONResponse(status_code=exc.status_code, content=exc.error.model_dump(mode="json"))


async def handle_validation_error(_: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        raise exc
    details = [
        {
            "loc": list(issue.get("loc", ())),
            "msg": issue.get("msg", "invalid value"),
        }
        for issue in exc.errors()
    ]
    error = ErrorModel(
        code="validation_error",
        message="Request validation failed",
        details=details,
    )
    return JSONResponse(status_code=422, content=error.model_dump(mode="json"))


def create_app(
    *,
    settings: AppSettings,
    container_factory: Callable[[], AppContainer],
    init_logging: Callable[[], None],
) -> FastAPI:
    app = FastAPI(
        title="Oko Core API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lambda app_obj: build_lifespan(
            app_obj,
            container_factory=container_factory,
            init_logging=init_logging,
        ),
    )
    app.state.container = None

    app.middleware("http")(handle_cancelled_request)
    app.add_exception_handler(ApiError, handle_api_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)

    if settings.static_dir.exists():
        app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")
    settings.media_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=settings.media_dir), name="media")

    @app.get("/", response_model=None)  # type: ignore[untyped-decorator]
    async def root() -> Response:
        if not settings.index_file.exists():
            return PlainTextResponse("Frontend build not found", status_code=503)
        return FileResponse(settings.index_file)

    app.include_router(v1_router)
    return app


__all__ = [
    "build_lifespan",
    "create_app",
    "handle_api_error",
    "handle_cancelled_request",
    "handle_validation_error",
]
