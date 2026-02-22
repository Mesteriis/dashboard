"""Shared FastAPI dependencies for API v1 routers."""

from __future__ import annotations

from fastapi import HTTPException, Request

from config.container import AppContainer


def get_container(request: Request) -> AppContainer:
    """Resolve application DI container from FastAPI app state."""
    container = getattr(request.app.state, "container", None)
    if not isinstance(container, AppContainer):
        raise HTTPException(status_code=500, detail="Application container is not configured")
    return container


__all__ = ["get_container"]
