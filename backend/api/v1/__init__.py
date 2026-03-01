from __future__ import annotations

from api.v1.actions import actions_router
from api.v1.core import core_router
from api.v1.plugins import plugins_router
from api.v1.store import store_router
from fastapi import APIRouter

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(core_router)
v1_router.include_router(actions_router)
v1_router.include_router(plugins_router)
v1_router.include_router(store_router)

__all__ = ["v1_router"]
