from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from core.contracts.errors import ApiError
from fastapi import Depends, Header


def _parse_capabilities(raw: str | None) -> set[str]:
    if not raw:
        return set()
    return {chunk.strip() for chunk in raw.split(",") if chunk.strip()}


def _require_capability(capability: str) -> Callable[[str | None], str]:
    def _checker(x_oko_capabilities: str | None = Header(default=None)) -> str:
        capabilities = _parse_capabilities(x_oko_capabilities)
        if capability not in capabilities:
            raise ApiError(
                status_code=403,
                code="capability_required",
                message=f"Capability '{capability}' is required",
                details=[{"capability": capability}],
            )
        return capability

    return _checker


def _get_actor(x_oko_actor: str | None = Header(default=None)) -> str:
    actor = (x_oko_actor or "").strip()
    if actor:
        return actor
    raise ApiError(status_code=401, code="actor_required", message="Header 'X-Oko-Actor' is required")


ActorDep = Annotated[str, Depends(_get_actor)]

require_state = Depends(_require_capability("read.state"))
require_config = Depends(_require_capability("read.config"))
require_config_import = Depends(_require_capability("write.config.import"))
require_config_patch = Depends(_require_capability("write.config.patch"))
require_config_rollback = Depends(_require_capability("write.config.rollback"))
require_config_revisions = Depends(_require_capability("read.config.revisions"))
require_events = Depends(_require_capability("read.events"))
require_widgets_registry = Depends(_require_capability("read.registry.widgets"))
require_actions_registry = Depends(_require_capability("read.registry.actions"))
require_actions_validate = Depends(_require_capability("exec.actions.validate"))
require_actions_execute = Depends(_require_capability("exec.actions.execute"))
require_actions_history = Depends(_require_capability("read.actions.history"))
require_plugins_list = Depends(_require_capability("read.plugins.list"))
require_plugins_manifest = Depends(_require_capability("read.plugins.manifest"))
require_plugins_services = Depends(_require_capability("read.plugins.services"))


__all__ = [
    "ActorDep",
    "require_actions_execute",
    "require_actions_history",
    "require_actions_registry",
    "require_actions_validate",
    "require_config",
    "require_config_import",
    "require_config_patch",
    "require_config_revisions",
    "require_config_rollback",
    "require_events",
    "require_plugins_list",
    "require_plugins_manifest",
    "require_plugins_services",
    "require_state",
    "require_widgets_registry",
]
