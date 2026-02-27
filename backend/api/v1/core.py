from __future__ import annotations

import asyncio
import hashlib
import ssl
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import httpx
from core.contracts.models import (
    ConfigImportRequest,
    ConfigPatchRequest,
    ConfigRevision,
    ConfigRollbackRequest,
    ConfigStateResponse,
    ConfigValidateRequest,
    ConfigValidationResponse,
    EventEnvelope,
    WidgetRegistryEntry,
)
from core.events.sse import format_sse_event
from core.security import (
    ActorDep,
    require_config,
    require_config_import,
    require_config_patch,
    require_config_revisions,
    require_config_rollback,
    require_events,
    require_state,
    require_widgets_registry,
)
from depends.v1.core_deps import ConfigServiceDep, ContainerDep
from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse, StreamingResponse

core_router = APIRouter(tags=["core"])


@core_router.get("/health")
async def get_health(container: ContainerDep) -> dict[str, object]:
    return {
        "ok": True,
        "role": container.settings.runtime_role,
        "ts": datetime.now(UTC).isoformat(),
    }


def _origin_from_service_url(raw_url: str) -> str:
    parsed = urlparse(raw_url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Only http/https URLs with host are supported")
    if parsed.username or parsed.password:
        raise HTTPException(status_code=400, detail="URLs with credentials are not allowed")
    return f"{parsed.scheme}://{parsed.netloc}"


def _is_tls_verify_failure(exc: httpx.ConnectError) -> bool:
    cause = exc.__cause__
    if isinstance(cause, ssl.SSLCertVerificationError):
        return True
    if isinstance(cause, ssl.SSLError):
        message = str(cause).lower()
        return "certificate verify failed" in message
    return "certificate verify failed" in str(exc).lower()


def _favicon_cache_key(origin: str) -> str:
    digest = hashlib.sha256(origin.encode("utf-8")).hexdigest()
    return digest[:32]


def _favicon_ext(media_type: str) -> str:
    normalized = media_type.split(";", 1)[0].strip().lower()
    if normalized in {"image/x-icon", "image/vnd.microsoft.icon"}:
        return "ico"
    if normalized == "image/png":
        return "png"
    if normalized == "image/svg+xml":
        return "svg"
    if normalized == "image/jpeg":
        return "jpg"
    if normalized == "image/webp":
        return "webp"
    if normalized == "image/gif":
        return "gif"
    return "ico"


def _find_cached_favicon(cache_dir: Path, key: str) -> Path | None:
    candidates = sorted(cache_dir.glob(f"{key}.*"), key=lambda path: path.stat().st_mtime, reverse=True)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _missing_favicon_marker_path(cache_dir: Path, key: str) -> Path:
    return cache_dir / f".{key}.missing"


def _cache_is_fresh(path: Path, ttl: timedelta) -> bool:
    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    return datetime.now(UTC) - modified < ttl


def _has_fresh_missing_favicon_marker(cache_dir: Path, key: str, ttl: timedelta) -> bool:
    marker = _missing_favicon_marker_path(cache_dir, key)
    return marker.is_file() and _cache_is_fresh(marker, ttl)


def _touch_missing_favicon_marker(cache_dir: Path, key: str) -> None:
    marker = _missing_favicon_marker_path(cache_dir, key)
    marker.write_text("missing", encoding="utf-8")


def _clear_missing_favicon_marker(cache_dir: Path, key: str) -> None:
    marker = _missing_favicon_marker_path(cache_dir, key)
    marker.unlink(missing_ok=True)


def _media_url(path: Path, media_dir: Path) -> str:
    relative = path.relative_to(media_dir)
    return f"/media/{relative.as_posix()}"


def _write_cached_favicon(cache_dir: Path, key: str, body: bytes, media_type: str) -> Path:
    ext = _favicon_ext(media_type)
    target = cache_dir / f"{key}.{ext}"
    temp = cache_dir / f".{key}.{ext}.tmp"
    temp.write_bytes(body)
    temp.replace(target)
    for candidate in cache_dir.glob(f"{key}.*"):
        if candidate == target:
            continue
        if candidate.is_file():
            candidate.unlink(missing_ok=True)
    return target


async def _fetch_origin_favicon(
    origin: str,
    *,
    timeout_sec: float,
    max_bytes: int,
    tls_verify: bool,
    tls_insecure_fallback: bool,
) -> tuple[bytes, str]:
    favicon_url = f"{origin.rstrip('/')}/favicon.ico"
    verify_attempts: list[bool] = [tls_verify]
    if tls_verify and tls_insecure_fallback:
        verify_attempts.append(False)

    response: httpx.Response | None = None
    last_error: Exception | None = None
    for verify in verify_attempts:
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=timeout_sec, verify=verify) as client:
                response = await client.get(
                    favicon_url,
                    headers={
                        "accept": "image/*,*/*;q=0.8",
                        "user-agent": "oko-favicon-proxy/1.0",
                    },
                )
            break
        except httpx.ConnectError as exc:
            last_error = exc
            if (
                verify
                and tls_insecure_fallback
                and _is_tls_verify_failure(exc)
            ):
                continue
            raise HTTPException(status_code=502, detail="Failed to connect to favicon upstream") from exc
        except httpx.TimeoutException as exc:
            raise HTTPException(status_code=504, detail="Favicon upstream timeout") from exc
        except httpx.HTTPError as exc:
            last_error = exc
            raise HTTPException(status_code=502, detail="Failed to fetch favicon from upstream") from exc

    if response is None:
        raise HTTPException(status_code=502, detail="Failed to fetch favicon from upstream") from last_error

    if response.status_code >= 400:
        raise HTTPException(status_code=404, detail="Favicon not found")

    body = response.content
    if not body:
        raise HTTPException(status_code=404, detail="Favicon not found")
    if len(body) > max_bytes:
        raise HTTPException(status_code=413, detail="Favicon is too large")

    content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if not content_type.startswith("image/"):
        content_type = "image/x-icon"
    return body, content_type


