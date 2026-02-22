"""Structured logging configuration with request tracing and handler fan-out."""

from __future__ import annotations

import contextlib
import logging
import sys
from collections.abc import Callable
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

import structlog

GlobalLogSink = Callable[[str, int], None]
DEFAULT_LOG_FILE = ".data/logs/backend.log"
_global_log_sink: GlobalLogSink | None = None


def set_global_log_sink(sink: GlobalLogSink | None) -> None:
    """Register runtime sink for the global forwarding handler."""
    global _global_log_sink
    _global_log_sink = sink


def _resolve_level(level: str) -> int:
    resolved = logging.getLevelName(level.upper())
    if isinstance(resolved, int):
        return resolved
    return logging.INFO


def _shared_processors() -> list[structlog.types.Processor]:
    return [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        _add_request_id,
        structlog.processors.dict_tracebacks,
    ]


def _render_console(
    _logger: structlog.types.WrappedLogger,
    _method_name: str,
    event_dict: structlog.types.EventDict,
) -> str:
    level = str(event_dict.get("level", "info")).upper()
    message = str(event_dict.get("event", "")).strip()
    return f"{level} {message}".strip()


_json_timestamper = structlog.processors.TimeStamper(fmt="iso")
_json_renderer = structlog.processors.JSONRenderer()


def _render_json(
    logger: structlog.types.WrappedLogger,
    method_name: str,
    event_dict: structlog.types.EventDict,
) -> str:
    event_with_ts = _json_timestamper(logger, method_name, dict(event_dict))
    rendered = _json_renderer(logger, method_name, event_with_ts)
    if isinstance(rendered, bytes):
        return rendered.decode("utf-8", errors="replace")
    return rendered


def _build_formatter(processor: structlog.types.Processor) -> structlog.stdlib.ProcessorFormatter:
    return structlog.stdlib.ProcessorFormatter(
        processor=processor,
        foreign_pre_chain=_shared_processors(),
    )


def _build_console_handler(level: int) -> logging.Handler:
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setLevel(level)
    handler.setFormatter(_build_formatter(_render_console))
    return handler


def _build_file_handler(level: int, log_file: Path) -> logging.Handler:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(_build_formatter(_render_json))
    return handler


class GlobalLoggerForwardHandler(logging.Handler):
    """Forward logs to runtime sink for future global logger integration."""

    def emit(self, record: logging.LogRecord) -> None:
        if _global_log_sink is None:
            return
        try:
            _global_log_sink(self.format(record), record.levelno)
        except Exception:
            self.handleError(record)


def _build_global_handler(level: int) -> logging.Handler:
    handler = GlobalLoggerForwardHandler()
    handler.setLevel(level)
    handler.setFormatter(_build_formatter(_render_json))
    return handler


def _reset_root_handlers(root: logging.Logger) -> None:
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()


def _configure_root_logging(
    *,
    level: int,
    log_file: str | Path | None,
    enable_global_handler: bool,
) -> None:
    root = logging.getLogger()
    _reset_root_handlers(root)
    root.setLevel(level)
    root.addHandler(_build_console_handler(level))

    if log_file is not None:
        try:
            root.addHandler(_build_file_handler(level, Path(log_file)))
        except OSError:
            # Fall back to console-only logging if file destination is unavailable.
            sys.stderr.write(f"WARNING file log handler init failed: {log_file}\n")

    if enable_global_handler:
        root.addHandler(_build_global_handler(level))


def _configure_structlog(level: int, *, cache_logger_on_first_use: bool) -> None:
    structlog.configure(
        processors=[
            *_shared_processors(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=cache_logger_on_first_use,
    )


def setup_logging(
    level: str = "INFO",
    *,
    log_file: str | Path | None = DEFAULT_LOG_FILE,
    enable_global_handler: bool = True,
) -> None:
    """Configure global logging handlers and structlog for runtime."""
    resolved_level = _resolve_level(level)
    _configure_root_logging(level=resolved_level, log_file=log_file, enable_global_handler=enable_global_handler)
    _configure_structlog(resolved_level, cache_logger_on_first_use=True)


def setup_dev_logging(
    level: str = "INFO",
    *,
    log_file: str | Path | None = DEFAULT_LOG_FILE,
    enable_global_handler: bool = True,
) -> None:
    """Configure global logging handlers and structlog for development runtime."""
    resolved_level = _resolve_level(level)
    _configure_root_logging(level=resolved_level, log_file=log_file, enable_global_handler=enable_global_handler)
    _configure_structlog(resolved_level, cache_logger_on_first_use=False)


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
            f"http {method} {path} started",
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
                f"http {method} {path} finished status={status_code or '-'} duration_ms={duration_ms}",
                method=method,
                path=path,
                status_code=status_code,
                duration_ms=duration_ms,
                request_id=request_id,
            )

            set_request_id(None)
