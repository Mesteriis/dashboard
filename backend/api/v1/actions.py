from __future__ import annotations

from core.contracts.models import (
    ActionEnvelope,
    ActionExecutionResponse,
    ActionRegistryEntry,
    ActionStatus,
    ActionValidationResponse,
)
from core.security import (
    ActorDep,
    require_actions_execute,
    require_actions_history,
    require_actions_registry,
    require_actions_validate,
)
from depends.v1.core_deps import ActionRepositoryDep, ActionRpcClientDep, GatewayDep
from fastapi import APIRouter, Query

actions_router = APIRouter(tags=["actions"])


@actions_router.get("/actions/registry", response_model=list[ActionRegistryEntry])
async def get_actions_registry(
    gateway: GatewayDep,
    _capability: str = require_actions_registry,
) -> list[ActionRegistryEntry]:
    return gateway.list_registry()


@actions_router.post("/actions/validate", response_model=ActionValidationResponse)
async def validate_action(
    payload: ActionEnvelope,
    gateway: GatewayDep,
    actor: ActorDep,
    _capability: str = require_actions_validate,
) -> ActionValidationResponse:
    return await gateway.validate_action(action=payload, actor=actor)


@actions_router.post("/actions/execute", response_model=ActionExecutionResponse)
async def execute_action(
    payload: ActionEnvelope,
    action_rpc_client: ActionRpcClientDep,
    actor: ActorDep,
    _capability: str = require_actions_execute,
) -> ActionExecutionResponse:
    return await action_rpc_client.execute(action=payload, actor=actor)


@actions_router.get("/actions/history", response_model=list[ActionStatus])
async def get_actions_history(
    action_repository: ActionRepositoryDep,
    _capability: str = require_actions_history,
    limit: int = Query(default=50, ge=1, le=500),
) -> list[ActionStatus]:
    return await action_repository.list_history(limit=limit)


__all__ = ["actions_router"]
