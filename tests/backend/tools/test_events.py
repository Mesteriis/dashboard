from __future__ import annotations

import pytest
from fastapi import FastAPI

from tools.events import build_lifespan


class StubLanScanService:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def start(self) -> None:
        self.calls.append("start")

    async def stop(self) -> None:
        self.calls.append("stop")


@pytest.mark.asyncio
async def test_build_lifespan_runs_shutdown_callbacks_after_stop() -> None:
    service = StubLanScanService()
    callback_calls: list[str] = []

    def sync_callback() -> None:
        callback_calls.append("sync")

    async def async_callback() -> None:
        callback_calls.append("async")

    lifespan = build_lifespan(
        service,
        shutdown_callbacks=[sync_callback, async_callback],
    )

    async with lifespan(FastAPI()):
        assert service.calls == ["start"]
        assert callback_calls == []

    assert service.calls == ["start", "stop"]
    assert callback_calls == ["sync", "async"]


@pytest.mark.asyncio
async def test_build_lifespan_runs_startup_callbacks_before_service_start() -> None:
    service = StubLanScanService()
    callback_calls: list[str] = []

    def sync_callback() -> None:
        callback_calls.append("sync")

    async def async_callback() -> None:
        callback_calls.append("async")

    lifespan = build_lifespan(
        service,
        startup_callbacks=[sync_callback, async_callback],
    )

    async with lifespan(FastAPI()):
        assert callback_calls == ["sync", "async"]
        assert service.calls == ["start"]
