"""Dependencies for metrics API router."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from config.container import AppContainer
from depens.v1.deps import get_container

ContainerDep = Annotated[AppContainer, Depends(get_container)]


__all__ = ["ContainerDep"]
