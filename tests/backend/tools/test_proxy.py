from __future__ import annotations

import pytest

from tools.proxy import build_upstream_url, close_upstream_resources, rewrite_location, rewrite_set_cookie


def test_build_upstream_url_merges_base_request_and_auth_query() -> None:
    upstream = build_upstream_url(
        base_url="https://example.local/base/path?from_base=1",
        proxy_path="metrics",
        request_query={"q": "value"},
        auth_query={"token": "secret"},
    )

    assert upstream == "https://example.local/base/path/metrics?from_base=1&q=value&token=secret"


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        ("https://example.local/login", "/api/v1/dashboard/iframe/grafana/proxy/login"),
        ("/login", "/api/v1/dashboard/iframe/grafana/proxy/login"),
        ("login", "/api/v1/dashboard/iframe/grafana/proxy/login"),
    ],
)
def test_rewrite_location_maps_upstream_to_proxy(location: str, expected: str) -> None:
    rewritten = rewrite_location(
        location=location,
        item_url="https://example.local/",
        item_id="grafana",
    )
    assert rewritten == expected


def test_rewrite_set_cookie_removes_domain_and_scopes_path() -> None:
    rewritten = rewrite_set_cookie(
        "session=abc123; Domain=example.local; Path=/; HttpOnly; Secure",
        item_id="grafana",
    )

    assert len(rewritten) == 1
    cookie = rewritten[0]
    assert "session=abc123" in cookie
    assert "Domain=" not in cookie
    assert "Path=/api/v1/dashboard/iframe/grafana/proxy" in cookie


def test_rewrite_set_cookie_returns_original_for_invalid_cookie() -> None:
    raw = "not-a-cookie"
    assert rewrite_set_cookie(raw, item_id="grafana") == [raw]


@pytest.mark.asyncio
async def test_close_upstream_resources_closes_response_and_client() -> None:
    class DummyResponse:
        def __init__(self) -> None:
            self.closed = False

        async def aclose(self) -> None:
            self.closed = True

    class DummyClient:
        def __init__(self) -> None:
            self.closed = False

        async def aclose(self) -> None:
            self.closed = True

    response = DummyResponse()
    client = DummyClient()
    await close_upstream_resources(response, client)  # type: ignore[arg-type]
    assert response.closed is True
    assert client.closed is True
