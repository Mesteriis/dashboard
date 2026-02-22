from __future__ import annotations

import inspect
from collections.abc import AsyncIterator, Callable, Iterable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any

from fastapi import FastAPI
from service.lan_scan import LanScanService


def build_lifespan(
    lan_scan_service: LanScanService,
    *,
    startup_callbacks: Iterable[Callable[[], Any]] = (),
    shutdown_callbacks: Iterable[Callable[[], Any]] = (),
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        lan_scan_started = False
        try:
            for callback in startup_callbacks:
                result = callback()
                if inspect.isawaitable(result):
                    await result
            await lan_scan_service.start()
            lan_scan_started = True
            yield
        finally:
            if lan_scan_started:
                await lan_scan_service.stop()
            for callback in shutdown_callbacks:
                result = callback()
                if inspect.isawaitable(result):
                    await result

    return lifespan
