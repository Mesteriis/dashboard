"""Plugin Store integration API endpoints."""

from __future__ import annotations

from depends.v1.core_deps import ContainerDep
from fastapi import APIRouter, HTTPException

store_router = APIRouter(prefix="/store", tags=["store"])


@store_router.get("")
async def get_store_info(container: ContainerDep) -> dict:
    """Get plugin store information and available plugins."""
    if not container.plugin_store_client:
        raise HTTPException(status_code=503, detail="Plugin store client not configured")

    # Sync plugins from store
    plugins = await container.plugin_store_client.sync_plugins()
    is_healthy = await container.plugin_store_client.health_check()

    return {
        "available": is_healthy,
        "plugins": [
            {
                "id": p.id,
                "name": p.name,
                "version": p.version,
                "description": p.description,
                "author": p.author,
                "source": p.source,
                "manifest": p.manifest,
            }
            for p in plugins
        ],
        "total": len(plugins),
    }


@store_router.get("/health")
async def check_store_health(container: ContainerDep) -> dict:
    """Check if plugin store is available."""
    if not container.plugin_store_client:
        return {"available": False, "error": "Store client not configured"}

    is_healthy = await container.plugin_store_client.health_check()
    return {
        "available": is_healthy,
        "status": "healthy" if is_healthy else "unavailable",
    }


@store_router.get("/{plugin_id}")
async def get_store_plugin(plugin_id: str, container: ContainerDep) -> dict:
    """Get specific plugin from store."""
    if not container.plugin_store_client:
        raise HTTPException(status_code=503, detail="Plugin store client not configured")

    manifest = await container.plugin_store_client.get_plugin_manifest(plugin_id)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} not found in store")

    return manifest


@store_router.post("/{plugin_id}/install")
async def install_plugin(plugin_id: str, container: ContainerDep) -> dict:
    """
    Install plugin from store to local backend.
    
    This downloads the plugin from store and installs it to the backend's
    plugins directory, making it available for loading.
    """
    if not container.plugin_store_client:
        raise HTTPException(status_code=503, detail="Plugin store client not configured")

    if not container.plugin_installer:
        raise HTTPException(status_code=503, detail="Plugin installer not configured")

    # Install plugin
    plugin_info = await container.plugin_installer.install_plugin(plugin_id)
    if not plugin_info:
        raise HTTPException(status_code=500, detail=f"Failed to install plugin {plugin_id}")

    return {
        "status": "installed",
        "plugin": plugin_info.to_dict(),
        "message": f"Plugin {plugin_info.manifest.name} installed successfully",
    }


@store_router.post("/{plugin_id}/uninstall")
async def uninstall_plugin(plugin_id: str, container: ContainerDep) -> dict:
    """
    Uninstall plugin from local backend.
    
    This removes the plugin from the backend's plugins directory.
    Note: Plugin should be unloaded before uninstalling.
    """
    if not container.plugin_installer:
        raise HTTPException(status_code=503, detail="Plugin installer not configured")

    success = await container.plugin_installer.uninstall_plugin(plugin_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} not found")

    return {
        "status": "uninstalled",
        "plugin_id": plugin_id,
        "message": f"Plugin {plugin_id} uninstalled successfully",
    }


__all__ = ["store_router"]
