from __future__ import annotations

import asyncio
from collections.abc import Mapping
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from core.contracts.storage import StorageRpcRequest, StorageRpcResponse

from .errors import (
    StorageDdlNotAllowed,
    StorageError,
    StorageLimitExceeded,
    StorageQueryNotAllowed,
    StorageRateLimited,
    StorageRpcTimeout,
)
from .protocols import PluginStorage
from .rpc_bus import StorageRpcBus

STORAGE_RPC_QUEUE = "oko.storage.rpc.v1"


@dataclass(frozen=True)
class StorageRpcEnvelope:
    correlation_id: UUID
    reply_to: str
    request: StorageRpcRequest


@dataclass(frozen=True)
class StorageRpcReply:
    correlation_id: UUID
    response: StorageRpcResponse


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


class InProcStorageRPC:
    def __init__(self, *, storage: PluginStorage) -> None:
        self._storage = storage

    async def call(self, request: StorageRpcRequest) -> StorageRpcResponse:
        try:
            result = await self._dispatch(request)
            return StorageRpcResponse(id=request.id, ok=True, result=result)
        except StorageError as exc:
            return StorageRpcResponse(id=request.id, ok=False, error=_error_payload(exc))
        except Exception as exc:
            error = StorageError(str(exc))
            return StorageRpcResponse(id=request.id, ok=False, error=_error_payload(error))

    async def _dispatch(self, request: StorageRpcRequest) -> dict[str, Any] | None:
        if request.op == "kv.get":
            key = _require_text(request.key, "key")
            value = await self._storage.kv_get(
                plugin_id=request.plugin_id,
                key=key,
                secret=bool(request.secret),
            )
            return {"value": value}

        if request.op == "kv.set":
            key = _require_text(request.key, "key")
            row = _require_mapping(request.row, "row")
            if "value" not in row:
                raise StorageQueryNotAllowed("kv.set requires row.value")
            await self._storage.kv_set(
                plugin_id=request.plugin_id,
                key=key,
                value=row["value"],
                secret=bool(request.secret),
            )
            return {"ok": True}

        if request.op == "kv.delete":
            key = _require_text(request.key, "key")
            deleted = await self._storage.kv_delete(plugin_id=request.plugin_id, key=key)
            return {"deleted": deleted}

        if request.op == "table.get":
            table = _require_text(request.table, "table")
            pk = _require_value(request.key, "key")
            row = await self._storage.table_get(plugin_id=request.plugin_id, table=table, pk=pk)
            return {"row": row}

        if request.op == "table.upsert":
            table = _require_text(request.table, "table")
            payload = _require_mapping(request.row, "row")
            row = await self._storage.table_upsert(plugin_id=request.plugin_id, table=table, row=payload)
            return {"row": row}

        if request.op == "table.delete":
            table = _require_text(request.table, "table")
            pk = _require_value(request.key, "key")
            deleted = await self._storage.table_delete(plugin_id=request.plugin_id, table=table, pk=pk)
            return {"deleted": deleted}

        if request.op == "table.query":
            table = _require_text(request.table, "table")
            where = _require_mapping(request.where, "where")
            rows = await self._storage.table_query(
                plugin_id=request.plugin_id,
                table=table,
                where=where,
                limit=request.limit,
            )
            return {"rows": rows}

        raise StorageQueryNotAllowed(f"Unsupported storage operation: {request.op}")

    async def kv_get(self, *, plugin_id: str, key: str, secret: bool = False) -> Any | None:
        response = await self.call(
            StorageRpcRequest(
                plugin_id=plugin_id,
                op="kv.get",
                key=key,
                secret=secret,
            )
        )
        payload = _ensure_ok(response)
        return payload.get("value")

    async def kv_set(self, *, plugin_id: str, key: str, value: Any, secret: bool = False) -> None:
        response = await self.call(
            StorageRpcRequest(
                plugin_id=plugin_id,
                op="kv.set",
                key=key,
                row={"value": value},
                secret=secret,
            )
        )
        _ = _ensure_ok(response)

    async def kv_delete(self, *, plugin_id: str, key: str) -> bool:
        response = await self.call(
            StorageRpcRequest(
                plugin_id=plugin_id,
                op="kv.delete",
                key=key,
            )
        )
        payload = _ensure_ok(response)
        return bool(payload.get("deleted", False))

    async def table_get(self, *, plugin_id: str, table: str, pk: Any) -> dict[str, Any] | None:
        response = await self.call(
            StorageRpcRequest(
                plugin_id=plugin_id,
                op="table.get",
                table=table,
                key=pk,
            )
        )
        payload = _ensure_ok(response)
        row = payload.get("row")
        if row is None:
            return None
        if not isinstance(row, dict):
            raise StorageError("Invalid table.get response payload")
        return row

    async def table_upsert(self, *, plugin_id: str, table: str, row: Mapping[str, Any]) -> dict[str, Any]:
        response = await self.call(
            StorageRpcRequest(
                plugin_id=plugin_id,
                op="table.upsert",
                table=table,
                row=dict(row),
            )
        )
        payload = _ensure_ok(response)
        stored_row = payload.get("row")
        if not isinstance(stored_row, dict):
            raise StorageError("Invalid table.upsert response payload")
        return stored_row

    async def table_delete(self, *, plugin_id: str, table: str, pk: Any) -> bool:
        response = await self.call(
            StorageRpcRequest(
                plugin_id=plugin_id,
                op="table.delete",
                table=table,
                key=pk,
            )
        )
        payload = _ensure_ok(response)
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
        payload = _ensure_ok(response)
        rows = payload.get("rows", [])
        if not isinstance(rows, list):
            raise StorageError("Invalid table.query response payload")

        normalized_rows: list[dict[str, Any]] = []
        for item in rows:
            if isinstance(item, dict):
                normalized_rows.append(item)
        return normalized_rows


