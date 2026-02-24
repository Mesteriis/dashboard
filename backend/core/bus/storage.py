from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from aio_pika import IncomingMessage
from core.contracts.bus import (
    BusMessageV1,
    BusReplyV1,
    StorageKvDeletePayload,
    StorageKvGetPayload,
    StorageKvSetPayload,
    StorageTableDeletePayload,
    StorageTableGetPayload,
    StorageTableQueryPayload,
    StorageTableUpsertPayload,
)
from core.contracts.storage import (
    PluginStorageConfig,
    StorageLimits,
    StorageRpcRequest,
    StorageRpcResponse,
    StorageTableSpec,
)
from core.storage.errors import (
    StorageDdlNotAllowed,
    StorageError,
    StorageLimitExceeded,
    StorageQueryNotAllowed,
    StorageRateLimited,
    StorageRpcTimeout,
)
from core.storage.protocols import PluginStorage

from .client import BusClient, BusRpcTimeoutError
from .constants import QUEUE_STORAGE
from .quota import PluginQuotaGuard


def _error_payload(error: StorageError) -> dict[str, Any]:
    return {
        "code": error.code,
        "message": error.message,
        "ts": datetime.now(UTC).isoformat(),
    }


def _error_to_exception(payload: Mapping[str, Any] | None) -> StorageError:
    code = str((payload or {}).get("code", "storage_error"))
    message = str((payload or {}).get("message", "Storage operation failed"))
    if code == StorageLimitExceeded.code:
        return StorageLimitExceeded(message)
    if code == StorageQueryNotAllowed.code:
        return StorageQueryNotAllowed(message)
    if code == StorageRateLimited.code:
        return StorageRateLimited(message)
    if code == StorageDdlNotAllowed.code:
        return StorageDdlNotAllowed(message)
    if code == StorageRpcTimeout.code:
        return StorageRpcTimeout(message)
    return StorageError(message)


def _ensure_ok(reply: BusReplyV1) -> Mapping[str, Any]:
    if reply.ok:
        result = reply.result or {}
        if isinstance(result, dict):
            return result
        raise StorageError("Storage response payload is invalid")
    raise _error_to_exception(reply.error)


def _ensure_response_ok(response: StorageRpcResponse) -> Mapping[str, Any]:
    return _ensure_ok(
        BusReplyV1(
            correlation_id=str(response.id),
            ok=response.ok,
            error=response.error,
            result=response.result,
        )
    )


