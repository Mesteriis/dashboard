from __future__ import annotations

from contextlib import suppress
from datetime import UTC, datetime
from typing import Any

from core.config import ConfigService
from core.contracts.errors import ApiError
from core.contracts.models import ActionEnvelope
from core.events.protocols import EventPublisher
from core.gateway import ActionGateway
from core.storage import StorageRPC

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


async def _persist_scan_snapshot(
    *,
    action: ActionEnvelope,
    status: str,
    summary: dict[str, Any],
    storage_rpc: StorageRPC | None,
) -> None:
    if storage_rpc is None:
        return

    await storage_rpc.table_upsert(
        plugin_id=PLUGIN_NAME,
        table="scan_runs",
        row={
            "scan_id": str(action.id),
            "status": status,
            "dry_run": bool(action.dry_run),
            "requested_at": action.requested_at.isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "summary": summary,
        },
    )
    await storage_rpc.kv_set(
        plugin_id=PLUGIN_NAME,
        key="last_scan_summary",
        value=summary,
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
