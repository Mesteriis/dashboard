from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from api.v1 import v1_router
from config.container import build_container
from core.contracts.errors import ApiError, ErrorModel
from core.logging_setup import configure_logging
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent
configure_logging()
container = build_container(base_dir=BASE_DIR)
logger = logging.getLogger("core.http")


@asynccontextmanager
async def app_lifespan(_: FastAPI):
    await container.startup()
    try:
        yield
    finally:
        await container.shutdown()


app = FastAPI(
    title="Oko Core API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=app_lifespan,
)
app.state.container = container


@app.middleware("http")
async def handle_cancelled_request(request: Request, call_next):
    try:
        return await call_next(request)
    except asyncio.CancelledError:
        logger.info(
            "Request cancelled by client method=%s path=%s",
            request.method,
            request.url.path,
        )
        return Response(status_code=499)


@app.exception_handler(ApiError)
async def handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.error.model_dump(mode="json"))


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
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


if container.settings.static_dir.exists():
    app.mount("/static", StaticFiles(directory=container.settings.static_dir), name="static")
container.settings.media_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=container.settings.media_dir), name="media")

# Mount plugin routers if plugin service is available
if container.plugin_service:
    # Mount plugin pages router
    app.include_router(container.plugin_service.router.get_router())
    # Mount plugin API router
    app.include_router(container.plugin_service.router.get_api_router())


@app.get("/", response_model=None)
async def root() -> Response:
    if not container.settings.index_file.exists():
        return PlainTextResponse("Frontend build not found", status_code=503)
    return FileResponse(container.settings.index_file)


app.include_router(v1_router)

__all__ = ["app"]
