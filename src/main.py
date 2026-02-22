from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Response
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from api.v1.dashboard import (
    dashboard_router,
    start_health_runtime,
    stop_health_runtime,
)
from config.container import build_container
from tools.events import build_lifespan
from tools.proxy import build_upstream_url, rewrite_location, rewrite_set_cookie

BASE_DIR = Path(__file__).resolve().parent
container = build_container(base_dir=BASE_DIR)

app = FastAPI(
    title="oko-dashboard",
    lifespan=build_lifespan(
        container.lan_scan_service,
        startup_callbacks=[lambda: start_health_runtime(container)],
        shutdown_callbacks=[stop_health_runtime, container.db_engine.dispose],
    ),
)
app.state.container = container

if container.settings.static_dir.exists():
    app.mount("/static", StaticFiles(directory=container.settings.static_dir), name="static")


@app.get("/")
async def root() -> Response:
    if not container.settings.index_file.exists():
        return PlainTextResponse(
            "Frontend build not found. Build frontend first (npm run build).",
            status_code=503,
        )
    return FileResponse(container.settings.index_file)


app.include_router(dashboard_router)

__all__ = [
    "app",
    "build_upstream_url",
    "rewrite_location",
    "rewrite_set_cookie",
]
