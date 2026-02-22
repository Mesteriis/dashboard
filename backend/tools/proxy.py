from __future__ import annotations

from collections.abc import Mapping, Sequence
from http.cookies import SimpleCookie
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx

PROXY_REQUEST_HEADERS = {
    "accept",
    "accept-language",
    "cache-control",
    "content-type",
    "cookie",
    "if-modified-since",
    "if-none-match",
    "pragma",
    "range",
    "referer",
    "user-agent",
}

PROXY_RESPONSE_HEADERS = {
    "content-type",
    "cache-control",
    "etag",
    "expires",
    "last-modified",
    "content-range",
    "accept-ranges",
    "location",
}


async def close_upstream_resources(
    upstream_response: httpx.Response,
    client: httpx.AsyncClient,
) -> None:
    try:
        await upstream_response.aclose()
    finally:
        await client.aclose()


def build_upstream_url(
    base_url: str,
    proxy_path: str,
    request_query: Sequence[tuple[str, str]],
    auth_query: Mapping[str, str],
) -> str:
    parsed = urlsplit(base_url)
    base_path = parsed.path.rstrip("/")
    target_path = f"{base_path}/{proxy_path}" if proxy_path else base_path

    merged_query = parse_qsl(parsed.query, keep_blank_values=True)
    merged_query.extend(request_query)
    merged_query.extend(auth_query.items())

    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            target_path or "/",
            urlencode(merged_query, doseq=True),
            "",
        )
    )


def rewrite_location(location: str, item_url: str, item_id: str) -> str:
    proxy_base = f"/api/v1/dashboard/iframe/{item_id}/proxy"
    item_parsed = urlsplit(item_url)
    item_origin = f"{item_parsed.scheme}://{item_parsed.netloc}"

    if location.startswith(item_origin):
        suffix = location[len(item_origin) :]
        return f"{proxy_base}{suffix if suffix.startswith('/') else '/' + suffix}"

    if location.startswith("/"):
        return f"{proxy_base}{location}"

    return f"{proxy_base}/{location}"


def rewrite_set_cookie(set_cookie_value: str, item_id: str) -> list[str]:
    cookie = SimpleCookie()
    try:
        cookie.load(set_cookie_value)
    except Exception:
        return [set_cookie_value]

    if not cookie:
        return [set_cookie_value]

    proxy_base = f"/api/v1/dashboard/iframe/{item_id}/proxy"
    rewritten: list[str] = []
    for morsel in cookie.values():
        morsel["domain"] = ""
        raw_path = morsel["path"] or "/"
        if not raw_path.startswith("/"):
            raw_path = "/" + raw_path
        morsel["path"] = proxy_base if raw_path == "/" else f"{proxy_base}{raw_path}"
        rewritten.append(morsel.OutputString())

    return rewritten or [set_cookie_value]


def filter_cookie_header(cookie_header: str | None, blocked_cookie_names: set[str]) -> str | None:
    if not cookie_header:
        return None

    if not blocked_cookie_names:
        return cookie_header

    cookie = SimpleCookie()
    try:
        cookie.load(cookie_header)
    except Exception:
        return cookie_header

    allowed_parts: list[str] = []
    for key, morsel in cookie.items():
        if key in blocked_cookie_names:
            continue
        allowed_parts.append(f"{key}={morsel.value}")

    if not allowed_parts:
        return None
    return "; ".join(allowed_parts)
