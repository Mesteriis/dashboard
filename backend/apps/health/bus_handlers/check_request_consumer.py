from __future__ import annotations

from aio_pika import IncomingMessage
from apps.health.model.contracts import HealthCheckRequestedV1
from apps.health.service.checkers import HealthChecker
from core.bus.client import BusClient
from core.contracts.bus import BusMessageV1


class HealthCheckRequestConsumer:
    def __init__(self, *, bus_client: BusClient, checker: HealthChecker) -> None:
        self._bus_client = bus_client
        self._checker = checker

    async def start(self) -> None:
        await self._bus_client.consume(
            queue_name="oko.bus.health.check.request",
            binding_keys=("health.check.request",),
            callback=self._on_message,
            durable=True,
        )

    async def stop(self) -> None:
        return

    async def _on_message(self, incoming: IncomingMessage) -> None:
        async with incoming.process(ignore_processed=True):
            message = BusMessageV1.model_validate_json(incoming.body.decode("utf-8"))
            if message.type != "health.check.request":
                return
            if message.plugin_id != "core.health":
                return

            payload = HealthCheckRequestedV1.model_validate(message.payload)
            result = await self._checker.run(payload)
            await self._bus_client.emit(
                message=BusMessageV1(
                    type="health.check.result",
                    plugin_id="core.health",
                    correlation_id=message.correlation_id,
                    payload=result.model_dump(mode="json"),
                ),
                routing_key="health.check.result",
            )


__all__ = ["HealthCheckRequestConsumer"]
