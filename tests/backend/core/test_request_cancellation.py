from __future__ import annotations

import asyncio
import importlib
from pathlib import Path

import pytest
from starlette.requests import Request
from starlette.responses import Response

DEFAULT_BOOTSTRAP = """\
version: 1
app:
  id: demo
  title: Demo
widgets:
  - type: system.status
"""


def _reload_main_module():
    module = importlib.import_module("main")
    container = getattr(module, "container", None)
    if container is not None:
        container.db_engine.sync_engine.dispose()
    return importlib.reload(module)


@pytest.mark.asyncio
async def test_cancelled_request_middleware_returns_499(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = (tmp_path / "oko.sqlite3").resolve()
    bootstrap = (tmp_path / "bootstrap.yaml").resolve()
    bootstrap.write_text(DEFAULT_BOOTSTRAP, encoding="utf-8")

    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("BROKER_URL", "memory://local")
    monkeypatch.setenv("OKO_BOOTSTRAP_CONFIG_FILE", str(bootstrap))

    main_module = _reload_main_module()

    request = Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/api/v1/plugins/autodiscover/services",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "server": ("test", 80),
        }
    )

    async def _cancelled_call_next(_: Request) -> Response:
        raise asyncio.CancelledError()

    response = await main_module.handle_cancelled_request(request, _cancelled_call_next)
    assert response.status_code == 499

