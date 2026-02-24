from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import UTC, datetime
from uuid import uuid4

from core.contracts.models import EventEnvelope


class EventBus:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[EventEnvelope]] = set()
        self._lock = asyncio.Lock()
        self._revision = 0

    async def publish(
        self,
        *,
        event_type: str,
        source: str,
        payload: dict[str, object] | None = None,
        correlation_id: str | None = None,
        revision: int | None = None,
    ) -> EventEnvelope:
        async with self._lock:
            self._revision = max(self._revision + 1, revision or 1)
            envelope = EventEnvelope(
                id=uuid4(),
                type=event_type,
                event_version=1,
                revision=self._revision,
                ts=datetime.now(UTC),
                source=source,
                correlation_id=correlation_id,
                payload=payload or {},
            )
            for queue in tuple(self._subscribers):
                if queue.full():
                    with suppress(asyncio.QueueEmpty):
                        queue.get_nowait()
                try:
                    queue.put_nowait(envelope)
                except asyncio.QueueFull:
                    continue
            return envelope

    def subscribe(self, *, queue_size: int = 256) -> asyncio.Queue[EventEnvelope]:
        queue: asyncio.Queue[EventEnvelope] = asyncio.Queue(maxsize=max(1, queue_size))
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[EventEnvelope]) -> None:
        self._subscribers.discard(queue)


__all__ = ["EventBus"]
