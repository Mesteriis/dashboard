from __future__ import annotations

from collections.abc import Mapping
from threading import Lock
from typing import Any

from core.contracts.storage import PluginStorageConfig

from .errors import StorageQueryNotAllowed
from .protocols import PluginStorage


class StorageModeRouter:
    def __init__(
        self,
        *,
        plugin_configs: Mapping[str, PluginStorageConfig],
        universal_storage: PluginStorage,
        physical_storage: PluginStorage,
        lock_manager: Any | None = None,
    ) -> None:
        self._plugin_configs = dict(plugin_configs)
        self._universal_storage = universal_storage
        self._physical_storage = physical_storage
        self._lock_manager = lock_manager
        self._table_mode_overrides: dict[tuple[str, str], str] = {}
        self._guard = Lock()

    async def kv_get(self, *, plugin_id: str, key: str, secret: bool = False) -> Any | None:
        storage = self._storage_for(plugin_id, table=None)
        return await storage.kv_get(plugin_id=plugin_id, key=key, secret=secret)

    async def kv_set(self, *, plugin_id: str, key: str, value: Any, secret: bool = False) -> None:
        storage = self._storage_for(plugin_id, table=None)
        await storage.kv_set(plugin_id=plugin_id, key=key, value=value, secret=secret)

    async def kv_delete(self, *, plugin_id: str, key: str) -> bool:
        storage = self._storage_for(plugin_id, table=None)
        return await storage.kv_delete(plugin_id=plugin_id, key=key)

    async def table_get(self, *, plugin_id: str, table: str, pk: Any) -> dict[str, Any] | None:
        storage = self._storage_for(plugin_id, table=table)
        return await storage.table_get(plugin_id=plugin_id, table=table, pk=pk)

    async def table_upsert(self, *, plugin_id: str, table: str, row: Mapping[str, Any]) -> dict[str, Any]:
        self._ensure_write_allowed(plugin_id=plugin_id, table=table, operation="table_upsert")
        storage = self._storage_for(plugin_id, table=table)
        return await storage.table_upsert(plugin_id=plugin_id, table=table, row=row)

    async def table_delete(self, *, plugin_id: str, table: str, pk: Any) -> bool:
        self._ensure_write_allowed(plugin_id=plugin_id, table=table, operation="table_delete")
        storage = self._storage_for(plugin_id, table=table)
        return await storage.table_delete(plugin_id=plugin_id, table=table, pk=pk)

    async def table_query(
        self,
        *,
        plugin_id: str,
        table: str,
        where: Mapping[str, Any],
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        storage = self._storage_for(plugin_id, table=table)
        return await storage.table_query(plugin_id=plugin_id, table=table, where=where, limit=limit)

    def set_table_mode(self, *, plugin_id: str, table: str, mode: str) -> None:
        normalized_mode = mode.strip()
        if normalized_mode not in {"core_universal", "core_physical_tables"}:
            raise StorageQueryNotAllowed(f"Unsupported storage mode '{mode}'")
        with self._guard:
            self._table_mode_overrides[(plugin_id, table)] = normalized_mode

    def get_plugin_config(self, plugin_id: str) -> PluginStorageConfig:
        config = self._plugin_configs.get(plugin_id)
        if config is None:
            raise StorageQueryNotAllowed(f"Storage config for plugin '{plugin_id}' is not defined")
        return config

    def clear_table_mode_override(self, *, plugin_id: str, table: str) -> None:
        with self._guard:
            self._table_mode_overrides.pop((plugin_id, table), None)

    def get_table_mode(self, *, plugin_id: str, table: str) -> str:
        config = self._plugin_configs.get(plugin_id)
        if config is None:
            raise StorageQueryNotAllowed(f"Storage config for plugin '{plugin_id}' is not defined")

        with self._guard:
            override = self._table_mode_overrides.get((plugin_id, table))
        if override:
            return override
        return config.mode

    def _storage_for(self, plugin_id: str, table: str | None) -> PluginStorage:
        config = self._plugin_configs.get(plugin_id)
        if config is None:
            raise StorageQueryNotAllowed(f"Storage config for plugin '{plugin_id}' is not defined")

        resolved_mode = config.mode if table is None else self.get_table_mode(plugin_id=plugin_id, table=table)

        if resolved_mode == "core_universal":
            return self._universal_storage

        if resolved_mode == "core_physical_tables":
            return self._physical_storage

        raise StorageQueryNotAllowed(f"Unsupported storage mode '{resolved_mode}' for plugin '{plugin_id}'")

    def _ensure_write_allowed(self, *, plugin_id: str, table: str, operation: str) -> None:
        if self._lock_manager is None:
            return
        if self._lock_manager.is_table_write_locked(plugin_id=plugin_id, table=table):
            raise StorageQueryNotAllowed(
                f"Storage table '{table}' for plugin '{plugin_id}' is read-only during migration; operation "
                f"'{operation}' is denied"
            )


__all__ = ["StorageModeRouter"]