@core_router.get("/favicon")
async def get_favicon(
    container: ContainerDep,
    url: str = Query(..., min_length=1, max_length=2048),
) -> Response:
    origin = _origin_from_service_url(url)
    media_dir = container.settings.media_dir
    cache_dir = media_dir / "favicons"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_ttl = timedelta(days=container.settings.favicon_cache_ttl_days)
    cache_key = _favicon_cache_key(origin)
    cached = _find_cached_favicon(cache_dir, cache_key)

    if cached and _cache_is_fresh(cached, cache_ttl):
        return RedirectResponse(url=_media_url(cached, media_dir), status_code=307)
    if _has_fresh_missing_favicon_marker(cache_dir, cache_key, cache_ttl):
        raise HTTPException(status_code=404, detail="Favicon not found")

    try:
        body, media_type = await _fetch_origin_favicon(
            origin,
            timeout_sec=container.settings.favicon_timeout_sec,
            max_bytes=container.settings.favicon_max_bytes,
            tls_verify=container.settings.favicon_tls_verify,
            tls_insecure_fallback=container.settings.favicon_tls_insecure_fallback,
        )
    except HTTPException as exc:
        if exc.status_code == 404:
            _touch_missing_favicon_marker(cache_dir, cache_key)
        if cached:
            return RedirectResponse(url=_media_url(cached, media_dir), status_code=307)
        raise

    _clear_missing_favicon_marker(cache_dir, cache_key)
    cached_path = _write_cached_favicon(cache_dir, cache_key, body, media_type)
    return RedirectResponse(url=_media_url(cached_path, media_dir), status_code=307)


@core_router.get("/state")
async def get_state(
    config_service: ConfigServiceDep,
    _capability: str = require_state,
) -> dict[str, object]:
    state = await config_service.get_active_state()
    return state.active_state.model_dump(mode="json")


@core_router.get("/config")
async def get_config(
    config_service: ConfigServiceDep,
    _capability: str = require_config,
) -> dict[str, object]:
    return await config_service.get_active_revision()


@core_router.post("/config/import", response_model=ConfigStateResponse)
async def import_config(
    payload: ConfigImportRequest,
    config_service: ConfigServiceDep,
    actor: ActorDep,
    _capability: str = require_config_import,
) -> ConfigStateResponse:
    return await config_service.import_config(request=payload, actor=actor)


@core_router.post("/config/validate", response_model=ConfigValidationResponse)
async def validate_config(
    payload: ConfigValidateRequest,
    config_service: ConfigServiceDep,
    _capability: str = require_config_import,
) -> ConfigValidationResponse:
    return config_service.validate_config(request=payload)


@core_router.post("/config/patch", response_model=ConfigStateResponse)
async def patch_config(
    payload: ConfigPatchRequest,
    config_service: ConfigServiceDep,
    actor: ActorDep,
    _capability: str = require_config_patch,
) -> ConfigStateResponse:
    return await config_service.patch_config(request=payload, actor=actor)


@core_router.post("/config/rollback", response_model=ConfigStateResponse)
async def rollback_config(
    payload: ConfigRollbackRequest,
    config_service: ConfigServiceDep,
    actor: ActorDep,
    _capability: str = require_config_rollback,
) -> ConfigStateResponse:
    return await config_service.rollback(request=payload, actor=actor)


@core_router.get("/config/revisions", response_model=list[ConfigRevision])
async def get_config_revisions(
    config_service: ConfigServiceDep,
    _capability: str = require_config_revisions,
    limit: int = Query(default=50, ge=1, le=500),
) -> list[ConfigRevision]:
    rows = await config_service.list_revisions(limit=limit)
    return [ConfigRevision.model_validate(row) for row in rows]


@core_router.get("/widgets/registry", response_model=list[WidgetRegistryEntry])
async def get_widgets_registry(
    config_service: ConfigServiceDep,
    _capability: str = require_widgets_registry,
) -> list[WidgetRegistryEntry]:
    return await config_service.widgets_registry()


@core_router.get("/events/stream")
async def stream_events(
    request: Request,
    container: ContainerDep,
    _capability: str = require_events,
    once: bool = Query(default=False, description="Return initial snapshot event and close"),
) -> StreamingResponse:
    queue = container.event_bus.subscribe()

    async def _stream() -> AsyncIterator[str]:
        try:
            active = await container.config_service.get_active_state()
            initial = EventEnvelope(
                id=uuid4(),
                type="core.state.snapshot",
                event_version=1,
                revision=active.active_state.state_seq,
                ts=datetime.now(UTC),
                source="core.events",
                payload={
                    "active_revision": active.active_state.active_revision,
                    "state_seq": active.active_state.state_seq,
                },
            )
            yield format_sse_event(initial)
            health_items = await container.health_repository.list_snapshot_items()
            health_snapshot = EventEnvelope(
                id=uuid4(),
                type="health.state.snapshot",
                event_version=1,
                revision=initial.revision,
                ts=datetime.now(UTC),
                source="apps.health.snapshot",
                payload={
                    "items": health_items,
                },
            )
            yield format_sse_event(health_snapshot)
            if once:
                return

            while True:
                if await request.is_disconnected():
                    return
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=container.settings.event_stream_keepalive_sec)
                except TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                yield format_sse_event(event)
        finally:
            container.event_bus.unsubscribe(queue)

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "cache-control": "no-cache, no-transform",
            "connection": "keep-alive",
            "x-accel-buffering": "no",
        },
    )


__all__ = ["core_router"]
