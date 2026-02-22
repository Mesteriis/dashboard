"""Structured logging configuration with request tracing."""

from __future__ import annotations

import contextlib
import logging
import sys
from typing import Any

import structlog


def setup_logging(level: str = "INFO") -> None:
    """Configure structlog with JSON output for production and console for development."""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=logging.getLevelName(level),
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            _add_request_id,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def setup_dev_logging(level: str = "INFO") -> None:
    """Configure structlog with human-readable console output for development."""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=logging.getLevelName(level),
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="%H:%M:%S"),
            _add_request_id,
            structlog.dev.ConsoleRenderer(colors=True),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )


def _add_request_id(
    logger: structlog.types.WrappedLogger,
    _method_name: str,
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    """Add request ID from context vars if available."""
    from contextvars import copy_context

    request_id = copy_context().get(_request_id_var, None)
    if request_id is not None:
        event_dict["request_id"] = request_id
    return event_dict


_request_id_var: Any = None

with contextlib.suppress(ImportError):
    from contextvars import ContextVar

    _request_id_var = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    """Get current request ID from context."""
    if _request_id_var is None:
        return None
    result = _request_id_var.get()
    return str(result) if result is not None else None


def set_request_id(request_id: str | None) -> None:
    """Set request ID in context."""
    if _request_id_var is None:
        return
    _request_id_var.set(request_id)


def generate_request_id() -> str:
    """Generate a new request ID."""
    import secrets

    return secrets.token_urlsafe(8)


class LoggingMiddleware:
    """ASGI middleware for request logging with tracing."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        import time

        request_id = generate_request_id()
        set_request_id(request_id)

        logger = structlog.get_logger()
        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "/")

        start_time = time.perf_counter()

        await logger.ainfo(
            "request_started",
            method=method,
            path=path,
            request_id=request_id,
        )

        status_code = None

        async def send_wrapper(message: dict[str, Any]) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            log_level = "info"
            if status_code and status_code >= 500:
                log_level = "error"
            elif status_code and status_code >= 400:
                log_level = "warning"

            await getattr(logger, f"a{log_level}")(
                "request_finished",
                method=method,
                path=path,
                status_code=status_code,
                duration_ms=duration_ms,
                request_id=request_id,
            )

            set_request_id(None)
