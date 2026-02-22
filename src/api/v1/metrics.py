"""Prometheus metrics endpoint for dashboard monitoring."""

from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST

from depens.v1.metrics_deps import ContainerDep
from depens.v1.metrics_logic import collect_metrics_payload

metrics_router = APIRouter(prefix="/metrics", tags=["metrics"])


@metrics_router.get("", response_class=Response)
@metrics_router.get("/", response_class=Response)
async def get_metrics(container: ContainerDep) -> Response:
    return Response(
        content=collect_metrics_payload(container),
        media_type=CONTENT_TYPE_LATEST,
    )


__all__ = ["metrics_router"]
