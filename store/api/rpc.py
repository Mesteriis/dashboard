"""Store RPC API for backend integration."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from store.schemas import PluginInfo, PluginListResponse
from store.services.storage import plugin_storage

router = APIRouter(prefix="/rpc", tags=["rpc"])


class PluginDownloadRequest(BaseModel):
    """Request for downloading a plugin."""

    plugin_id: str


class PluginDownloadResponse(BaseModel):
    """Response with plugin file path."""

    success: bool
    plugin_id: str
    plugin_path: str | None = None
    archive_path: str | None = None
    message: str


class PluginSyncResponse(BaseModel):
    """Response for plugin sync."""

    plugins: list[PluginInfo]
    total: int


@router.get("/plugins", response_model=PluginSyncResponse)
async def sync_plugins() -> PluginSyncResponse:
    """
    Sync plugin list with backend.
    Returns all plugins available in store.
    """
    plugins = plugin_storage.list_plugins()
    return PluginSyncResponse(plugins=plugins, total=len(plugins))


@router.post("/plugins/download", response_model=PluginDownloadResponse)
async def download_plugin(request: PluginDownloadRequest) -> PluginDownloadResponse:
    """
    Download plugin files for installation.
    Returns path to plugin files or archive.
    """
    plugin = plugin_storage.get_plugin(request.plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin {request.plugin_id} not found")

    # Get plugin path
    plugin_path = plugin_storage.get_plugin_path(request.plugin_id)
    if not plugin_path or not plugin_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Plugin files not found for {request.plugin_id}"
        )

    # Return path to extracted plugin
    return PluginDownloadResponse(
        success=True,
        plugin_id=request.plugin_id,
        plugin_path=str(plugin_path),
        message=f"Plugin {plugin.name} ready for installation",
    )


@router.get("/plugins/{plugin_id}/manifest")
async def get_plugin_manifest(plugin_id: str) -> dict:
    """Get plugin manifest for preview."""
    plugin = plugin_storage.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} not found")

    return {
        "plugin_id": plugin_id,
        "name": plugin.name,
        "version": plugin.version,
        "description": plugin.description,
        "author": plugin.author,
        "manifest": plugin.manifest.model_dump() if plugin.manifest else None,
    }


@router.get("/health")
async def health_check() -> dict:
    """Health check for backend integration."""
    health = plugin_storage.get_health()
    return {
        "status": health["status"],
        "plugins_available": health["plugins_count"],
    }
