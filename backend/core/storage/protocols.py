from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from core.contracts.storage import StorageRpcRequest, StorageRpcResponse


class PluginStorage(Protocol):
    async def kv_get(self, *, plugin_id: str, key: str, secret: bool = False) -> Any | None: ...

    async def kv_set(self, *, plugin_id: str, key: str, value: Any, secret: bool = False) -> None: ...

    async def kv_delete(self, *, plugin_id: str, key: str) -> bool: ...

    async def table_get(self, *, plugin_id: str, table: str, pk: Any) -> dict[str, Any] | None: ...

    async def table_upsert(self, *, plugin_id: str, table: str, row: Mapping[str, Any]) -> dict[str, Any]: ...

    async def table_delete(self, *, plugin_id: str, table: str, pk: Any) -> bool: ...

    async def table_query(
        self,
        *,
        plugin_id: str,
        table: str,
        where: Mapping[str, Any],
        limit: int | None = None,
    ) -> list[dict[str, Any]]: ...


class StorageRPC(Protocol):
    async def call(self, request: StorageRpcRequest) -> StorageRpcResponse: ...

    async def kv_get(self, *, plugin_id: str, key: str, secret: bool = False) -> Any | None: ...

    async def kv_set(self, *, plugin_id: str, key: str, value: Any, secret: bool = False) -> None: ...

    async def kv_delete(self, *, plugin_id: str, key: str) -> bool: ...

    async def table_get(self, *, plugin_id: str, table: str, pk: Any) -> dict[str, Any] | None: ...

    async def table_upsert(self, *, plugin_id: str, table: str, row: Mapping[str, Any]) -> dict[str, Any]: ...

    async def table_delete(self, *, plugin_id: str, table: str, pk: Any) -> bool: ...

    async def table_query(
        self,
        *,
        plugin_id: str,
        table: str,
        where: Mapping[str, Any],
        limit: int | None = None,
    ) -> list[dict[str, Any]]: ...


__all__ = ["PluginStorage", "StorageRPC"]
