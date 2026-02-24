from __future__ import annotations

from datetime import UTC, datetime

from aio_pika import IncomingMessage
from apps.health.model.contracts import HealthCheckResultV1, HealthStatusChangedV1
from apps.health.service.repository import HealthRepository
from apps.health.service.status import evaluate_health
from core.bus.client import BusClient
from core.contracts.bus import BusMessageV1
from core.events.protocols import EventPublisher


class HealthCheckResultConsumer:
    def __init__(
        self,
        *,
        bus_client: BusClient,
        repository: HealthRepository,
        event_publisher: EventPublisher,
        window_size: int,
    ) -> None:
        self._bus_client = bus_client
        self._repository = repository
        self._event_publisher = event_publisher
        self._window_size = max(1, window_size)

    async def start(self) -> None:
        await self._bus_client.consume(
            queue_name="oko.bus.health.check.result",
            binding_keys=("health.check.result",),
            callback=self._on_message,
            durable=True,
        )

    async def stop(self) -> None:
        return

    async def _on_message(self, incoming: IncomingMessage) -> None:
        async with incoming.process(ignore_processed=True):
            message = BusMessageV1.model_validate_json(incoming.body.decode("utf-8"))
            if message.type != "health.check.result":
                return
            if message.plugin_id != "core.health":
                return

            result = HealthCheckResultV1.model_validate(message.payload)
            await self._repository.insert_sample(result)
            service = await self._repository.get_service(result.service_id)
            if service is None:
                return
            samples = await self._repository.list_latest_samples(result.service_id, limit=self._window_size)
            evaluated = evaluate_health(
                samples=samples,
                latency_threshold_ms=service.latency_threshold_ms,
                window_size=self._window_size,
            )

            previous = await self._repository.get_state(result.service_id)
            previous_status = previous.current_status if previous is not None else None
            changed = previous is None or previous.current_status != evaluated.status

            last_change_ts = datetime.now(UTC) if changed else (previous.last_change_ts if previous is not None else result.checked_at)
            state = await self._repository.upsert_state(
                service_id=result.service_id,
                status=evaluated.status,
                last_change_ts=last_change_ts,
                avg_latency=evaluated.avg_latency_ms,
                success_rate=evaluated.success_rate,
                consecutive_failures=evaluated.consecutive_failures,
            )

            event = HealthStatusChangedV1(
                service_id=result.service_id,
                item_id=result.item_id,
                previous_status=previous_status,
                current_status=state.current_status,
                avg_latency_ms=state.avg_latency,
                success_rate=state.success_rate,
                consecutive_failures=state.consecutive_failures,
                window_size=self._window_size,
            )
            if changed:
                await self._event_publisher.publish(
                    event_type="health.status.changed",
                    source="apps.health.aggregator",
                    payload=event.model_dump(mode="json"),
                    correlation_id=message.correlation_id,
                )
                return

            await self._event_publisher.publish(
                event_type="health.status.updated",
                source="apps.health.aggregator",
                payload=event.model_dump(mode="json"),
                correlation_id=message.correlation_id,
            )


__all__ = ["HealthCheckResultConsumer"]
