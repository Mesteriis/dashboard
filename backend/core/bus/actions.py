from __future__ import annotations

from typing import Any

from aio_pika import IncomingMessage
from core.contracts.bus import ActionExecutePayload, BusMessageV1, BusReplyV1
from core.contracts.errors import ApiError
from core.contracts.models import ActionEnvelope, ActionExecutionResponse
from core.gateway import ActionGateway

from .client import BusClient, BusRpcTimeoutError
from .constants import QUEUE_ACTIONS, ROUTING_ACTION_EXECUTE


def _api_error_payload(error: ApiError) -> dict[str, Any]:
    payload = error.error.model_dump(mode="json")
    payload["status_code"] = error.status_code
    return payload


class BrokerActionRPC:
    def __init__(self, *, bus_client: BusClient, timeout_sec: float = 5.0) -> None:
        self._bus_client = bus_client
        self._timeout_sec = timeout_sec

    async def execute(self, *, action: ActionEnvelope, actor: str) -> ActionExecutionResponse:
        message = BusMessageV1(
            type="action.execute",
            plugin_id="core",
            payload=ActionExecutePayload(action=action.model_dump(mode="json"), actor=actor).model_dump(mode="json"),
        )
        try:
            reply = await self._bus_client.call(
                message=message,
                routing_key=ROUTING_ACTION_EXECUTE,
                timeout_sec=self._timeout_sec,
            )
        except BusRpcTimeoutError as exc:
            raise ApiError(
                status_code=504,
                code="action_rpc_timeout",
                message="Action execution timed out waiting for worker reply",
                retryable=True,
            ) from exc

        if not reply.ok:
            error_payload = dict(reply.error or {})
            status_code = int(error_payload.pop("status_code", 500))
            code = str(error_payload.get("code", "action_rpc_failed"))
            message = str(error_payload.get("message", "Action execution failed"))
            details = error_payload.get("details")
            if not isinstance(details, list):
                details = []
            raise ApiError(
                status_code=status_code,
                code=code,
                message=message,
                details=[item for item in details if isinstance(item, dict)],
            )

        result = reply.result or {}
        return ActionExecutionResponse.model_validate(result)


class ActionBusConsumer:
    def __init__(self, *, bus_client: BusClient, gateway: ActionGateway) -> None:
        self._bus_client = bus_client
        self._gateway = gateway

    async def start(self) -> None:
        await self._bus_client.consume(
            queue_name=QUEUE_ACTIONS,
            binding_keys=(ROUTING_ACTION_EXECUTE,),
            callback=self._on_message,
            durable=True,
        )

    async def stop(self) -> None:
        return

    async def _on_message(self, incoming: IncomingMessage) -> None:
        async with incoming.process(ignore_processed=True):
            message = BusMessageV1.model_validate_json(incoming.body.decode("utf-8"))
            correlation_id = message.correlation_id or str(message.id)

            if message.type != "action.execute":
                await self._bus_client.reply(
                    incoming,
                    BusReplyV1(
                        correlation_id=correlation_id,
                        ok=False,
                        error={"code": "action_type_not_supported", "message": message.type},
                    ),
                )
                return

            try:
                payload = ActionExecutePayload.model_validate(message.payload)
                action = ActionEnvelope.model_validate(payload.action)
                response = await self._gateway.execute_action(action=action, actor=payload.actor)
                reply = BusReplyV1(
                    correlation_id=correlation_id,
                    ok=True,
                    result=response.model_dump(mode="json"),
                )
            except ApiError as exc:
                reply = BusReplyV1(correlation_id=correlation_id, ok=False, error=_api_error_payload(exc))
            except Exception as exc:  # pragma: no cover - defensive
                fallback = ApiError(status_code=500, code="action_execute_failed", message=str(exc))
                reply = BusReplyV1(correlation_id=correlation_id, ok=False, error=_api_error_payload(fallback))

            await self._bus_client.reply(incoming, reply)


__all__ = ["ActionBusConsumer", "BrokerActionRPC"]
