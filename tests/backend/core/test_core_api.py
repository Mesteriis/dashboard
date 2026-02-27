from __future__ import annotations

import importlib
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.asyncio


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


def _full_headers() -> dict[str, str]:
    return {
        "X-Oko-Actor": "tester",
        "X-Oko-Capabilities": ",".join(
            [
                "read.state",
                "read.config",
                "read.config.revisions",
                "read.registry.widgets",
                "read.registry.actions",
                "exec.actions.validate",
                "exec.actions.execute",
                "read.actions.history",
                "write.config.import",
                "write.config.patch",
                "write.config.rollback",
                "exec.system.echo",
                "exec.autodiscover.scan",
                "read.events",
            ]
        ),
    }


async def _client(main_module):
    async with (
        main_module.app.router.lifespan_context(main_module.app),
        AsyncClient(transport=ASGITransport(app=main_module.app), base_url="http://test") as client,
    ):
        yield client


async def test_state_requires_capability(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = (tmp_path / "oko.sqlite3").resolve()
    bootstrap = (tmp_path / "bootstrap.yaml").resolve()
    bootstrap.write_text(DEFAULT_BOOTSTRAP, encoding="utf-8")

    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("BROKER_URL", "memory://local")
    monkeypatch.setenv("OKO_BOOTSTRAP_CONFIG_FILE", str(bootstrap))

    main_module = _reload_main_module()

    async for client in _client(main_module):
        response = await client.get("/api/v1/state", headers={"X-Oko-Actor": "tester"})
        assert response.status_code == httpx.codes.FORBIDDEN
        assert response.json()["code"] == "capability_required"


async def test_config_flow_import_patch_rollback(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = (tmp_path / "oko.sqlite3").resolve()
    bootstrap = (tmp_path / "bootstrap.yaml").resolve()
    bootstrap.write_text(DEFAULT_BOOTSTRAP, encoding="utf-8")

    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("BROKER_URL", "memory://local")
    monkeypatch.setenv("OKO_BOOTSTRAP_CONFIG_FILE", str(bootstrap))

    main_module = _reload_main_module()
    headers = _full_headers()

    async for client in _client(main_module):
        state_response = await client.get("/api/v1/state", headers=headers)
        assert state_response.status_code == httpx.codes.OK
        active_revision = state_response.json()["active_revision"]

        import_response = await client.post(
            "/api/v1/config/import",
            headers=headers,
            json={
                "format": "json",
                "payload": '{"version":1,"app":{"id":"demo","title":"Imported"},"widgets":[]}',
                "source": "import",
            },
        )
        assert import_response.status_code == httpx.codes.OK
        imported_revision = import_response.json()["active_state"]["active_revision"]
        assert imported_revision > active_revision

        patch_response = await client.post(
            "/api/v1/config/patch",
            headers=headers,
            json={"patch": {"app": {"title": "Patched"}}, "source": "patch"},
        )
        assert patch_response.status_code == httpx.codes.OK
        patched_revision = patch_response.json()["active_state"]["active_revision"]
        assert patched_revision > imported_revision

        revisions_response = await client.get("/api/v1/config/revisions", headers=headers)
        assert revisions_response.status_code == httpx.codes.OK
        revisions = revisions_response.json()
        assert len(revisions) >= 3

        rollback_response = await client.post(
            "/api/v1/config/rollback",
            headers=headers,
            json={"revision": imported_revision, "source": "rollback"},
        )
        assert rollback_response.status_code == httpx.codes.OK
        rolled_payload = rollback_response.json()["revision"]["payload"]
        assert rolled_payload["app"]["title"] == "Imported"


async def test_config_validate_endpoint(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = (tmp_path / "oko.sqlite3").resolve()
    bootstrap = (tmp_path / "bootstrap.yaml").resolve()
    bootstrap.write_text(DEFAULT_BOOTSTRAP, encoding="utf-8")

    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("BROKER_URL", "memory://local")
    monkeypatch.setenv("OKO_BOOTSTRAP_CONFIG_FILE", str(bootstrap))

    main_module = _reload_main_module()
    headers = _full_headers()

    async for client in _client(main_module):
        valid_response = await client.post(
            "/api/v1/config/validate",
            headers=headers,
            json={"format": "yaml", "payload": "version: 1\napp:\n  id: demo\n"},
        )
        assert valid_response.status_code == httpx.codes.OK
        assert valid_response.json()["valid"] is True

        invalid_response = await client.post(
            "/api/v1/config/validate",
            headers=headers,
            json={"format": "yaml", "payload": "version: 1\n"},
        )
        assert invalid_response.status_code == httpx.codes.OK
        assert invalid_response.json()["valid"] is False


async def test_actions_gateway_execute_and_history(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = (tmp_path / "oko.sqlite3").resolve()
    bootstrap = (tmp_path / "bootstrap.yaml").resolve()
    bootstrap.write_text(DEFAULT_BOOTSTRAP, encoding="utf-8")

    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("BROKER_URL", "memory://local")
    monkeypatch.setenv("OKO_BOOTSTRAP_CONFIG_FILE", str(bootstrap))

    main_module = _reload_main_module()
    headers = _full_headers()

    async for client in _client(main_module):
        validate_response = await client.post(
            "/api/v1/actions/validate",
            headers=headers,
            json={
                "type": "system.echo",
                "requested_by": "tester",
                "capability": "exec.system.echo",
                "payload": {"hello": "world"},
            },
        )
        assert validate_response.status_code == httpx.codes.OK
        assert validate_response.json()["valid"] is True

        execute_response = await client.post(
            "/api/v1/actions/execute",
            headers=headers,
            json={
                "type": "system.echo",
                "requested_by": "tester",
                "capability": "exec.system.echo",
                "payload": {"hello": "world"},
                "dry_run": False,
            },
        )
        assert execute_response.status_code == httpx.codes.OK
        assert execute_response.json()["status"] == "succeeded"

        history_response = await client.get("/api/v1/actions/history", headers=headers)
        assert history_response.status_code == httpx.codes.OK
        history = history_response.json()
        assert len(history) >= 2


async def test_autodiscover_action_registry_and_dry_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pytest.skip("autodiscover action not yet implemented")

    db_path = (tmp_path / "oko.sqlite3").resolve()
    bootstrap = (tmp_path / "bootstrap.yaml").resolve()
    bootstrap.write_text(DEFAULT_BOOTSTRAP, encoding="utf-8")

    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("BROKER_URL", "memory://local")
    monkeypatch.setenv("OKO_BOOTSTRAP_CONFIG_FILE", str(bootstrap))

    main_module = _reload_main_module()
    headers = _full_headers()

    async for client in _client(main_module):
        registry_response = await client.get("/api/v1/actions/registry", headers=headers)
        assert registry_response.status_code == httpx.codes.OK
        registry_items = registry_response.json()
        autodiscover_entry = next(item for item in registry_items if item.get("type") == "autodiscover.scan")
        assert autodiscover_entry["capability"] == "exec.autodiscover.scan"
        assert autodiscover_entry["dry_run_supported"] is True

        execute_response = await client.post(
            "/api/v1/actions/execute",
            headers=headers,
            json={
                "type": "autodiscover.scan",
                "requested_by": "tester",
                "capability": "exec.autodiscover.scan",
                "payload": {
                    "hosts": ["127.0.0.1"],
                    "ports": [22, 80, 443],
                    "timeout_ms": 30,
                },
                "dry_run": True,
            },
        )
        assert execute_response.status_code == httpx.codes.OK
        payload = execute_response.json()
        assert payload["status"] == "succeeded"
        assert payload["result"]["plugin"] == "autodiscover"
        assert payload["result"]["dry_run"] is True
        assert payload["result"]["action"] == "autodiscover.scan"


async def test_execute_kill_switch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = (tmp_path / "oko.sqlite3").resolve()
    bootstrap = (tmp_path / "bootstrap.yaml").resolve()
    bootstrap.write_text(DEFAULT_BOOTSTRAP, encoding="utf-8")

    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("BROKER_URL", "memory://local")
    monkeypatch.setenv("OKO_BOOTSTRAP_CONFIG_FILE", str(bootstrap))
    monkeypatch.setenv("OKO_ACTIONS_EXECUTE_ENABLED", "false")

    main_module = _reload_main_module()
    headers = _full_headers()

    async for client in _client(main_module):
        execute_response = await client.post(
            "/api/v1/actions/execute",
            headers=headers,
            json={
                "type": "system.echo",
                "requested_by": "tester",
                "capability": "exec.system.echo",
                "payload": {"hello": "world"},
                "dry_run": False,
            },
        )
        assert execute_response.status_code == httpx.codes.SERVICE_UNAVAILABLE
        assert execute_response.json()["code"] == "execute_disabled"


async def test_events_stream_once_returns_snapshot(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = (tmp_path / "oko.sqlite3").resolve()
    bootstrap = (tmp_path / "bootstrap.yaml").resolve()
    bootstrap.write_text(DEFAULT_BOOTSTRAP, encoding="utf-8")

    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("BROKER_URL", "memory://local")
    monkeypatch.setenv("OKO_BOOTSTRAP_CONFIG_FILE", str(bootstrap))

    main_module = _reload_main_module()
    headers = _full_headers()

    async for client in _client(main_module):
        async with client.stream("GET", "/api/v1/events/stream?once=true", headers=headers) as response:
            assert response.status_code == httpx.codes.OK
            payload = ""
            async for chunk in response.aiter_text():
                payload += chunk
            assert "event: core.state.snapshot" in payload
            assert "active_revision" in payload


async def test_favicon_proxy_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = (tmp_path / "oko.sqlite3").resolve()
    bootstrap = (tmp_path / "bootstrap.yaml").resolve()
    media_dir = (tmp_path / "media").resolve()
    bootstrap.write_text(DEFAULT_BOOTSTRAP, encoding="utf-8")

    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("BROKER_URL", "memory://local")
    monkeypatch.setenv("OKO_BOOTSTRAP_CONFIG_FILE", str(bootstrap))
    monkeypatch.setenv("OKO_MEDIA_DIR", str(media_dir))
    monkeypatch.setenv("OKO_FAVICON_CACHE_TTL_DAYS", "7")

    main_module = _reload_main_module()
    fetch_calls = 0

    async def _fake_fetch(origin: str, **_: object) -> tuple[bytes, str]:
        nonlocal fetch_calls
        fetch_calls += 1
        assert origin == "https://demo.local"
        return b"ico-bytes", "image/x-icon"

    monkeypatch.setattr("api.v1.core._fetch_origin_favicon", _fake_fetch)

    async for client in _client(main_module):
        response_first = await client.get("/api/v1/favicon", params={"url": "https://demo.local/some/path"})
        assert response_first.status_code == httpx.codes.TEMPORARY_REDIRECT
        location_first = response_first.headers["location"]
        assert location_first.startswith("/media/favicons/")
        cached_file = media_dir / location_first.removeprefix("/media/")
        assert cached_file.read_bytes() == b"ico-bytes"

        response_second = await client.get("/api/v1/favicon", params={"url": "https://demo.local/another/path"})
        assert response_second.status_code == httpx.codes.TEMPORARY_REDIRECT
        assert response_second.headers["location"] == location_first
        assert fetch_calls == 1

        stale_ts = (datetime.now(UTC) - timedelta(days=8)).timestamp()
        os.utime(cached_file, (stale_ts, stale_ts))

        response_third = await client.get("/api/v1/favicon", params={"url": "https://demo.local"})
        assert response_third.status_code == httpx.codes.TEMPORARY_REDIRECT
        assert response_third.headers["location"].startswith("/media/favicons/")
        assert fetch_calls == 2


async def test_favicon_proxy_rejects_invalid_url(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = (tmp_path / "oko.sqlite3").resolve()
    bootstrap = (tmp_path / "bootstrap.yaml").resolve()
    bootstrap.write_text(DEFAULT_BOOTSTRAP, encoding="utf-8")

    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("BROKER_URL", "memory://local")
    monkeypatch.setenv("OKO_BOOTSTRAP_CONFIG_FILE", str(bootstrap))
    monkeypatch.setenv("OKO_MEDIA_DIR", str((tmp_path / "media").resolve()))

    main_module = _reload_main_module()

    async for client in _client(main_module):
        response = await client.get("/api/v1/favicon", params={"url": "file:///etc/passwd"})
        assert response.status_code == httpx.codes.BAD_REQUEST
        assert response.json()["detail"] == "Only http/https URLs with host are supported"


async def test_favicon_proxy_passes_upstream_errors(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db_path = (tmp_path / "oko.sqlite3").resolve()
    bootstrap = (tmp_path / "bootstrap.yaml").resolve()
    media_dir = (tmp_path / "media").resolve()
    bootstrap.write_text(DEFAULT_BOOTSTRAP, encoding="utf-8")

    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("BROKER_URL", "memory://local")
    monkeypatch.setenv("OKO_BOOTSTRAP_CONFIG_FILE", str(bootstrap))
    monkeypatch.setenv("OKO_MEDIA_DIR", str(media_dir))

    main_module = _reload_main_module()

    async def _fake_fail(_origin: str, **_: object) -> tuple[bytes, str]:
        raise HTTPException(status_code=404, detail="Favicon not found")

    monkeypatch.setattr("api.v1.core._fetch_origin_favicon", _fake_fail)

    async for client in _client(main_module):
        response = await client.get("/api/v1/favicon", params={"url": "https://demo.local"})
        assert response.status_code == httpx.codes.NOT_FOUND
        assert response.json()["detail"] == "Favicon not found"

        stale_file = media_dir / "favicons" / "fallback.ico"
        stale_file.parent.mkdir(parents=True, exist_ok=True)
        stale_file.write_bytes(b"stale")
        monkeypatch.setattr(
            "api.v1.core._find_cached_favicon",
            lambda *_args, _stale_file=stale_file, **_kwargs: _stale_file,
        )
        monkeypatch.setattr("api.v1.core._cache_is_fresh", lambda *_args, **_kwargs: False)

        stale_response = await client.get("/api/v1/favicon", params={"url": "https://demo.local"})
        assert stale_response.status_code == httpx.codes.TEMPORARY_REDIRECT
        assert stale_response.headers["location"] == "/media/favicons/fallback.ico"
