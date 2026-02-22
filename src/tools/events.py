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
    shutdown_callbacks: Iterable[Callable[[], Any]] = (),
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await lan_scan_service.start()
        try:
            yield
        finally:
            await lan_scan_service.stop()
            for callback in shutdown_callbacks:
                result = callback()
                if inspect.isawaitable(result):
                    await result

    return lifespan
