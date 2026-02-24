from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, IncomingMessage, Message
from aio_pika.abc import AbstractChannel, AbstractConnection, AbstractExchange, AbstractQueue
from aio_pika.exceptions import QueueEmpty
from core.contracts.bus import BusMessageV1, BusReplyV1

from .constants import (
    BUS_EXCHANGE,
    BUS_EXCHANGE_TYPE,
    QUEUE_ACTIONS,
    QUEUE_EVENTS,
    QUEUE_HEALTH_CHECK_REQUEST,
    QUEUE_HEALTH_CHECK_RESULT,
    QUEUE_STORAGE,
    ROUTING_ACTION_EXECUTE,
    ROUTING_EVENT_PUBLISH,
    ROUTING_HEALTH_CHECK_REQUEST,
    ROUTING_HEALTH_CHECK_RESULT,
)


class BusRpcTimeoutError(TimeoutError):
    pass


class BusClient:
    def __init__(self, *, broker_url: str, prefetch_count: int = 32) -> None:
        self._broker_url = broker_url
        self._prefetch_count = prefetch_count
        self._memory_mode = broker_url.startswith("memory://")
        self._connection: AbstractConnection | None = None
        self._channel: AbstractChannel | None = None
        self._exchange: AbstractExchange | None = None
        self._lock = asyncio.Lock()
        self._memory_consumers: list[tuple[str, Any]] = []
        self._memory_reply_queues: dict[str, asyncio.Queue[BusReplyV1]] = {}

    async def connect(self) -> None:
        if self._memory_mode:
            return
        async with self._lock:
            if self._connection is not None and not self._connection.is_closed:
                return

            self._connection = await aio_pika.connect_robust(self._broker_url)
            self._channel = await self._connection.channel()
            await self._channel.set_qos(prefetch_count=self._prefetch_count)
            self._exchange = await self._channel.declare_exchange(
                BUS_EXCHANGE,
                type=ExchangeType(BUS_EXCHANGE_TYPE),
                durable=True,
            )
            await self._declare_topology(channel=self._channel, exchange=self._exchange)

    async def close(self) -> None:
        if self._memory_mode:
            self._memory_consumers = []
            self._memory_reply_queues = {}
            return
        async with self._lock:
            if self._channel is not None and not self._channel.is_closed:
                await self._channel.close()
            self._channel = None
            self._exchange = None
            if self._connection is not None and not self._connection.is_closed:
                await self._connection.close()
            self._connection = None

    async def emit(self, *, message: BusMessageV1, routing_key: str) -> None:
        if self._memory_mode:
            await self._dispatch_memory(
                routing_key=routing_key,
                incoming=_MemoryIncomingMessage(
                    body=message.model_dump_json().encode("utf-8"),
                    correlation_id=message.correlation_id,
                    reply_to=message.reply_to,
                ),
            )
            return
        exchange = await self._require_exchange()
        body = message.model_dump_json().encode("utf-8")
        outgoing = Message(
            body=body,
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
            correlation_id=message.correlation_id,
            reply_to=message.reply_to,
            message_id=str(message.id),
            timestamp=message.ts,
        )
        await exchange.publish(outgoing, routing_key=routing_key)

    async def call(self, *, message: BusMessageV1, routing_key: str, timeout_sec: float) -> BusReplyV1:
        if self._memory_mode:
            correlation_id = message.correlation_id or str(message.id)
            reply_to = f"memory.reply.{uuid4()}"
            reply_queue: asyncio.Queue[BusReplyV1] = asyncio.Queue(maxsize=1)
            self._memory_reply_queues[reply_to] = reply_queue
            request = message.model_copy(update={"reply_to": reply_to, "correlation_id": correlation_id})
            await self._dispatch_memory(
                routing_key=routing_key,
                incoming=_MemoryIncomingMessage(
                    body=request.model_dump_json().encode("utf-8"),
                    correlation_id=correlation_id,
                    reply_to=reply_to,
                ),
            )
            try:
                return await asyncio.wait_for(reply_queue.get(), timeout=max(0.05, timeout_sec))
            except TimeoutError as exc:
                raise BusRpcTimeoutError(f"RPC timeout for routing key '{routing_key}'") from exc
            finally:
                self._memory_reply_queues.pop(reply_to, None)

        channel = await self._require_channel()
        exchange = await self._require_exchange()

        reply_queue = await channel.declare_queue(
            name="",
            durable=False,
            exclusive=True,
            auto_delete=True,
        )
        await reply_queue.bind(exchange=exchange, routing_key=reply_queue.name)

        correlation_id = message.correlation_id or str(message.id)
        request = message.model_copy(update={"reply_to": reply_queue.name, "correlation_id": correlation_id})
        body = request.model_dump_json().encode("utf-8")
        outgoing = Message(
            body=body,
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
            correlation_id=correlation_id,
            reply_to=reply_queue.name,
            message_id=str(request.id),
            timestamp=request.ts,
        )
        await exchange.publish(outgoing, routing_key=routing_key)

        loop = asyncio.get_running_loop()
        deadline = loop.time() + max(0.05, timeout_sec)

        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise BusRpcTimeoutError(f"RPC timeout for routing key '{routing_key}'")
            try:
                incoming = await reply_queue.get(timeout=min(remaining, 0.25))
            except QueueEmpty:
                await asyncio.sleep(min(0.05, remaining))
                continue
            except TimeoutError:
                continue
            async with incoming.process(ignore_processed=True):
                reply = BusReplyV1.model_validate_json(incoming.body.decode("utf-8"))
                if reply.correlation_id != correlation_id:
                    continue
                return reply

    async def consume(
        self,
        *,
        queue_name: str,
        binding_keys: tuple[str, ...],
        callback: Any,
        durable: bool = True,
    ) -> AbstractQueue:
        if self._memory_mode:
            for binding_key in binding_keys:
                self._memory_consumers.append((binding_key, callback))
            return _MemoryQueue()

        channel = await self._require_channel()
        exchange = await self._require_exchange()
        queue = await channel.declare_queue(queue_name, durable=durable)
        for binding_key in binding_keys:
            await queue.bind(exchange=exchange, routing_key=binding_key)
        await queue.consume(callback)
        return queue

    async def reply(self, incoming: IncomingMessage, reply: BusReplyV1) -> None:
        if self._memory_mode:
            reply_queue = self._memory_reply_queues.get(str(incoming.reply_to))
            if reply_queue is None:
                return
            if reply_queue.full():
                _ = reply_queue.get_nowait()
            reply_queue.put_nowait(reply)
            return

        if not incoming.reply_to:
            return
        channel = await self._require_channel()
        outgoing = Message(
            body=reply.model_dump_json().encode("utf-8"),
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
            correlation_id=reply.correlation_id,
        )
        await channel.default_exchange.publish(outgoing, routing_key=incoming.reply_to)

    async def _require_channel(self) -> AbstractChannel:
        if self._channel is None or self._channel.is_closed:
            await self.connect()
        if self._channel is None:
            raise RuntimeError("AMQP channel is not initialized")
        return self._channel

    async def _require_exchange(self) -> AbstractExchange:
        if self._exchange is None:
            await self.connect()
        if self._exchange is None:
            raise RuntimeError("AMQP exchange is not initialized")
        return self._exchange

    @staticmethod
    async def _declare_topology(*, channel: AbstractChannel, exchange: AbstractExchange) -> None:
        storage_queue = await channel.declare_queue(QUEUE_STORAGE, durable=True)
        for key in ("storage.kv.*", "storage.table.*"):
            await storage_queue.bind(exchange=exchange, routing_key=key)

        actions_queue = await channel.declare_queue(QUEUE_ACTIONS, durable=True)
        await actions_queue.bind(exchange=exchange, routing_key=ROUTING_ACTION_EXECUTE)

        events_queue = await channel.declare_queue(QUEUE_EVENTS, durable=True)
        await events_queue.bind(exchange=exchange, routing_key=ROUTING_EVENT_PUBLISH)

        health_check_queue = await channel.declare_queue(QUEUE_HEALTH_CHECK_REQUEST, durable=True)
        await health_check_queue.bind(exchange=exchange, routing_key=ROUTING_HEALTH_CHECK_REQUEST)

        health_result_queue = await channel.declare_queue(QUEUE_HEALTH_CHECK_RESULT, durable=True)
        await health_result_queue.bind(exchange=exchange, routing_key=ROUTING_HEALTH_CHECK_RESULT)

    async def _dispatch_memory(self, *, routing_key: str, incoming: _MemoryIncomingMessage) -> None:
        for binding_key, callback in tuple(self._memory_consumers):
            if _routing_key_matches(binding_key, routing_key):
                await callback(incoming)


@dataclass
class _MemoryQueue:
    consumer_tags: tuple[str, ...] = ()


class _MemoryIncomingMessage:
    def __init__(self, *, body: bytes, correlation_id: str | None, reply_to: str | None) -> None:
        self.body = body
        self.correlation_id = correlation_id
        self.reply_to = reply_to

    @asynccontextmanager
    async def process(self, ignore_processed: bool = True):
        _ = ignore_processed
        yield self


def _routing_key_matches(pattern: str, key: str) -> bool:
    pattern_parts = pattern.split(".")
    key_parts = key.split(".")

    i = 0
    j = 0
    while i < len(pattern_parts) and j < len(key_parts):
        token = pattern_parts[i]
        if token == "#":
            return True
        if token == "*":
            i += 1
            j += 1
            continue
        if token != key_parts[j]:
            return False
        i += 1
        j += 1

    if i < len(pattern_parts) and pattern_parts[i] == "#":
        return True
    return i == len(pattern_parts) and j == len(key_parts)


__all__ = ["BusClient", "BusRpcTimeoutError"]
