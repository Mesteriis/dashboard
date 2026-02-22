from __future__ import annotations

import os
from pathlib import Path

import structlog
from api.v1 import v1_router
from api.v1.metrics import metrics_router
from config.container import build_container
from depens.v1.health_runtime import start_health_runtime, stop_health_runtime
from fastapi import FastAPI, Response
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from tools.events import build_lifespan
from tools.logging import DEFAULT_LOG_FILE, LoggingMiddleware, setup_dev_logging, setup_logging
from tools.proxy import build_upstream_url, rewrite_location, rewrite_set_cookie

BASE_DIR = Path(__file__).resolve().parent


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_log_file(name: str, default: str) -> str | None:
    raw = os.getenv(name)
    if raw is None:
        return default

    value = raw.strip()
    if value.lower() in {"", "none", "null", "false", "off"}:
        return None
    return value


is_dev = os.getenv("OKO_DEV", "false").lower() == "true"
log_level = os.getenv("DASHBOARD_LOG_LEVEL", "INFO")
log_file = _env_log_file("DASHBOARD_LOG_FILE", DEFAULT_LOG_FILE)
enable_global_log_handler = _env_bool("DASHBOARD_ENABLE_GLOBAL_LOG_HANDLER", True)

def _configure_logging() -> None:
    if is_dev:
        setup_dev_logging(
            level=log_level,
            log_file=log_file,
            enable_global_handler=enable_global_log_handler,
        )
    else:
        setup_logging(
            level=log_level,
            log_file=log_file,
            enable_global_handler=enable_global_log_handler,
        )


_configure_logging()

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
        startup_callbacks=[_configure_logging, lambda: start_health_runtime(container)],
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
