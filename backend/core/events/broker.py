from __future__ import annotations

from contextlib import suppress
from datetime import UTC, datetime
from uuid import uuid4

from aio_pika import IncomingMessage
from core.bus.client import BusClient
from core.bus.constants import QUEUE_EVENTS, ROUTING_EVENT_PUBLISH
from core.contracts.bus import BusMessageV1, EventPublishPayload
from core.contracts.models import EventEnvelope

from .bus import EventBus


class BrokerEventPublisher:
    def __init__(self, *, bus_client: BusClient) -> None:
        self._bus_client = bus_client
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
        publish_payload = EventPublishPayload(
            event_type=envelope.type,
            source=envelope.source,
            payload=envelope.payload,
            correlation_id=envelope.correlation_id,
            revision=envelope.revision,
        )
        await self._bus_client.emit(
            message=BusMessageV1(
                type="event.publish",
                plugin_id="core",
                payload=publish_payload.model_dump(mode="json"),
            ),
            routing_key=ROUTING_EVENT_PUBLISH,
        )
        return envelope


class EventPublishConsumer:
    def __init__(self, *, bus_client: BusClient, event_bus: EventBus) -> None:
        self._bus_client = bus_client
        self._event_bus = event_bus
        self._consumer_tag: str | None = None
        self._queue_name = QUEUE_EVENTS

    async def start(self) -> None:
        queue = await self._bus_client.consume(
            queue_name=self._queue_name,
            binding_keys=(ROUTING_EVENT_PUBLISH,),
            callback=self._on_message,
            durable=True,
        )
        with suppress(Exception):
            self._consumer_tag = queue.consumer_tags[0] if queue.consumer_tags else None

    async def stop(self) -> None:
        self._consumer_tag = None

    async def _on_message(self, incoming: IncomingMessage) -> None:
        async with incoming.process(ignore_processed=True):
            message = BusMessageV1.model_validate_json(incoming.body.decode("utf-8"))
            if message.type != "event.publish":
                return
            payload = EventPublishPayload.model_validate(message.payload)
            await self._event_bus.publish(
                event_type=payload.event_type,
                source=payload.source,
                payload=payload.payload,
                correlation_id=payload.correlation_id,
                revision=payload.revision,
            )


__all__ = ["BrokerEventPublisher", "EventPublishConsumer"]
