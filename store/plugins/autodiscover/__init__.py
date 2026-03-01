from __future__ import annotations

import asyncio
import logging
import os
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

from core.contracts.models import ActionEnvelope

if TYPE_CHECKING:
    from core.config import ConfigService
    from core.events.protocols import EventPublisher
    from core.gateway import ActionGateway
    from core.storage import StorageRPC
else:
    ConfigService = Any
    EventPublisher = Any
    ActionGateway = Any
    StorageRPC = Any

from .constants import DEFAULT_RESULT_FILE
from .manifest import ACTION_SCAN, CAPABILITY_SCAN, PLUGIN_NAME
from .registry import register_autodiscover_actions
from .services import extract_services_from_scan_payload
from .storage import load_last_result

logger = logging.getLogger("core.plugins.autodiscover")

_action_gateway: ActionGateway | None = None
_event_bus: EventPublisher | None = None
_config_service: ConfigService | None = None
_storage_rpc: StorageRPC | None = None
_background_task: asyncio.Task[Any] | None = None
_last_sync_marker: str | None = None
_runtime_role: str | None = None
_last_services_cache: dict[str, Any] | None = None

_BACKGROUND_INTERVAL_SEC = max(60, int(os.getenv("OKO_AUTODISCOVER_BACKGROUND_SCAN_INTERVAL_SEC", "900")))
_BACKGROUND_INITIAL_DELAY_SEC = max(1, int(os.getenv("OKO_AUTODISCOVER_BACKGROUND_SCAN_INITIAL_DELAY_SEC", "15")))
_BACKGROUND_MAX_HOSTS = max(16, int(os.getenv("OKO_AUTODISCOVER_BACKGROUND_SCAN_MAX_HOSTS", "255")))
_BACKGROUND_PORTS_FROM = max(1, int(os.getenv("OKO_AUTODISCOVER_BACKGROUND_SCAN_PORTS_FROM", "1")))
_BACKGROUND_PORTS_TO = max(
    _BACKGROUND_PORTS_FROM,
    min(65535, int(os.getenv("OKO_AUTODISCOVER_BACKGROUND_SCAN_PORTS_TO", "1000"))),
)
_BACKGROUND_RUNNING_ACTION_MAX_AGE_SEC = max(
    60,
    int(os.getenv("OKO_AUTODISCOVER_BACKGROUND_RUNNING_ACTION_MAX_AGE_SEC", "600")),
)
_BACKGROUND_ROLE = (os.getenv("OKO_AUTODISCOVER_BACKGROUND_SCAN_ROLE", "worker") or "worker").strip().lower()


