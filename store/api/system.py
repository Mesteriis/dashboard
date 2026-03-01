"""System API routes."""

from fastapi import APIRouter

from store.core.config import settings
from store.schemas import HealthResponse
from store.services.storage import plugin_storage

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    health = plugin_storage.get_health()
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        storage_path=str(plugin_storage.storage_path),
        plugins_count=health["plugins_count"],
    )


@router.get("/info")
async def system_info() -> dict:
    """Get system information."""
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "debug": settings.debug,
        "storage_path": str(plugin_storage.storage_path),
        "max_plugin_size_mb": settings.max_plugin_size_mb,
    }
