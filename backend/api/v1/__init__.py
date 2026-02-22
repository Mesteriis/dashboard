from __future__ import annotations

from api.v1.config import config_router
from api.v1.health import health_router
from api.v1.iframe import iframe_router
from api.v1.lan import lan_router
from fastapi import APIRouter

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(config_router)
v1_router.include_router(health_router)
v1_router.include_router(iframe_router)
v1_router.include_router(lan_router)

__all__ = ["v1_router"]