def _resolve_result_file() -> Path:
    plugin_dir = Path(__file__).resolve().parent
    candidates = (
        Path.cwd() / DEFAULT_RESULT_FILE,
        plugin_dir / DEFAULT_RESULT_FILE,
        plugin_dir.parent / DEFAULT_RESULT_FILE,
        plugin_dir.parent.parent / DEFAULT_RESULT_FILE,
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _summary_from_payload(result_payload: dict[str, Any], services: list[dict[str, Any]]) -> dict[str, Any]:
    hosts = result_payload.get("hosts")
    host_count = len(hosts) if isinstance(hosts, list) else 0
    return {
        "discovered_hosts": host_count,
        "discovered_services": len(services),
        "generated_at": result_payload.get("generated_at"),
        "duration_ms": result_payload.get("duration_ms"),
    }


def _as_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    token = str(value).strip()
    return token or None


def _as_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed


def _parse_datetime(value: Any) -> datetime | None:
    parsed: datetime | None = None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        token = value.strip()
        if token:
            with suppress(Exception):
                parsed = datetime.fromisoformat(token.replace("Z", "+00:00"))
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _normalized_services_from_projection(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    services: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        services.append(
            {
                "host_ip": row.get("host_ip"),
                "hostname": row.get("hostname"),
                "port": row.get("port"),
                "service": row.get("service"),
                "title": row.get("title"),
                "description": None,
                "url": row.get("url"),
                "status": row.get("status"),
                "server": row.get("server"),
            }
        )
    services.sort(
        key=lambda item: (
            str(item.get("host_ip") or ""),
            int(item.get("port") or 0),
        )
    )
    return services


def _generated_at_from_scan_run(row: dict[str, Any] | None) -> str | None:
    if not isinstance(row, dict):
        return None
    summary = row.get("summary")
    if isinstance(summary, dict):
        summary_generated_at = _as_optional_string(summary.get("generated_at"))
        if summary_generated_at:
            return summary_generated_at
    requested_at = _as_optional_string(row.get("requested_at"))
    if requested_at:
        return requested_at
    return _as_optional_string(row.get("updated_at"))


async def _resolve_latest_scan_id_from_runs() -> str | None:
    if _storage_rpc is None:
        return None

    candidates: list[tuple[datetime, str]] = []
    for status in ("completed", "synced"):
        rows: list[dict[str, Any]] = []
        with suppress(Exception):
            rows = await _storage_rpc.table_query(
                plugin_id=PLUGIN_NAME,
                table="scan_runs",
                where={"status": status},
                limit=250,
            )
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            scan_id = _as_optional_string(row.get("scan_id"))
            if not scan_id:
                continue
            generated_at = _generated_at_from_scan_run(row)
            parsed_generated_at = _parse_datetime(generated_at)
            if parsed_generated_at is None:
                continue
            candidates.append((parsed_generated_at, scan_id))

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


async def _resolve_generated_at_for_scan(scan_id: str | None) -> str | None:
    if _storage_rpc is None or not scan_id:
        return None
    with suppress(Exception):
        scan_run = await _storage_rpc.table_get(
            plugin_id=PLUGIN_NAME,
            table="scan_runs",
            pk=scan_id,
        )
        return _generated_at_from_scan_run(scan_run if isinstance(scan_run, dict) else None)
    return None


async def _persist_services_projection(*, scan_id: str, services: list[dict[str, Any]]) -> None:
    if _storage_rpc is None:
        return
    now_iso = datetime.now(UTC).isoformat()
    dedupe: set[str] = set()
    projection_write_failed = False
    for row in services:
        if not isinstance(row, dict):
            continue
        port = _as_optional_int(row.get("port"))
        if port is None:
            continue
        host_ip = _as_optional_string(row.get("host_ip"))
        service = _as_optional_string(row.get("service"))
        url = _as_optional_string(row.get("url"))
        dedupe_token = f"{host_ip or ''}:{port}:{service or ''}:{url or ''}"
        if dedupe_token in dedupe:
            continue
        dedupe.add(dedupe_token)
        if projection_write_failed:
            continue
        try:
            await _storage_rpc.table_upsert(
                plugin_id=PLUGIN_NAME,
                table="scan_services",
                row={
                    "service_key": f"{scan_id}:{dedupe_token}",
                    "scan_id": scan_id,
                    "host_ip": host_ip,
                    "hostname": _as_optional_string(row.get("hostname")),
                    "port": port,
                    "service": service,
                    "title": _as_optional_string(row.get("title")),
                    "url": url,
                    "status": _as_optional_string(row.get("status")),
                    "server": _as_optional_string(row.get("server")),
                    "updated_at": now_iso,
                },
            )
        except Exception as exc:
            projection_write_failed = True
            logger.warning(
                "Autodiscover could not write scan_services projection scan_id=%s: %s",
                scan_id,
                exc,
            )


async def _sync_result_to_storage() -> None:
    global _last_sync_marker

    if _storage_rpc is None:
        return

    payload = load_last_result(_resolve_result_file())
    if not isinstance(payload, dict):
        return

    generated_at_value = payload.get("generated_at")
    if isinstance(generated_at_value, str) and generated_at_value.strip():
        marker = generated_at_value.strip()
    else:
        marker = f"sync:{datetime.now(UTC).isoformat()}"

    if marker == _last_sync_marker:
        return

    scan_id = f"legacy:{marker}"
    services = extract_services_from_scan_payload(payload)
    summary = _summary_from_payload(payload, services)
    now_iso = datetime.now(UTC).isoformat()
    requested_at = marker if marker.startswith("20") else now_iso

    await _persist_services_projection(scan_id=scan_id, services=services)
    await _storage_rpc.kv_set(
        plugin_id=PLUGIN_NAME,
        key="last_scan_summary",
        value=summary,
    )
    await _storage_rpc.kv_set(
        plugin_id=PLUGIN_NAME,
        key="last_scan_id",
        value=scan_id,
    )
    await _storage_rpc.table_upsert(
        plugin_id=PLUGIN_NAME,
        table="scan_runs",
        row={
            "scan_id": scan_id,
            "status": "synced",
            "dry_run": False,
            "requested_at": requested_at,
            "updated_at": now_iso,
            "summary": summary,
        },
    )
    _last_sync_marker = marker
    logger.info(
        "Autodiscover legacy sync stored scan_id=%s services=%s generated_at=%s",
        scan_id,
        len(services),
        marker,
    )


async def _run_scheduled_scan_once() -> bool:
    if _action_gateway is None:
        logger.info("Autodiscover background scan skipped: action gateway is not available")
        return False

    now_utc = datetime.now(UTC)
    with suppress(Exception):
        history = await _action_gateway.history(limit=50)
        if isinstance(history, list):
            for entry in history:
                if not isinstance(entry, dict):
                    continue
                if str(entry.get("type") or "") != ACTION_SCAN:
                    continue
                status = str(entry.get("status") or "").lower()
                requested_by = str(entry.get("requested_by") or "")
                if requested_by == f"plugin.{PLUGIN_NAME}.scheduler" and status in {
                    "queued",
                    "validated",
                    "running",
                }:
                    age_sec = 0
                    requested_at_raw = entry.get("requested_at")
                    requested_at_dt: datetime | None = None
                    if isinstance(requested_at_raw, datetime):
                        requested_at_dt = requested_at_raw
                    elif isinstance(requested_at_raw, str):
                        with suppress(Exception):
                            requested_at_dt = datetime.fromisoformat(
                                requested_at_raw.replace("Z", "+00:00"),
                            )
                    if requested_at_dt is not None:
                        if requested_at_dt.tzinfo is None:
                            requested_at_dt = requested_at_dt.replace(tzinfo=UTC)
                        age_sec = max(0, int((now_utc - requested_at_dt).total_seconds()))
                    if age_sec > _BACKGROUND_RUNNING_ACTION_MAX_AGE_SEC:
                        logger.warning(
                            "Autodiscover found stale scheduler action id=%s status=%s age_sec=%s, starting new scan",
                            entry.get("id"),
                            status,
                            age_sec,
                        )
                        continue
                    logger.info(
                        "Autodiscover background scan skipped: scheduler action id=%s status=%s age_sec=%s",
                        entry.get("id"),
                        status,
                        age_sec,
                    )
                    return False

    actor = f"plugin.{PLUGIN_NAME}.scheduler"
    action = ActionEnvelope(
        type=ACTION_SCAN,
        requested_by=actor,
        capability=CAPABILITY_SCAN,
        payload={
            "max_hosts": _BACKGROUND_MAX_HOSTS,
            "ports_from": _BACKGROUND_PORTS_FROM,
            "ports_to": _BACKGROUND_PORTS_TO,
            "include_http_services": True,
            "include_dashboard_items": True,
        },
        dry_run=False,
    )
    logger.info(
        "Autodiscover background scan enqueue actor=%s max_hosts=%s ports=%s-%s",
        actor,
        _BACKGROUND_MAX_HOSTS,
        _BACKGROUND_PORTS_FROM,
        _BACKGROUND_PORTS_TO,
    )
    await _action_gateway.execute_action(action=action, actor=actor)
    logger.info(
        "Autodiscover background scan action dispatched action_id=%s action_type=%s actor=%s",
        action.id,
        ACTION_SCAN,
        actor,
    )
    return True


async def _background_worker() -> None:
    first_run_at = datetime.now(UTC) + timedelta(seconds=_BACKGROUND_INITIAL_DELAY_SEC)
    logger.info(
        "Autodiscover background worker started interval_sec=%s initial_delay_sec=%s max_hosts=%s first_run_at=%s",
        _BACKGROUND_INTERVAL_SEC,
        _BACKGROUND_INITIAL_DELAY_SEC,
        _BACKGROUND_MAX_HOSTS,
        first_run_at.isoformat(),
    )
    await asyncio.sleep(_BACKGROUND_INITIAL_DELAY_SEC)
    cycle = 0
    while True:
        cycle += 1
        cycle_started_at = datetime.now(UTC)
        try:
            logger.info(
                "Autodiscover background cycle started cycle=%s started_at=%s",
                cycle,
                cycle_started_at.isoformat(),
            )
            await _sync_result_to_storage()
            dispatched = await _run_scheduled_scan_once()
            next_run_at = datetime.now(UTC) + timedelta(seconds=_BACKGROUND_INTERVAL_SEC)
            logger.info(
                "Autodiscover background cycle completed cycle=%s scan_dispatched=%s next_run_at=%s due_in_sec=%s",
                cycle,
                dispatched,
                next_run_at.isoformat(),
                _BACKGROUND_INTERVAL_SEC,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Autodiscover background worker cycle failed")
        await asyncio.sleep(_BACKGROUND_INTERVAL_SEC)


def setup(
    action_gateway: ActionGateway | None = None,
    event_bus: EventPublisher | None = None,
    config_service: ConfigService | None = None,
    storage_rpc: StorageRPC | None = None,
    runtime_role: str | None = None,
) -> None:
    global _action_gateway, _event_bus, _config_service, _storage_rpc, _runtime_role

    _action_gateway = action_gateway
    _event_bus = event_bus
    _config_service = config_service
    _storage_rpc = storage_rpc
    _runtime_role = runtime_role

    if _action_gateway is not None and _event_bus is not None:
        register_autodiscover_actions(
            _action_gateway,
            event_bus=_event_bus,
            config_service=_config_service,
            storage_rpc=_storage_rpc,
        )


def teardown() -> None:
    global _action_gateway, _event_bus, _config_service, _storage_rpc, _background_task

    if _background_task is not None and not _background_task.done():
        _background_task.cancel()

    _background_task = None
    _action_gateway = None
    _event_bus = None
    _config_service = None
    _storage_rpc = None


async def on_startup() -> None:
    global _background_task

    role = (_runtime_role or "unknown").strip().lower()
    if _BACKGROUND_ROLE != "any" and role != _BACKGROUND_ROLE:
        logger.info(
            "Autodiscover background worker skipped runtime_role=%s expected_role=%s",
            role,
            _BACKGROUND_ROLE,
        )
        return

    await _sync_result_to_storage()

    if _background_task is not None and not _background_task.done():
        return
    _background_task = asyncio.create_task(
        _background_worker(),
        name="autodiscover-background-worker",
    )
    logger.info("Autodiscover background worker task created runtime_role=%s", role)


async def on_shutdown() -> None:
    global _background_task

    if _background_task is None:
        return
    _background_task.cancel()
    with suppress(asyncio.CancelledError, TimeoutError):
        await asyncio.wait_for(_background_task, timeout=2.0)
    _background_task = None


async def get_services() -> dict[str, Any]:
    global _last_services_cache

    if _storage_rpc is None:
        return {
            "services": [],
            "total": 0,
            "generated_at": datetime.now(UTC).isoformat(),
        }

    services: list[dict[str, Any]] | None = None
    generated_at: str | None = None
    scan_id: str | None = None
    projection_used = False
    storage_errors = 0

    async def _safe_kv_get(key: str) -> Any | None:
        nonlocal storage_errors
        try:
            return await _storage_rpc.kv_get(plugin_id=PLUGIN_NAME, key=key)
        except Exception as exc:
            storage_errors += 1
            logger.warning("Autodiscover storage read timeout/failure op=kv.get key=%s: %s", key, exc)
            return None

    async def _safe_table_query(*, table: str, where: dict[str, Any], limit: int | None = None) -> list[dict[str, Any]]:
        nonlocal storage_errors
        try:
            rows = await _storage_rpc.table_query(
                plugin_id=PLUGIN_NAME,
                table=table,
                where=where,
                limit=limit,
            )
            if not isinstance(rows, list):
                return []
            return [row for row in rows if isinstance(row, dict)]
        except Exception as exc:
            storage_errors += 1
            logger.warning("Autodiscover storage read timeout/failure op=table.query table=%s: %s", table, exc)
            return []

    async def _safe_kv_set(key: str, value: Any) -> None:
        nonlocal storage_errors
        try:
            await _storage_rpc.kv_set(plugin_id=PLUGIN_NAME, key=key, value=value)
        except Exception as exc:
            storage_errors += 1
            logger.warning("Autodiscover storage write timeout/failure op=kv.set key=%s: %s", key, exc)

    last_scan_id = await _safe_kv_get("last_scan_id")
    if isinstance(last_scan_id, str) and last_scan_id.strip():
        scan_id = last_scan_id.strip()
    else:
        scan_id = await _resolve_latest_scan_id_from_runs()

    if scan_id:
        rows = await _safe_table_query(
            table="scan_services",
            where={"scan_id": scan_id},
        )
        if isinstance(rows, list) and rows:
            services = _normalized_services_from_projection(rows)
            projection_used = True
        else:
            logger.info("Autodiscover services projection is empty for scan_id=%s", scan_id)
            fallback_scan_id = await _resolve_latest_scan_id_from_runs()
            if fallback_scan_id and fallback_scan_id != scan_id:
                fallback_rows = await _safe_table_query(
                    table="scan_services",
                    where={"scan_id": fallback_scan_id},
                )
                if isinstance(fallback_rows, list) and fallback_rows:
                    services = _normalized_services_from_projection(fallback_rows)
                    scan_id = fallback_scan_id
                    projection_used = True
                    await _safe_kv_set("last_scan_id", fallback_scan_id)
                    logger.warning(
                        "Autodiscover services self-healed last_scan_id to %s",
                        fallback_scan_id,
                    )

        generated_at = await _resolve_generated_at_for_scan(scan_id)

    if services is None:
        kv_services = await _safe_kv_get("services_latest")
        if isinstance(kv_services, list):
            services = [row for row in kv_services if isinstance(row, dict)]
            if services:
                logger.warning("Autodiscover services fallback used: KV services_latest")

    summary_payload = await _safe_kv_get("last_scan_summary")
    if generated_at is None and isinstance(summary_payload, dict):
        generated_at = _as_optional_string(summary_payload.get("generated_at"))

    if not isinstance(services, list):
        result_payload = await _safe_kv_get("last_scan_result")
        services = extract_services_from_scan_payload(result_payload if isinstance(result_payload, dict) else None)
        if generated_at is None and isinstance(result_payload, dict):
            generated_at = _as_optional_string(result_payload.get("generated_at"))
        if services:
            logger.warning("Autodiscover services fallback used: KV last_scan_result")

    if storage_errors > 0 and (not services):
        cached_services = _last_services_cache.get("services") if isinstance(_last_services_cache, dict) else None
        if isinstance(cached_services, list):
            logger.warning(
                "Autodiscover services served from in-memory cache due to storage errors=%s",
                storage_errors,
            )
            return dict(_last_services_cache)

    response = {
        "services": services,
        "total": len(services),
        "generated_at": generated_at or datetime.now(UTC).isoformat(),
    }
    if isinstance(services, list) and (services or projection_used):
        _last_services_cache = dict(response)
    return response


__all__ = [
    "get_services",
    "on_shutdown",
    "on_startup",
    "register_autodiscover_actions",
    "setup",
    "teardown",
]
