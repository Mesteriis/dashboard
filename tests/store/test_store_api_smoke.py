from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from store.main import app

pytestmark = pytest.mark.asyncio


async def test_store_health_endpoint() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert isinstance(payload.get("plugins_count"), int)


async def test_store_plugins_list_contract() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/plugins")

    assert response.status_code == 200
    payload = response.json()
    assert "plugins" in payload
    assert "total" in payload
    assert isinstance(payload["plugins"], list)
    assert payload["total"] == len(payload["plugins"])