class BrokerStorageRPC:
    def __init__(self, *, bus_client: BusClient, timeout_sec: float = 2.0) -> None:
        self._bus_client = bus_client
        self._timeout_sec = timeout_sec

    async def call(self, request: StorageRpcRequest) -> StorageRpcResponse:
        message = BusMessageV1(
            id=request.id,
            ts=request.ts,
            type=f"storage.{request.op}",
            plugin_id=request.plugin_id,
            payload=self._request_payload(request),
        )
        try:
            reply = await self._bus_client.call(
                message=message,
                routing_key=message.type,
                timeout_sec=self._timeout_sec,
            )
        except BusRpcTimeoutError:
            timeout_error = StorageRpcTimeout(f"Storage RPC timeout waiting for '{request.op}'")
            return StorageRpcResponse(id=request.id, ok=False, error=_error_payload(timeout_error))
        return StorageRpcResponse(id=request.id, ok=reply.ok, error=reply.error, result=reply.result)

    async def kv_get(self, *, plugin_id: str, key: str, secret: bool = False) -> Any | None:
        response = await self.call(StorageRpcRequest(plugin_id=plugin_id, op="kv.get", key=key, secret=secret))
        payload = _ensure_response_ok(response)
        return payload.get("value")

    async def kv_set(self, *, plugin_id: str, key: str, value: Any, secret: bool = False) -> None:
        response = await self.call(
            StorageRpcRequest(plugin_id=plugin_id, op="kv.set", key=key, row={"value": value}, secret=secret)
        )
        _ = _ensure_response_ok(response)

    async def kv_delete(self, *, plugin_id: str, key: str) -> bool:
        response = await self.call(StorageRpcRequest(plugin_id=plugin_id, op="kv.delete", key=key))
        payload = _ensure_response_ok(response)
        return bool(payload.get("deleted", False))

    async def table_get(self, *, plugin_id: str, table: str, pk: Any) -> dict[str, Any] | None:
        response = await self.call(StorageRpcRequest(plugin_id=plugin_id, op="table.get", table=table, key=pk))
        payload = _ensure_response_ok(response)
        row = payload.get("row")
        if row is None:
            return None
        if not isinstance(row, dict):
            raise StorageError("Invalid table.get response payload")
        return row

    async def table_upsert(self, *, plugin_id: str, table: str, row: Mapping[str, Any]) -> dict[str, Any]:
        response = await self.call(
            StorageRpcRequest(plugin_id=plugin_id, op="table.upsert", table=table, row=dict(row))
        )
        payload = _ensure_response_ok(response)
        stored = payload.get("row")
        if not isinstance(stored, dict):
            raise StorageError("Invalid table.upsert response payload")
        return stored

    async def table_delete(self, *, plugin_id: str, table: str, pk: Any) -> bool:
        response = await self.call(StorageRpcRequest(plugin_id=plugin_id, op="table.delete", table=table, key=pk))
        payload = _ensure_response_ok(response)
        return bool(payload.get("deleted", False))

    async def table_query(
        self,
        *,
        plugin_id: str,
        table: str,
        where: Mapping[str, Any],
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        response = await self.call(
            StorageRpcRequest(
                plugin_id=plugin_id,
                op="table.query",
                table=table,
                where=dict(where),
                limit=limit,
            )
        )
        payload = _ensure_response_ok(response)
        rows = payload.get("rows", [])
        if not isinstance(rows, list):
            raise StorageError("Invalid table.query response payload")
        return [item for item in rows if isinstance(item, dict)]

    @staticmethod
    def _request_payload(request: StorageRpcRequest) -> dict[str, Any]:
        if request.op == "kv.get":
            return StorageKvGetPayload(key=str(request.key), secret=bool(request.secret)).model_dump(mode="json")
        if request.op == "kv.set":
            row = dict(request.row or {})
            if "value" not in row:
                raise StorageQueryNotAllowed("kv.set requires row.value")
            return StorageKvSetPayload(
                key=str(request.key),
                value=row["value"],
                secret=bool(request.secret),
            ).model_dump(mode="json")
        if request.op == "kv.delete":
            return StorageKvDeletePayload(key=str(request.key)).model_dump(mode="json")
        if request.op == "table.get":
            return StorageTableGetPayload(table=str(request.table), key=request.key).model_dump(mode="json")
        if request.op == "table.upsert":
            return StorageTableUpsertPayload(
                table=str(request.table),
                row=dict(request.row or {}),
            ).model_dump(mode="json")
        if request.op == "table.delete":
            return StorageTableDeletePayload(table=str(request.table), key=request.key).model_dump(mode="json")
        if request.op == "table.query":
            return StorageTableQueryPayload(
                table=str(request.table),
                where=dict(request.where or {}),
                limit=request.limit,
            ).model_dump(mode="json")
        raise StorageQueryNotAllowed(f"Unsupported storage operation: {request.op}")


class StorageBusConsumer:
    def __init__(
        self,
        *,
        bus_client: BusClient,
        storage: PluginStorage,
        plugin_configs: Mapping[str, PluginStorageConfig],
        capabilities: Mapping[str, set[str]] | None = None,
    ) -> None:
        self._bus_client = bus_client
        self._storage = storage
        self._plugin_configs = dict(plugin_configs)
        self._capabilities = {plugin_id: set(values) for plugin_id, values in (capabilities or {}).items()}
        self._quota = PluginQuotaGuard()

    async def start(self) -> None:
        await self._bus_client.consume(
            queue_name=QUEUE_STORAGE,
            binding_keys=("storage.kv.*", "storage.table.*"),
            callback=self._on_message,
            durable=True,
        )

    async def stop(self) -> None:
        return

    async def _on_message(self, incoming: IncomingMessage) -> None:
        async with incoming.process(ignore_processed=True):
            message = BusMessageV1.model_validate_json(incoming.body.decode("utf-8"))
            correlation_id = message.correlation_id or str(message.id)

            try:
                result = await self._handle_message(message)
                reply = BusReplyV1(correlation_id=correlation_id, ok=True, result=result)
            except StorageError as exc:
                reply = BusReplyV1(correlation_id=correlation_id, ok=False, error=_error_payload(exc))
            except Exception as exc:  # pragma: no cover - defensive
                wrapped = StorageError(str(exc))
                reply = BusReplyV1(correlation_id=correlation_id, ok=False, error=_error_payload(wrapped))

            await self._bus_client.reply(incoming, reply)

    async def _handle_message(self, message: BusMessageV1) -> dict[str, Any]:
        limits, table_specs = self._resolve_plugin(message.plugin_id)
        self._enforce_capability(plugin_id=message.plugin_id, op=message.type)
        self._quota.enforce_qps(plugin_id=message.plugin_id, message_type=message.type, limits=limits)

        if message.type == "storage.kv.get":
            payload = StorageKvGetPayload.model_validate(message.payload)
            value = await self._storage.kv_get(plugin_id=message.plugin_id, key=payload.key, secret=payload.secret)
            return {"value": value}

        if message.type == "storage.kv.set":
            payload = StorageKvSetPayload.model_validate(message.payload)
            self._quota.enforce_kv_bytes(value=payload.value, limits=limits)
            await self._storage.kv_set(
                plugin_id=message.plugin_id,
                key=payload.key,
                value=payload.value,
                secret=payload.secret,
            )
            return {"ok": True}

        if message.type == "storage.kv.delete":
            payload = StorageKvDeletePayload.model_validate(message.payload)
            deleted = await self._storage.kv_delete(plugin_id=message.plugin_id, key=payload.key)
            return {"deleted": deleted}

        if message.type == "storage.table.get":
            payload = StorageTableGetPayload.model_validate(message.payload)
            row = await self._storage.table_get(plugin_id=message.plugin_id, table=payload.table, pk=payload.key)
            return {"row": row}

        if message.type == "storage.table.upsert":
            payload = StorageTableUpsertPayload.model_validate(message.payload)
            self._quota.enforce_row_bytes(row=dict(payload.row), limits=limits)
            row = await self._storage.table_upsert(plugin_id=message.plugin_id, table=payload.table, row=payload.row)
            return {"row": row}

        if message.type == "storage.table.delete":
            payload = StorageTableDeletePayload.model_validate(message.payload)
            deleted = await self._storage.table_delete(plugin_id=message.plugin_id, table=payload.table, pk=payload.key)
            return {"deleted": deleted}

        if message.type == "storage.table.query":
            payload = StorageTableQueryPayload.model_validate(message.payload)
            self._enforce_table_query_policy(
                table=payload.table,
                where=payload.where,
                table_specs=table_specs,
            )
            limit = self._quota.clamp_query_limit(requested=payload.limit, limits=limits)
            rows = await self._storage.table_query(
                plugin_id=message.plugin_id,
                table=payload.table,
                where=payload.where,
                limit=limit,
            )
            return {"rows": rows}

        raise StorageQueryNotAllowed(f"Unsupported storage operation: {message.type}")

    def _resolve_plugin(self, plugin_id: str) -> tuple[StorageLimits, dict[str, StorageTableSpec]]:
        config = self._plugin_configs.get(plugin_id)
        if config is None:
            raise StorageQueryNotAllowed(f"Storage config for plugin '{plugin_id}' is not defined")
        table_specs = {table.name: table for table in config.tables}
        return config.limits, table_specs

    def _enforce_capability(self, *, plugin_id: str, op: str) -> None:
        allowed = self._capabilities.get(plugin_id)
        if allowed is None:
            raise StorageQueryNotAllowed(f"Operation '{op}' is not allowed for plugin '{plugin_id}'")
        if "*" in allowed or op in allowed:
            return
        raise StorageQueryNotAllowed(f"Operation '{op}' is not allowed for plugin '{plugin_id}'")

    @staticmethod
    def _enforce_table_query_policy(
        *,
        table: str,
        where: Mapping[str, Any],
        table_specs: Mapping[str, StorageTableSpec],
    ) -> None:
        if not where:
            raise StorageQueryNotAllowed("table_query requires non-empty where")
        spec = table_specs.get(table)
        if spec is None:
            raise StorageQueryNotAllowed(f"Table '{table}' is not allowed")
        allowed_fields = {spec.primary_key, *spec.indexes}
        for field, value in where.items():
            if field not in allowed_fields:
                raise StorageQueryNotAllowed(f"Field '{field}' is not indexed or primary key")
            if not (value is None or isinstance(value, str | int | float | bool)):
                raise StorageQueryNotAllowed("table_query supports scalar equality only")


__all__ = ["BrokerStorageRPC", "StorageBusConsumer"]
