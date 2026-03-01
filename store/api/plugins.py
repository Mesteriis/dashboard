"""Plugin management API routes."""

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile

from store.schemas import (
    PluginActionResponse,
    PluginInfo,
    PluginListResponse,
    PluginUploadGitHubRequest,
    PluginUploadResponse,
)
from store.services.storage import plugin_storage

router = APIRouter(prefix="/plugins", tags=["plugins"])


@router.get("", response_model=PluginListResponse)
async def list_plugins() -> PluginListResponse:
    """List all plugins available in store catalog."""
    plugins = plugin_storage.list_plugins()
    return PluginListResponse(plugins=plugins, total=len(plugins))


@router.get("/{plugin_id}", response_model=PluginInfo)
async def get_plugin(plugin_id: str) -> PluginInfo:
    """Get plugin details by ID."""
    plugin = plugin_storage.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} not found")
    return plugin


@router.post("/upload/zip", response_model=PluginUploadResponse)
async def upload_plugin_zip(
    file: Annotated[UploadFile, File(description="Plugin ZIP file")],
) -> PluginUploadResponse:
    """Upload a plugin from a ZIP file."""
    # Validate file extension
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only ZIP files are allowed")

    try:
        # Save uploaded file temporarily
        import tempfile
        from pathlib import Path

        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = Path(tmp.name)

        # Store plugin
        plugin_info = plugin_storage.store_plugin_from_zip(tmp_path, file.filename)

        # Cleanup temp file
        tmp_path.unlink()

        return PluginUploadResponse(
            success=True,
            plugin_id=plugin_info.id,
            message=f"Plugin {plugin_info.name} uploaded successfully",
            plugin=plugin_info,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload plugin: {str(e)}")


@router.post("/upload/github", response_model=PluginUploadResponse)
async def upload_plugin_github(
    request: PluginUploadGitHubRequest,
) -> PluginUploadResponse:
    """Upload a plugin from a GitHub repository."""
    try:
        plugin_info = plugin_storage.store_plugin_from_github(
            repo_url=str(request.repo_url),
            branch=request.branch,
            subdirectory=request.subdirectory,
        )

        return PluginUploadResponse(
            success=True,
            plugin_id=plugin_info.id,
            message=f"Plugin {plugin_info.name} imported from GitHub successfully",
            plugin=plugin_info,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to import plugin from GitHub: {str(e)}"
        )


@router.delete("/{plugin_id}", response_model=PluginActionResponse)
async def delete_plugin(plugin_id: str) -> PluginActionResponse:
    """Delete a plugin."""
    plugin = plugin_storage.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} not found")

    success = plugin_storage.delete_plugin(plugin_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete plugin")

    return PluginActionResponse(
        success=True,
        message=f"Plugin {plugin.name} deleted successfully",
        plugin=plugin,
    )


@router.get("/{plugin_id}/path")
async def get_plugin_path(plugin_id: str) -> dict:
    """Get the file system path to a plugin."""
    plugin = plugin_storage.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} not found")

    plugin_path = plugin_storage.get_plugin_path(plugin_id)
    if not plugin_path:
        raise HTTPException(status_code=404, detail="Plugin path not found")

    return {
        "plugin_id": plugin_id,
        "path": str(plugin_path),
        "exists": plugin_path.exists(),
    }