class BusStorageRPC:
    def __init__(
        self,
        *,
        bus: StorageRpcBus,
        queue_name: str = STORAGE_RPC_QUEUE,
        timeout_sec: float = 2.0,
    ) -> None:
        self._bus = bus
        self._queue_name = queue_name
        self._timeout_sec = timeout_sec

    async def call(self, request: StorageRpcRequest) -> StorageRpcResponse:
        reply_to = f"{self._queue_name}.reply.{uuid4()}"
        queue = self._bus.subscribe(queue_name=reply_to)

        envelope = StorageRpcEnvelope(
            correlation_id=request.id,
            reply_to=reply_to,
            request=request,
        )

        try:
            await self._bus.publish(queue_name=self._queue_name, message=envelope)
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=self._timeout_sec)
                except TimeoutError:
                    error = StorageRpcTimeout(
                        f"Storage RPC timeout waiting for '{request.op}' response on '{self._queue_name}'"
                    )
                    return StorageRpcResponse(id=request.id, ok=False, error=_error_payload(error))

                if not isinstance(message, StorageRpcReply):
                    continue
                if message.correlation_id != request.id:
                    continue
                return message.response
        finally:
            self._bus.unsubscribe(queue_name=reply_to, queue=queue)

    async def kv_get(self, *, plugin_id: str, key: str, secret: bool = False) -> Any | None:
        response = await self.call(
            StorageRpcRequest(
                plugin_id=plugin_id,
                op="kv.get",
                key=key,
                secret=secret,
            )
        )
        payload = _ensure_ok(response)
        return payload.get("value")

    async def kv_set(self, *, plugin_id: str, key: str, value: Any, secret: bool = False) -> None:
        response = await self.call(
            StorageRpcRequest(
                plugin_id=plugin_id,
                op="kv.set",
                key=key,
                row={"value": value},
                secret=secret,
            )
        )
        _ = _ensure_ok(response)

    async def kv_delete(self, *, plugin_id: str, key: str) -> bool:
        response = await self.call(
            StorageRpcRequest(
                plugin_id=plugin_id,
                op="kv.delete",
                key=key,
            )
        )
        payload = _ensure_ok(response)
        return bool(payload.get("deleted", False))

    async def table_get(self, *, plugin_id: str, table: str, pk: Any) -> dict[str, Any] | None:
        response = await self.call(
            StorageRpcRequest(
                plugin_id=plugin_id,
                op="table.get",
                table=table,
                key=pk,
            )
        )
        payload = _ensure_ok(response)
        row = payload.get("row")
        if row is None:
            return None
        if not isinstance(row, dict):
            raise StorageError("Invalid table.get response payload")
        return row

    async def table_upsert(self, *, plugin_id: str, table: str, row: Mapping[str, Any]) -> dict[str, Any]:
        response = await self.call(
            StorageRpcRequest(
                plugin_id=plugin_id,
                op="table.upsert",
                table=table,
                row=dict(row),
            )
        )
        payload = _ensure_ok(response)
        stored_row = payload.get("row")
        if not isinstance(stored_row, dict):
            raise StorageError("Invalid table.upsert response payload")
        return stored_row

    async def table_delete(self, *, plugin_id: str, table: str, pk: Any) -> bool:
        response = await self.call(
            StorageRpcRequest(
                plugin_id=plugin_id,
                op="table.delete",
                table=table,
                key=pk,
            )
        )
        payload = _ensure_ok(response)
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
        payload = _ensure_ok(response)
        rows = payload.get("rows", [])
        if not isinstance(rows, list):
            raise StorageError("Invalid table.query response payload")

        normalized_rows: list[dict[str, Any]] = []
        for item in rows:
            if isinstance(item, dict):
                normalized_rows.append(item)
        return normalized_rows


