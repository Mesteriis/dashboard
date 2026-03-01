"""Plugin Store - FastAPI service for plugin management."""

import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from store.api.plugins import router as plugins_router
from store.api.rpc import router as rpc_router
from store.api.system import router as system_router
from store.core.config import settings
from store.services.storage import plugin_storage


def setup_logging() -> None:
    """Configure structured logging."""
    logging.basicConfig(
        format="%(message)s",
        level=logging.DEBUG if settings.debug else logging.INFO,
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer() if settings.debug else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if settings.debug else logging.INFO
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    setup_logging()
    logger = structlog.get_logger(__name__)
    logger.info(
        "Store starting",
        version=settings.app_version,
        storage_path=str(plugin_storage.storage_path),
    )

    # Ensure storage exists
    plugin_storage.storage_path.mkdir(parents=True, exist_ok=True)
    plugins = plugin_storage.list_plugins()
    logger.info("Discovered plugins in storage", total=len(plugins))
    if plugins:
        for plugin in plugins:
            logger.info(
                "Plugin discovered",
                plugin_id=plugin.id,
                name=plugin.name,
                version=plugin.version,
                source=str(plugin.source),
            )
    else:
        logger.info("No plugins found in storage")

    yield

    # Shutdown
    logger = structlog.get_logger(__name__)
    logger.info("Store shutting down")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Store API for managing plugin uploads and distribution",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    # Include routers
    app.include_router(system_router, prefix="/api/v1")
    app.include_router(plugins_router, prefix="/api/v1")
    app.include_router(rpc_router, prefix="/api/v1")

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger = structlog.get_logger(__name__)
        logger.error("Unhandled exception", path=str(request.url), error=str(exc))
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Internal server error", "detail": str(exc)},
        )

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "store.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
