from __future__ import annotations

import logging
from contextlib import suppress
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from core.contracts.errors import ApiError
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

from .plugin import (
    ACTION_SCAN,
    ACTIONS,
    EVENT_HOST_FOUND,
    EVENT_SCAN_COMPLETED,
    EVENT_SCAN_FAILED,
    EVENT_SCAN_PROGRESS,
    EVENT_SCAN_STARTED,
    EVENT_SERVICE_FOUND,
    PLUGIN_NAME,
    execute_scan,
)
from .services import extract_services_from_scan_payload

logger = logging.getLogger("core.plugins.autodiscover")


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


async def _persist_scan_services(
    *,
    scan_id: str,
    services: list[dict[str, Any]],
    storage_rpc: StorageRPC | None,
) -> int:
    if storage_rpc is None:
        return 0

    now_iso = datetime.now(UTC).isoformat()
    dedupe: set[str] = set()
    persisted_rows = 0
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

        service_key = f"{scan_id}:{dedupe_token}"
        await storage_rpc.table_upsert(
            plugin_id=PLUGIN_NAME,
            table="scan_services",
            row={
                "service_key": service_key,
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
        persisted_rows += 1
    return persisted_rows


async def _persist_scan_snapshot(
    *,
    action: ActionEnvelope,
    status: str,
    summary: dict[str, Any],
    result_payload: dict[str, Any] | None,
    storage_rpc: StorageRPC | None,
) -> None:
    if storage_rpc is None:
        return

    scan_id = str(action.id)
    generated_at = None
    if isinstance(result_payload, dict):
        generated_at_value = result_payload.get("generated_at")
        if isinstance(generated_at_value, str) and generated_at_value.strip():
            generated_at = generated_at_value.strip()

    await storage_rpc.table_upsert(
        plugin_id=PLUGIN_NAME,
        table="scan_runs",
        row={
            "scan_id": scan_id,
            "status": status,
            "dry_run": bool(action.dry_run),
            "requested_at": generated_at or action.requested_at.isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "summary": summary,
        },
    )
    if status not in {"completed", "synced"}:
        logger.info("Autodiscover scan snapshot stored scan_id=%s status=%s", scan_id, status)
        return

    await storage_rpc.kv_set(
        plugin_id=PLUGIN_NAME,
        key="last_scan_summary",
        value=summary,
    )
    await storage_rpc.kv_set(
        plugin_id=PLUGIN_NAME,
        key="last_scan_id",
        value=scan_id,
    )

    if not isinstance(result_payload, dict):
        logger.info("Autodiscover scan snapshot stored scan_id=%s status=%s services=0", scan_id, status)
        return

    services = extract_services_from_scan_payload(result_payload)
    persisted_services = 0
    try:
        persisted_services = await _persist_scan_services(
            scan_id=scan_id,
            services=services,
            storage_rpc=storage_rpc,
        )
    except Exception as exc:
        logger.warning(
            "Autodiscover failed to persist scan_services projection for scan_id=%s: %s",
            scan_id,
            exc,
        )
        with suppress(Exception):
            await storage_rpc.kv_set(
                plugin_id=PLUGIN_NAME,
                key="services_latest",
                value=services,
            )
            logger.warning(
                "Autodiscover stored compatibility KV fallback services_latest scan_id=%s count=%s",
                scan_id,
                len(services),
            )
    else:
        if persisted_services > 0:
            with suppress(Exception):
                await storage_rpc.kv_delete(plugin_id=PLUGIN_NAME, key="services_latest")

    logger.info(
        "Autodiscover scan snapshot stored scan_id=%s status=%s services=%s",
        scan_id,
        status,
        persisted_services or len(services),
    )


def _scan_action_contract() -> tuple[str, str, str, bool]:
    for contract in ACTIONS:
        if contract.type == ACTION_SCAN:
            return (
                contract.type,
                contract.capability,
                contract.description,
                contract.dry_run_supported,
            )
    raise RuntimeError(f"Autodiscover action contract '{ACTION_SCAN}' is missing")


async def _execute_autodiscover_scan(
    action: ActionEnvelope,
    *,
    event_bus: EventPublisher,
    config_service: ConfigService | None = None,
    storage_rpc: StorageRPC | None = None,
) -> dict[str, Any]:
    correlation_id = str(action.id)
    await event_bus.publish(
        event_type=EVENT_SCAN_STARTED,
        source=f"plugin.{PLUGIN_NAME}",
        correlation_id=correlation_id,
        payload={
            "action_id": correlation_id,
            "dry_run": action.dry_run,
        },
    )

    payload = dict(action.payload)
    if "config_snapshot" not in payload and config_service is not None:
        with suppress(Exception):
            payload["config_snapshot"] = await config_service.get_active_revision()

    async def _progress(event_type: str, payload_data: dict[str, Any]) -> None:
        if event_type == "host_found":
            event_name = EVENT_HOST_FOUND
        elif event_type == "service_found":
            event_name = EVENT_SERVICE_FOUND
        else:
            event_name = EVENT_SCAN_PROGRESS
        await event_bus.publish(
            event_type=event_name,
            source=f"plugin.{PLUGIN_NAME}",
            correlation_id=correlation_id,
            payload={
                "action_id": correlation_id,
                "dry_run": action.dry_run,
                **payload_data,
            },
        )

    try:
        result = await execute_scan(
            payload=payload,
            dry_run=action.dry_run,
            progress_callback=_progress,
        )
    except ValueError as exc:
        await _persist_scan_snapshot(
            action=action,
            status="failed",
            summary={"error": str(exc)},
            result_payload=None,
            storage_rpc=storage_rpc,
        )
        await event_bus.publish(
            event_type=EVENT_SCAN_FAILED,
            source=f"plugin.{PLUGIN_NAME}",
            correlation_id=correlation_id,
            payload={"action_id": correlation_id, "error": str(exc)},
        )
        raise ApiError(
            status_code=422,
            code="autodiscover_invalid_payload",
            message=str(exc),
        ) from exc
    except Exception as exc:
        await _persist_scan_snapshot(
            action=action,
            status="failed",
            summary={"error": str(exc)},
            result_payload=None,
            storage_rpc=storage_rpc,
        )
        await event_bus.publish(
            event_type=EVENT_SCAN_FAILED,
            source=f"plugin.{PLUGIN_NAME}",
            correlation_id=correlation_id,
            payload={"action_id": correlation_id, "error": str(exc)},
        )
        raise ApiError(
            status_code=500,
            code="autodiscover_execution_failed",
            message=str(exc),
        ) from exc

    await _persist_scan_snapshot(
        action=action,
        status="completed",
        summary=result.get("summary", {}),
        result_payload=result.get("result") if isinstance(result.get("result"), dict) else None,
        storage_rpc=storage_rpc,
    )

    await event_bus.publish(
        event_type=EVENT_SCAN_COMPLETED,
        source=f"plugin.{PLUGIN_NAME}",
        correlation_id=correlation_id,
        payload={
            "action_id": correlation_id,
            "dry_run": action.dry_run,
            "summary": result.get("summary", {}),
        },
    )
    return result


def register_autodiscover_actions(
    gateway: ActionGateway,
    *,
    event_bus: EventPublisher,
    config_service: ConfigService | None = None,
    storage_rpc: StorageRPC | None = None,
) -> None:
    action_type, capability, description, dry_run_supported = _scan_action_contract()

    async def _executor(action: ActionEnvelope) -> dict[str, Any]:
        return await _execute_autodiscover_scan(
            action,
            event_bus=event_bus,
            config_service=config_service,
            storage_rpc=storage_rpc,
        )

    gateway.register_action(
        action_type=action_type,
        capability=capability,
        description=description,
        executor=_executor,
        dry_run_supported=dry_run_supported,
    )


__all__ = ["register_autodiscover_actions"]
