from __future__ import annotations

import contextlib
import json
import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
import structlog
from tools.logging import set_global_log_sink, setup_logging


def _flush_handlers() -> None:
    for handler in logging.getLogger().handlers:
        with contextlib.suppress(Exception):
            handler.flush()


@pytest.fixture(autouse=True)
def _cleanup_logging_state() -> Iterator[None]:
    yield
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()
    root.setLevel(logging.WARNING)
    set_global_log_sink(None)
    structlog.reset_defaults()


def test_console_handler_renders_level_and_message_only(capsys: pytest.CaptureFixture[str]) -> None:
    setup_logging(level="INFO", log_file=None, enable_global_handler=False)

    structlog.get_logger("test.console").info("console_message", noise="omit")
    _flush_handlers()

    captured = capsys.readouterr()
    lines = [line for line in captured.err.splitlines() if line.strip()]

    assert lines
    assert lines[-1] == "INFO console_message"


def test_file_handler_writes_json_log_line(tmp_path: Path) -> None:
    log_file = tmp_path / "backend.log"
    setup_logging(level="INFO", log_file=log_file, enable_global_handler=False)

    structlog.get_logger("test.file").info("file_message", component="tests")
    _flush_handlers()

    lines = [line for line in log_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert lines

    payload = json.loads(lines[-1])
    assert payload["event"] == "file_message"
    assert payload["level"] == "info"
    assert payload["component"] == "tests"
    assert payload["timestamp"]


def test_global_forward_handler_sends_json_payload() -> None:
    forwarded: list[tuple[str, int]] = []

    set_global_log_sink(lambda payload, level: forwarded.append((payload, level)))
    setup_logging(level="INFO", log_file=None, enable_global_handler=True)

    structlog.get_logger("test.global").warning("global_message", target="sink")
    _flush_handlers()

    assert len(forwarded) == 1
    payload, level = forwarded[0]

    event = json.loads(payload)
    assert level == logging.WARNING
    assert event["event"] == "global_message"
    assert event["level"] == "warning"
    assert event["target"] == "sink"
