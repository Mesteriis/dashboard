from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import signal
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from config.container import build_container
from core.logging_setup import configure_logging

LOGGER = logging.getLogger("oko.worker")


def _configure_logging() -> None:
    configure_logging()


def _redact_url(raw: str) -> str:
    parsed = urlparse(raw)
    if parsed.password is None:
        return raw
    netloc = parsed.netloc.replace(f":{parsed.password}@", ":***@")
    return urlunparse(parsed._replace(netloc=netloc))


async def run_worker() -> None:
    os.environ.setdefault("OKO_RUNTIME_ROLE", "worker")
    base_dir = Path(__file__).resolve().parents[1]
    LOGGER.info(
        "Starting worker runtime_role=%s db=%s broker=%s",
        os.getenv("OKO_RUNTIME_ROLE", "worker"),
        _redact_url(os.getenv("DATABASE_URL", "")),
        _redact_url(os.getenv("BROKER_URL", "")),
    )
    container = build_container(base_dir=base_dir)
    await container.startup()
    LOGGER.info("Worker started and ready to consume bus messages")

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _request_stop(signame: str) -> None:
        LOGGER.info("Received signal %s, stopping worker", signame)
        stop_event.set()

    for signame in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(signame, _request_stop, signame.name)

    try:
        await stop_event.wait()
    finally:
        LOGGER.info("Shutting down worker")
        await container.shutdown()
        LOGGER.info("Worker stopped")


def main() -> None:
    _configure_logging()
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
