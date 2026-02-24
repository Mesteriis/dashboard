from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Any


class StorageRpcBus:
    def __init__(self) -> None:
        self._queues: dict[str, set[asyncio.Queue[Any]]] = {}
        self._lock = asyncio.Lock()

    async def publish(self, *, queue_name: str, message: Any) -> None:
        async with self._lock:
            subscribers = tuple(self._queues.get(queue_name, ()))
            for queue in subscribers:
                if queue.full():
                    with suppress(asyncio.QueueEmpty):
                        queue.get_nowait()
                try:
                    queue.put_nowait(message)
                except asyncio.QueueFull:
                    continue

    def subscribe(self, *, queue_name: str, queue_size: int = 256) -> asyncio.Queue[Any]:
        queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=max(1, queue_size))
        self._queues.setdefault(queue_name, set()).add(queue)
        return queue

    def unsubscribe(self, *, queue_name: str, queue: asyncio.Queue[Any]) -> None:
        subscribers = self._queues.get(queue_name)
        if subscribers is None:
            return
        subscribers.discard(queue)
        if not subscribers:
            self._queues.pop(queue_name, None)


__all__ = ["StorageRpcBus"]
