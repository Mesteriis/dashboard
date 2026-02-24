from __future__ import annotations

from collections.abc import Iterable
from contextlib import contextmanager
from threading import Lock


class StorageMigrationLockManager:
    def __init__(self) -> None:
        self._guard = Lock()
        self._table_locks: dict[tuple[str, str], int] = {}

    @contextmanager
    def read_only_lock(self, *, plugin_id: str, tables: Iterable[str]):
        normalized_tables = sorted({table.strip() for table in tables if table.strip()})
        if not normalized_tables:
            raise ValueError("Migration lock requires at least one table")

        keys = [(plugin_id, table) for table in normalized_tables]
        with self._guard:
            for key in keys:
                self._table_locks[key] = self._table_locks.get(key, 0) + 1

        try:
            yield
        finally:
            with self._guard:
                for key in keys:
                    current = self._table_locks.get(key, 0)
                    if current <= 1:
                        self._table_locks.pop(key, None)
                    else:
                        self._table_locks[key] = current - 1

    def is_table_write_locked(self, *, plugin_id: str, table: str) -> bool:
        with self._guard:
            return (plugin_id, table) in self._table_locks


__all__ = ["StorageMigrationLockManager"]
