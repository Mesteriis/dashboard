from __future__ import annotations

import os
from pathlib import Path

import structlog
from fastapi import FastAPI, Response
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from api.v1 import v1_router
from api.v1.metrics import metrics_router
from config.container import build_container
from depens.v1.health_runtime import start_health_runtime, stop_health_runtime
from tools.events import build_lifespan
from tools.logging import LoggingMiddleware, setup_dev_logging, setup_logging
from tools.proxy import build_upstream_url, rewrite_location, rewrite_set_cookie

BASE_DIR = Path(__file__).resolve().parent

is_dev = os.getenv("OKO_DEV", "false").lower() == "true"
if is_dev:
    setup_dev_logging()
else:
    setup_logging()

logger = structlog.get_logger()

container = build_container(base_dir=BASE_DIR)

app = FastAPI(
    title="OKO Dashboard API",
    description="""
## OKO Dashboard - Infrastructure Monitoring

FastAPI + Vue dashboard for service links, health checks, iframe integrations, and optional LAN scan.

### Features

* **Dashboard Configuration** - Manage service groups, pages, and widgets
* **Health Monitoring** - Real-time health checks with SSE streaming
* **LAN Scanning** - Discover and monitor local network services
* **Iframe Proxy** - Secure iframe embedding with authentication
* **Desktop Support** - Tauri-based desktop application (macOS ARM64)

### Authentication

Proxy endpoints require an access token obtained from the iframe source endpoint.
The token is passed via cookie (`dashboard_proxy_access`).

### Environment Variables

* `DASHBOARD_HEALTHCHECK_VERIFY_TLS` - TLS verification for health checks
* `DASHBOARD_HEALTH_REFRESH_SEC` - Health probe interval
* `DASHBOARD_ENABLE_LAN_SCAN` - Enable LAN scanning
* `LAN_SCAN_ENABLED` - Explicit LAN scan switch
* `LAN_SCAN_RUN_ON_STARTUP` - Run LAN scan on startup
""",
    version="0.1.0",
    contact={
        "name": "OKO Dashboard",
        "url": "https://github.com/oko-dashboard",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=[
        {
            "name": "dashboard",
            "description": "Dashboard configuration and management",
        },
        {
            "name": "dashboard-health",
            "description": "Service health monitoring and checks",
        },
        {
            "name": "dashboard-iframe",
            "description": "Iframe source and proxy endpoints",
        },
        {
            "name": "lan-scan",
            "description": "LAN network scanning and discovery",
        },
    ],
    lifespan=build_lifespan(
        container.lan_scan_service,
        startup_callbacks=[lambda: start_health_runtime(container)],
        shutdown_callbacks=[stop_health_runtime, container.db_engine.dispose],
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)
app.state.container = container
app.add_middleware(LoggingMiddleware)

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


app.include_router(v1_router)
app.include_router(metrics_router)

__all__ = [
    "app",
    "build_upstream_url",
    "rewrite_location",
    "rewrite_set_cookie",
]
