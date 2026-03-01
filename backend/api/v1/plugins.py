from __future__ import annotations

import inspect
from typing import Any

from core.plugins.page_manifest import resolve_page_manifest, serialize_resolution
from core.security import (
    require_actions_execute,
    require_actions_registry,
    require_plugins_list,
    require_plugins_manifest,
    require_plugins_services,
)
from depends.v1.core_deps import ContainerDep
from fastapi import APIRouter, HTTPException, Query

plugins_router = APIRouter(prefix="/plugins", tags=["plugins"])


@plugins_router.get("")
async def list_plugins(
    container: ContainerDep,
    _capability: str = require_plugins_list,
    state: str | None = Query(default=None, description="Filter by plugin state"),
) -> dict:
    """
    List all plugins with optional state filtering.

    States: discovered, loading, active, error, disabled
    """
    if not container.plugin_service:
        return {"plugins": [], "total": 0}

    plugins = container.plugin_service.list_plugins()

    if state:
        from core.plugins.schemas import PluginState

        try:
            target_state = PluginState(state)
            plugins = [p for p in plugins if p.state == target_state]
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid state: {state}. Valid states: discovered, loading, active, error, disabled".format(
                    state=state
                ),
            )

    return {
        "plugins": [p.to_dict() for p in plugins],
        "total": len(plugins),
    }


@plugins_router.get("/{plugin_id}/manifest")
async def get_plugin_manifest(
    plugin_id: str,
    container: ContainerDep,
    _capability: str = require_plugins_manifest,
) -> dict[str, Any]:
    if not container.plugin_service:
        raise HTTPException(status_code=503, detail="Plugin service not available")

    plugin = container.plugin_service.get_plugin(plugin_id)
    if plugin is None:
        raise HTTPException(status_code=404, detail=f"Plugin not found: {plugin_id}")

    resolution = resolve_page_manifest(
        plugin_id=plugin.id,
        plugin_version=plugin.manifest.version,
        plugin_path=plugin.path,
    )
    payload = serialize_resolution(resolution)
    plugin.metadata["page_manifest"] = payload
    return {
        "plugin_id": plugin.id,
        **payload,
    }


@plugins_router.get("/{plugin_id}/services")
async def get_plugin_services(
    plugin_id: str,
    container: ContainerDep,
    _capability: str = require_plugins_services,
) -> dict[str, Any]:
    if not container.plugin_service:
        raise HTTPException(status_code=503, detail="Plugin service not available")

    plugin = container.plugin_service.get_plugin(plugin_id)
    if plugin is None:
        raise HTTPException(status_code=404, detail=f"Plugin not found: {plugin_id}")

    handler = getattr(plugin.module, "get_services", None) if plugin.module else None
    if handler is None:
        raise HTTPException(status_code=404, detail=f"Services endpoint is not supported for plugin: {plugin_id}")

    if not callable(handler):
        raise HTTPException(status_code=500, detail=f"Invalid services handler for plugin: {plugin_id}")

    result = handler()
    if inspect.isawaitable(result):
        result = await result
    if not isinstance(result, dict):
        raise HTTPException(status_code=500, detail=f"Invalid services response for plugin: {plugin_id}")

    return {
        "plugin_id": plugin.id,
        **result,
    }


@plugins_router.get("/registry")
async def get_plugins_registry(
    container: ContainerDep,
    _capability: str = require_actions_registry,
) -> dict:
    """Get registry of all plugins with their capabilities."""
    if not container.plugin_service:
        return {"plugins": [], "total": 0}

    plugins = container.plugin_service.list_plugins()
    registry = []

    for plugin in plugins:
        registry.append(
            {
                "id": plugin.id,
                "name": plugin.manifest.name,
                "version": plugin.manifest.version,
                "capabilities": list(plugin.manifest.capabilities),
                "actions": list(plugin.manifest.actions),
                "events": list(plugin.manifest.events),
                "ui_config": {
                    "has_page": plugin.ui_config.has_page if plugin.ui_config else False,
                    "page_path": plugin.ui_config.page_path if plugin.ui_config else None,
                    "show_in_menu": plugin.ui_config.show_in_menu if plugin.ui_config else True,
                }
                if plugin.ui_config
                else None,
            }
        )

    return {
        "plugins": registry,
        "total": len(registry),
    }


@plugins_router.get("/{plugin_id}")
async def get_plugin(
    plugin_id: str,
    container: ContainerDep,
    _capability: str = require_plugins_list,
) -> dict:
    """Get detailed information about a specific plugin."""
    if not container.plugin_service:
        raise HTTPException(status_code=503, detail="Plugin service not available")

    plugin = container.plugin_service.get_plugin(plugin_id)
    if plugin is None:
        raise HTTPException(status_code=404, detail=f"Plugin not found: {plugin_id}")

    return plugin.to_dict()


@plugins_router.post("/{plugin_id}/load")
async def load_plugin(
    plugin_id: str,
    container: ContainerDep,
    _capability: str = require_actions_execute,
) -> dict:
    """Load a plugin into memory."""
    if not container.plugin_service:
        raise HTTPException(status_code=503, detail="Plugin service not available")

    try:
        plugin = container.plugin_service.load_plugin(plugin_id)
        return {
            "status": "loaded",
            "plugin": plugin.to_dict(),
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load plugin: {exc}")


@plugins_router.post("/{plugin_id}/unload")
async def unload_plugin(
    plugin_id: str,
    container: ContainerDep,
    _capability: str = require_actions_execute,
) -> dict:
    """Unload a plugin from memory."""
    if not container.plugin_service:
        raise HTTPException(status_code=503, detail="Plugin service not available")

    success = container.plugin_service.unload_plugin(plugin_id)
    if success:
        return {"status": "unloaded", "plugin_id": plugin_id}
    raise HTTPException(status_code=400, detail=f"Failed to unload plugin: {plugin_id}")


@plugins_router.post("/{plugin_id}/reload")
async def reload_plugin(
    plugin_id: str,
    container: ContainerDep,
    _capability: str = require_actions_execute,
) -> dict:
    """Reload a plugin."""
    if not container.plugin_service:
        raise HTTPException(status_code=503, detail="Plugin service not available")

    try:
        plugin = container.plugin_service.reload_plugin(plugin_id)
        return {
            "status": "reloaded",
            "plugin": plugin.to_dict(),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to reload plugin: {exc}")


@plugins_router.post("/{plugin_id}/enable")
async def enable_plugin(
    plugin_id: str,
    container: ContainerDep,
    _capability: str = require_actions_execute,
) -> dict:
    """Enable a disabled plugin."""
    if not container.plugin_service:
        raise HTTPException(status_code=503, detail="Plugin service not available")

    try:
        plugin = container.plugin_service.enable_plugin(plugin_id)
        return {
            "status": "enabled",
            "plugin": plugin.to_dict(),
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to enable plugin: {exc}")


@plugins_router.post("/{plugin_id}/disable")
async def disable_plugin(
    plugin_id: str,
    container: ContainerDep,
    _capability: str = require_actions_execute,
) -> dict:
    """Disable a plugin."""
    if not container.plugin_service:
        raise HTTPException(status_code=503, detail="Plugin service not available")

    success = container.plugin_service.disable_plugin(plugin_id)
    if success:
        return {"status": "disabled", "plugin_id": plugin_id}
    raise HTTPException(status_code=400, detail=f"Failed to disable plugin: {plugin_id}")


__all__ = ["plugins_router"]