class StorageRpcConsumer:
    def __init__(
        self,
        *,
        bus: StorageRpcBus,
        storage: PluginStorage,
        queue_name: str = STORAGE_RPC_QUEUE,
        capabilities: Mapping[str, set[str]] | None = None,
    ) -> None:
        self._bus = bus
        self._queue_name = queue_name
        self._capabilities = dict(capabilities or {})
        self._inproc = InProcStorageRPC(storage=storage)
        self._task: asyncio.Task[None] | None = None
        self._ready = asyncio.Event()

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._ready = asyncio.Event()
        self._task = asyncio.create_task(self._run(), name="storage-rpc-consumer")
        try:
            await asyncio.wait_for(self._ready.wait(), timeout=1.0)
        except Exception:
            await self.stop()
            raise

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None
        self._ready = asyncio.Event()

    async def _run(self) -> None:
        queue = self._bus.subscribe(queue_name=self._queue_name)
        self._ready.set()
        try:
            while True:
                envelope = await queue.get()
                if not isinstance(envelope, StorageRpcEnvelope):
                    continue
                response = await self._handle_request(envelope.request)
                reply = StorageRpcReply(correlation_id=envelope.correlation_id, response=response)
                await self._bus.publish(queue_name=envelope.reply_to, message=reply)
        finally:
            self._bus.unsubscribe(queue_name=self._queue_name, queue=queue)

    async def _handle_request(self, request: StorageRpcRequest) -> StorageRpcResponse:
        if not self._is_allowed(plugin_id=request.plugin_id, op=request.op):
            error = StorageQueryNotAllowed(f"Operation '{request.op}' is not allowed for plugin '{request.plugin_id}'")
            return StorageRpcResponse(id=request.id, ok=False, error=_error_payload(error))
        return await self._inproc.call(request)

    def _is_allowed(self, *, plugin_id: str, op: str) -> bool:
        allowed = self._capabilities.get(plugin_id)
        if allowed is None:
            return False
        if "*" in allowed:
            return True
        return op in allowed


def _require_text(value: Any | None, field: str) -> str:
    if value is None:
        raise StorageQueryNotAllowed(f"Storage request field '{field}' is required")
    text = str(value).strip()
    if text:
        return text
    raise StorageQueryNotAllowed(f"Storage request field '{field}' is required")


def _require_mapping(value: Mapping[str, Any] | None, field: str) -> Mapping[str, Any]:
    if value is None:
        raise StorageQueryNotAllowed(f"Storage request field '{field}' is required")
    return value


def _require_value(value: Any | None, field: str) -> Any:
    if value is None:
        raise StorageQueryNotAllowed(f"Storage request field '{field}' is required")
    return value


def _ensure_ok(response: StorageRpcResponse) -> Mapping[str, Any]:
    if response.ok:
        result = response.result or {}
        if isinstance(result, dict):
            return result
        raise StorageError("Storage response payload is invalid")

    raise _error_to_exception(response.error)


__all__ = [
    "STORAGE_RPC_QUEUE",
    "BusStorageRPC",
    "InProcStorageRPC",
    "StorageRpcBus",
    "StorageRpcConsumer",
    "StorageRpcEnvelope",
    "StorageRpcReply",
]
