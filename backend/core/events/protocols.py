from __future__ import annotations

from typing import Protocol

from core.contracts.models import EventEnvelope


class EventPublisher(Protocol):
    async def publish(
        self,
        *,
        event_type: str,
        source: str,
        payload: dict[str, object] | None = None,
        correlation_id: str | None = None,
        revision: int | None = None,
    ) -> EventEnvelope: ...


__all__ = ["EventPublisher"]
