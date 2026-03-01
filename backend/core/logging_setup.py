from __future__ import annotations

import logging
import os
import threading
from datetime import datetime
from typing import TextIO

_CONFIGURE_LOCK = threading.Lock()
_IS_CONFIGURED = False

_LEVEL_LETTER = {
    logging.DEBUG: "D",
    logging.INFO: "I",
    logging.WARNING: "W",
    logging.ERROR: "E",
    logging.CRITICAL: "C",
}

_ANSI_RESET = "\x1b[0m"
_LEVEL_COLOR = {
    logging.DEBUG: "\x1b[36m",  # cyan
    logging.INFO: "\x1b[32m",  # green
    logging.WARNING: "\x1b[33m",  # yellow
    logging.ERROR: "\x1b[31m",  # red
    logging.CRITICAL: "\x1b[35m",  # magenta
}

_LOGGER_LEVEL_OVERRIDES: dict[str, int] = {
    # SQLAlchemy is too noisy on INFO/DEBUG for runtime logs.
    "sqlalchemy": logging.ERROR,
    "sqlalchemy.engine": logging.ERROR,
    "sqlalchemy.pool": logging.ERROR,
    "sqlalchemy.orm": logging.ERROR,
    "sqlalchemy.dialects": logging.ERROR,
}


class _SqlalchemyErrorOnlyFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return not (
            record.name.startswith("sqlalchemy") and record.levelno < logging.ERROR
        )


def _add_filter_once(handler: logging.Handler, log_filter: logging.Filter) -> None:
    if any(isinstance(existing, type(log_filter)) for existing in handler.filters):
        return
    handler.addFilter(log_filter)


def _as_bool(raw: str | None, *, default: bool) -> bool:
    if raw is None:
        return default
    token = raw.strip().lower()
    if token in {"1", "true", "yes", "on", "y"}:
        return True
    if token in {"0", "false", "no", "off", "n"}:
        return False
    return default


def _normalize_logger_name(name: str) -> str:
    token = str(name or "").strip()
    if not token:
        return "root"
    return token


def _iter_real_loggers() -> list[logging.Logger]:
    loggers: list[logging.Logger] = []
    for candidate in logging.root.manager.loggerDict.values():
        if isinstance(candidate, logging.Logger):
            loggers.append(candidate)
    return loggers


def _resolve_logger_width() -> int:
    min_width = 24
    max_width = 48
    known = {
        "root",
        "oko.worker",
        "core.plugins.router",
        "core.plugins.autodiscover",
        "apps.health.worker.scheduler",
    }
    for logger in _iter_real_loggers():
        known.add(_normalize_logger_name(logger.name))
    if not known:
        return min_width
    width = max(len(name) for name in known)
    width = max(min_width, width)
    width = min(max_width, width)
    return width


def _stream_supports_color(stream: TextIO | None) -> bool:
    if stream is None:
        return False
    is_a_tty = getattr(stream, "isatty", None)
    if not callable(is_a_tty):
        return False
    try:
        return bool(is_a_tty())
    except Exception:
        return False


class OkoConsoleFormatter(logging.Formatter):
    def __init__(self, *, logger_width: int, color: bool) -> None:
        super().__init__()
        self._logger_width = max(8, int(logger_width))
        self._color = bool(color)

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        _ = datefmt
        dt = datetime.fromtimestamp(record.created)
        return dt.strftime("%H:%M:%S")

    def format(self, record: logging.LogRecord) -> str:
        ts = self.formatTime(record)
        letter = _LEVEL_LETTER.get(record.levelno, record.levelname[:1].upper())
        level_block = f"[ {letter} ]"
        if self._color:
            color = _LEVEL_COLOR.get(record.levelno)
            if color:
                level_block = f"{color}{level_block}{_ANSI_RESET}"

        logger_name = _normalize_logger_name(record.name)
        message = record.getMessage()

        if record.exc_info:
            message = f"{message}\n{self.formatException(record.exc_info)}"
        if record.stack_info:
            message = f"{message}\n{self.formatStack(record.stack_info)}"

        return f"{ts} {level_block} [{logger_name:<{self._logger_width}}] {message}"


def configure_logging(*, force: bool = False) -> None:
    global _IS_CONFIGURED

    with _CONFIGURE_LOCK:
        if _IS_CONFIGURED and not force:
            return

        level_name = os.getenv("OKO_LOG_LEVEL", "INFO").upper()
        level = getattr(logging, level_name, logging.INFO)
        logger_width = _resolve_logger_width()

        root = logging.getLogger()
        if not root.handlers:
            root.addHandler(logging.StreamHandler())
        root.setLevel(level)

        default_stream: TextIO | None = None
        for handler in root.handlers:
            stream = getattr(handler, "stream", None)
            if stream is not None:
                default_stream = stream
                break
        color_enabled = _as_bool(
            os.getenv("OKO_LOG_COLOR"),
            default=_stream_supports_color(default_stream),
        )
        formatter = OkoConsoleFormatter(logger_width=logger_width, color=color_enabled)
        sqlalchemy_filter = _SqlalchemyErrorOnlyFilter()

        for handler in root.handlers:
            handler.setLevel(level)
            handler.setFormatter(formatter)
            _add_filter_once(handler, sqlalchemy_filter)

        for logger in _iter_real_loggers():
            logger.setLevel(level)
            for handler in logger.handlers:
                handler.setLevel(level)
                handler.setFormatter(formatter)
                _add_filter_once(handler, sqlalchemy_filter)

        for logger_name, logger_level in _LOGGER_LEVEL_OVERRIDES.items():
            logging.getLogger(logger_name).setLevel(logger_level)

        _IS_CONFIGURED = True


__all__ = ["OkoConsoleFormatter", "configure_logging"]
