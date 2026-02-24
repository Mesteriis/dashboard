from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from core.contracts.models import ActionEnvelope
from core.gateway import ActionGateway


async def _execute_system_echo(action: ActionEnvelope) -> dict[str, Any]:
    return {
        "echo": action.payload,
        "action": action.type,
        "dry_run": action.dry_run,
    }


async def _execute_system_ping(_action: ActionEnvelope) -> dict[str, Any]:
    return {
        "ok": True,
        "ts": datetime.now(UTC).isoformat(),
    }


def register_system_actions(gateway: ActionGateway) -> None:
    gateway.register_action(
        action_type="system.echo",
        capability="exec.system.echo",
        description="Echo payload for connectivity tests",
        executor=_execute_system_echo,
        dry_run_supported=True,
    )
    gateway.register_action(
        action_type="system.ping",
        capability="exec.system.ping",
        description="Ping system action executor",
        executor=_execute_system_ping,
        dry_run_supported=True,
    )


__all__ = ["register_system_actions"]
