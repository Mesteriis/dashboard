from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from core.contracts.errors import ApiError
from core.contracts.models import (
    ActionEnvelope,
    ActionExecutionResponse,
    ActionRegistryEntry,
    ActionValidationResponse,
    AuditEvent,
)
from core.events.protocols import EventPublisher
from core.storage.repositories import ActionRepository, AuditRepository

ActionExecutor = Callable[[ActionEnvelope], Awaitable[dict[str, Any]] | dict[str, Any]]


@dataclass(frozen=True)
class RegisteredAction:
    type: str
    capability: str
    description: str
    dry_run_supported: bool
    executor: ActionExecutor


class ActionGateway:
    def __init__(
        self,
        *,
        actions: ActionRepository,
        audit: AuditRepository,
        events: EventPublisher,
        execute_enabled: bool,
    ) -> None:
        self._actions = actions
        self._audit = audit
        self._events = events
        self._execute_enabled = execute_enabled
        self._registry: dict[str, RegisteredAction] = {}

    def register_action(
        self,
        *,
        action_type: str,
        capability: str,
        description: str,
        executor: ActionExecutor,
        dry_run_supported: bool = True,
    ) -> None:
        self._registry[action_type] = RegisteredAction(
            type=action_type,
            capability=capability,
            description=description,
            dry_run_supported=dry_run_supported,
            executor=executor,
        )

    def list_registry(self) -> list[ActionRegistryEntry]:
        return [
            ActionRegistryEntry(
                type=entry.type,
                capability=entry.capability,
                description=entry.description,
                dry_run_supported=entry.dry_run_supported,
            )
            for entry in sorted(self._registry.values(), key=lambda value: value.type)
        ]

    async def validate_action(self, *, action: ActionEnvelope, actor: str) -> ActionValidationResponse:
        registration = self._registry.get(action.type)
        blocked_reason: str | None = None

        if registration is None:
            blocked_reason = f"Unknown action type: {action.type}"
        elif registration.capability != action.capability:
            blocked_reason = (
                f"Action capability mismatch. Expected '{registration.capability}', got '{action.capability}'"
            )
        elif action.requested_by != actor:
            blocked_reason = "Actor mismatch between envelope and header"

        await self._actions.create_queued(action)

        if blocked_reason:
            await self._actions.set_status(
                action_id=action.id,
                status="blocked",
                error={"reason": blocked_reason},
            )
            await self._audit.append(
                AuditEvent(
                    actor=actor,
                    action_id=action.id,
                    capability=action.capability,
                    resource=action.type,
                    decision="deny",
                    outcome="blocked",
                    reason=blocked_reason,
                )
            )
            return ActionValidationResponse(action_id=action.id, valid=False, status="blocked")

        await self._actions.set_status(action_id=action.id, status="validated")
        await self._audit.append(
            AuditEvent(
                actor=actor,
                action_id=action.id,
                capability=action.capability,
                resource=action.type,
                decision="allow",
                outcome="validated",
                reason=None,
            )
        )
        return ActionValidationResponse(action_id=action.id, valid=True, status="validated")

    async def execute_action(self, *, action: ActionEnvelope, actor: str) -> ActionExecutionResponse:
        validation = await self.validate_action(action=action, actor=actor)
        if not validation.valid:
            return ActionExecutionResponse(action_id=action.id, status="blocked", result=None)

        registration = self._registry.get(action.type)
        if registration is None:
            raise ApiError(status_code=500, code="registry_state_invalid", message="Action registry entry missing")

        if not self._execute_enabled:
            await self._actions.set_status(
                action_id=action.id,
                status="blocked",
                error={"reason": "execute_disabled"},
            )
            await self._audit.append(
                AuditEvent(
                    actor=actor,
                    action_id=action.id,
                    capability=action.capability,
                    resource=action.type,
                    decision="deny",
                    outcome="blocked",
                    reason="Kill switch is enabled",
                )
            )
            raise ApiError(status_code=503, code="execute_disabled", message="Action execute is disabled")

        if action.dry_run and not registration.dry_run_supported:
            await self._actions.set_status(
                action_id=action.id,
                status="blocked",
                error={"reason": "dry_run_not_supported"},
            )
            raise ApiError(status_code=422, code="dry_run_not_supported", message="Action does not support dry-run")

        await self._actions.set_status(action_id=action.id, status="running")
        await self._events.publish(
            event_type="core.action.running",
            source="core.gateway",
            payload={"action_id": str(action.id), "type": action.type},
        )

        try:
            result = registration.executor(action)
            if inspect.isawaitable(result):
                result = await result
            if not isinstance(result, dict):
                result = {"ok": True}
            await self._actions.set_status(action_id=action.id, status="succeeded", result=result)
            await self._audit.append(
                AuditEvent(
                    actor=actor,
                    action_id=action.id,
                    capability=action.capability,
                    resource=action.type,
                    decision="allow",
                    outcome="executed",
                    reason=None,
                    metadata={"dry_run": action.dry_run},
                )
            )
            await self._events.publish(
                event_type="core.action.succeeded",
                source="core.gateway",
                payload={"action_id": str(action.id), "type": action.type, "result": result},
            )
            return ActionExecutionResponse(action_id=action.id, status="succeeded", result=result)
        except ApiError as exc:
            await self._actions.set_status(
                action_id=action.id,
                status="failed",
                error=exc.error.model_dump(mode="json"),
            )
            await self._audit.append(
                AuditEvent(
                    actor=actor,
                    action_id=action.id,
                    capability=action.capability,
                    resource=action.type,
                    decision="allow",
                    outcome="failed",
                    reason=exc.error.message,
                )
            )
            await self._events.publish(
                event_type="core.action.failed",
                source="core.gateway",
                payload={"action_id": str(action.id), "type": action.type, "error": exc.error.model_dump(mode="json")},
            )
            raise
        except Exception as exc:
            error = {"code": "execution_failed", "message": str(exc)}
            await self._actions.set_status(action_id=action.id, status="failed", error=error)
            await self._audit.append(
                AuditEvent(
                    actor=actor,
                    action_id=action.id,
                    capability=action.capability,
                    resource=action.type,
                    decision="allow",
                    outcome="failed",
                    reason=str(exc),
                )
            )
            await self._events.publish(
                event_type="core.action.failed",
                source="core.gateway",
                payload={"action_id": str(action.id), "type": action.type, "error": error},
            )
            raise ApiError(status_code=500, code="execution_failed", message=str(exc)) from exc

    async def history(self, *, limit: int = 100) -> list[dict[str, Any]]:
        return [row.model_dump(mode="json") for row in await self._actions.list_history(limit=limit)]


__all__ = ["ActionGateway", "RegisteredAction"]
