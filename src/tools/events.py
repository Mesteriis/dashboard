from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from fastapi import FastAPI

from service.lan_scan import LanScanService


def build_lifespan(
    lan_scan_service: LanScanService,
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await lan_scan_service.start()
        try:
            yield
        finally:
            await lan_scan_service.stop()

    return lifespan
