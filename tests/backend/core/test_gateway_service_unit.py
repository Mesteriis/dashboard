from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from core.contracts.errors import ApiError
from core.contracts.models import ActionEnvelope, ActionValidationResponse
from core.gateway.service import ActionGateway

pytestmark = pytest.mark.asyncio


def _gateway(*, execute_enabled: bool = True) -> tuple[ActionGateway, SimpleNamespace, SimpleNamespace, SimpleNamespace]:
    actions = SimpleNamespace(
        create_queued=AsyncMock(),
        set_status=AsyncMock(),
        list_history=AsyncMock(return_value=[]),
    )
    audit = SimpleNamespace(append=AsyncMock())
    events = SimpleNamespace(publish=AsyncMock())
    gateway = ActionGateway(actions=actions, audit=audit, events=events, execute_enabled=execute_enabled)
    return gateway, actions, audit, events


def _action(*, action_type: str = "demo.action", capability: str = "exec.demo", dry_run: bool = False) -> ActionEnvelope:
    return ActionEnvelope(
        type=action_type,
        requested_by="tester",
        capability=capability,
        payload={"x": 1},
        dry_run=dry_run,
    )


async def test_validate_action_blocked_and_validated_paths() -> None:
    gateway, actions, audit, _events = _gateway()

    unknown = await gateway.validate_action(action=_action(action_type="unknown"), actor="tester")
    assert unknown.valid is False
    assert unknown.status == "blocked"

    gateway.register_action(
        action_type="demo.action",
        capability="exec.demo",
        description="Demo",
        executor=lambda _action: {"ok": True},
    )

    mismatch = await gateway.validate_action(
        action=_action(capability="exec.other"),
        actor="tester",
    )
    assert mismatch.valid is False

    actor_mismatch = await gateway.validate_action(action=_action(), actor="another")
    assert actor_mismatch.valid is False

    valid = await gateway.validate_action(action=_action(), actor="tester")
    assert valid.valid is True
    assert valid.status == "validated"

    assert actions.create_queued.await_count == 4
    assert actions.set_status.await_count == 4
    assert audit.append.await_count == 4


async def test_execute_action_returns_blocked_when_validation_fails() -> None:
    gateway, _actions, _audit, _events = _gateway()
    response = await gateway.execute_action(action=_action(action_type="unknown"), actor="tester")
    assert response.status == "blocked"
    assert response.result is None


async def test_execute_action_handles_missing_registry_after_validation() -> None:
    gateway, _actions, _audit, _events = _gateway()
    action = _action()
    gateway.validate_action = AsyncMock(
        return_value=ActionValidationResponse(action_id=action.id, valid=True, status="validated")
    )

    with pytest.raises(ApiError) as err:
        await gateway.execute_action(action=action, actor="tester")
    assert err.value.status_code == 500
    assert err.value.error.code == "registry_state_invalid"


async def test_execute_action_respects_execute_disabled_and_dry_run_flags() -> None:
    disabled_gateway, disabled_actions, disabled_audit, _disabled_events = _gateway(execute_enabled=False)
    disabled_gateway.register_action(
        action_type="demo.action",
        capability="exec.demo",
        description="Demo",
        executor=lambda _action: {"ok": True},
    )

    with pytest.raises(ApiError) as disabled_err:
        await disabled_gateway.execute_action(action=_action(), actor="tester")
    assert disabled_err.value.status_code == 503
    assert disabled_actions.set_status.await_count >= 2
    assert disabled_audit.append.await_count >= 2

    dry_run_gateway, dry_actions, _dry_audit, _dry_events = _gateway()
    dry_run_gateway.register_action(
        action_type="demo.action",
        capability="exec.demo",
        description="Demo",
        executor=lambda _action: {"ok": True},
        dry_run_supported=False,
    )

    with pytest.raises(ApiError) as dry_err:
        await dry_run_gateway.execute_action(action=_action(dry_run=True), actor="tester")
    assert dry_err.value.status_code == 422
    assert dry_err.value.error.code == "dry_run_not_supported"
    assert dry_actions.set_status.await_count >= 2


async def test_execute_action_success_paths_and_history() -> None:
    gateway, actions, audit, events = _gateway()

    async def _async_executor(_action: ActionEnvelope) -> dict[str, object]:
        return {"result": "ok"}

    gateway.register_action(
        action_type="demo.action",
        capability="exec.demo",
        description="Demo",
        executor=_async_executor,
    )

    response = await gateway.execute_action(action=_action(), actor="tester")
    assert response.status == "succeeded"
    assert response.result == {"result": "ok"}

    gateway.register_action(
        action_type="demo.sync",
        capability="exec.sync",
        description="Sync",
        executor=lambda _action: "not-a-dict",  # type: ignore[return-value]
    )

    response_sync = await gateway.execute_action(
        action=_action(action_type="demo.sync", capability="exec.sync"),
        actor="tester",
    )
    assert response_sync.status == "succeeded"
    assert response_sync.result == {"ok": True}

    actions.list_history = AsyncMock(return_value=[SimpleNamespace(model_dump=lambda mode: {"id": "1"})])
    history = await gateway.history(limit=5)
    assert history == [{"id": "1"}]

    assert audit.append.await_count >= 2
    assert events.publish.await_count >= 4


async def test_execute_action_failure_paths() -> None:
    gateway, actions, audit, events = _gateway()

    def _api_error(_action: ActionEnvelope) -> dict[str, object]:
        raise ApiError(status_code=418, code="teapot", message="nope")

    gateway.register_action(
        action_type="demo.api-error",
        capability="exec.api",
        description="ApiError",
        executor=_api_error,
    )

    with pytest.raises(ApiError) as api_err:
        await gateway.execute_action(
            action=_action(action_type="demo.api-error", capability="exec.api"),
            actor="tester",
        )
    assert api_err.value.status_code == 418

    def _runtime_error(_action: ActionEnvelope) -> dict[str, object]:
        raise RuntimeError("kaboom")

    gateway.register_action(
        action_type="demo.error",
        capability="exec.error",
        description="Error",
        executor=_runtime_error,
    )

    with pytest.raises(ApiError) as runtime_err:
        await gateway.execute_action(
            action=_action(action_type="demo.error", capability="exec.error"),
            actor="tester",
        )
    assert runtime_err.value.status_code == 500
    assert runtime_err.value.error.code == "execution_failed"

    assert actions.set_status.await_count >= 4
    assert audit.append.await_count >= 4
    assert events.publish.await_count >= 4
