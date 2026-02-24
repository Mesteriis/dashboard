from __future__ import annotations

import json
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from time import monotonic
from typing import Any

from core.contracts.storage import PluginStorageConfig, StorageLimits, StorageTableSpec
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .errors import StorageLimitExceeded, StorageQueryNotAllowed, StorageRateLimited
from .models import PluginIndexRow, PluginKvRow, PluginRow


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except TypeError as exc:
        raise StorageQueryNotAllowed("Value must be JSON serializable") from exc


def _as_bytes(serialized: str) -> int:
    return len(serialized.encode("utf-8"))


def _is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, str | int | float | bool)


def _encode_index_value(value: Any) -> str:
    if not _is_scalar(value):
        raise StorageQueryNotAllowed("Indexed fields support only scalar equality values")
    return _canonical_json(value)


def _encode_pk(value: Any) -> str:
    if value is None or not _is_scalar(value):
        raise StorageQueryNotAllowed("Primary key must be a non-null scalar value")
    return _canonical_json(value)


@dataclass
class _TokenBucket:
    tokens: float
    updated_at: float


class _RateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[tuple[str, str], _TokenBucket] = {}
        self._lock = threading.Lock()

    def consume(self, *, plugin_id: str, op: str, qps: float) -> None:
        key = (plugin_id, op)
        now = monotonic()
        capacity = max(1.0, qps)
        refill_rate = qps

        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                self._buckets[key] = _TokenBucket(tokens=capacity - 1.0, updated_at=now)
                return

            elapsed = max(0.0, now - bucket.updated_at)
            bucket.tokens = min(capacity, bucket.tokens + elapsed * refill_rate)
            bucket.updated_at = now

            if bucket.tokens < 1.0:
                raise StorageRateLimited(
                    f"Rate limit exceeded for plugin '{plugin_id}' operation '{op}' (max_qps={qps})"
                )

            bucket.tokens -= 1.0


class UniversalStorage:
    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        plugin_configs: Mapping[str, PluginStorageConfig],
    ) -> None:
        self._session_factory = session_factory
        self._plugin_configs = dict(plugin_configs)
        self._tables: dict[str, dict[str, StorageTableSpec]] = {
            plugin_id: {table.name: table for table in config.tables}
            for plugin_id, config in self._plugin_configs.items()
        }
        self._rate_limiter = _RateLimiter()

    async def kv_get(self, *, plugin_id: str, key: str, secret: bool = False) -> Any | None:
        limits = self._limits_for(plugin_id)
        self._enforce_rate_limit(plugin_id=plugin_id, op="kv.get", limits=limits)

        async with self._session_factory() as session:
            row = await session.scalar(
                select(PluginKvRow).where(
                    PluginKvRow.plugin_id == plugin_id,
                    PluginKvRow.key == key,
                )
            )
            if row is None:
                return None
            if row.is_secret and not secret:
                raise StorageQueryNotAllowed("Secret key access requires secret=true")
            return json.loads(row.value)

    async def kv_set(self, *, plugin_id: str, key: str, value: Any, secret: bool = False) -> None:
        limits = self._limits_for(plugin_id)
        self._enforce_rate_limit(plugin_id=plugin_id, op="kv.set", limits=limits)

        serialized = _canonical_json(value)
        value_bytes = _as_bytes(serialized)
        if value_bytes > limits.max_kv_bytes:
            raise StorageLimitExceeded(
                f"KV value exceeds max_kv_bytes ({value_bytes}>{limits.max_kv_bytes})"
            )

        now = _utc_now()
        async with self._session_factory() as session, session.begin():
            row = await session.scalar(
                select(PluginKvRow).where(
                    PluginKvRow.plugin_id == plugin_id,
                    PluginKvRow.key == key,
                )
            )
            if row is None:
                session.add(
                    PluginKvRow(
                        plugin_id=plugin_id,
                        key=key,
                        value=serialized,
                        is_secret=bool(secret),
                        updated_at=now,
                        value_bytes=value_bytes,
                    )
                )
            else:
                row.value = serialized
                row.is_secret = bool(secret)
                row.value_bytes = value_bytes
                row.updated_at = now

    async def kv_delete(self, *, plugin_id: str, key: str) -> bool:
        limits = self._limits_for(plugin_id)
        self._enforce_rate_limit(plugin_id=plugin_id, op="kv.delete", limits=limits)

        async with self._session_factory() as session, session.begin():
            row = await session.scalar(
                select(PluginKvRow).where(
                    PluginKvRow.plugin_id == plugin_id,
                    PluginKvRow.key == key,
                )
            )
            if row is None:
                return False
            await session.delete(row)
            return True

    async def table_get(self, *, plugin_id: str, table: str, pk: Any) -> dict[str, Any] | None:
        limits = self._limits_for(plugin_id)
        self._enforce_rate_limit(plugin_id=plugin_id, op="table.get", limits=limits)
        _ = self._table_spec(plugin_id=plugin_id, table=table)

        encoded_pk = _encode_pk(pk)

        async with self._session_factory() as session:
            row = await session.scalar(
                select(PluginRow).where(
                    PluginRow.plugin_id == plugin_id,
                    PluginRow.table_name == table,
                    PluginRow.pk == encoded_pk,
                )
            )
            if row is None:
                return None
            payload = json.loads(row.row_json)
            if not isinstance(payload, dict):
                raise StorageQueryNotAllowed("Stored row payload is invalid")
            return payload

    async def table_upsert(self, *, plugin_id: str, table: str, row: Mapping[str, Any]) -> dict[str, Any]:
        return await self._table_upsert_impl(
            plugin_id=plugin_id,
            table=table,
            row=row,
            enforce_rate_limit=True,
        )

    async def migration_table_upsert(self, *, plugin_id: str, table: str, row: Mapping[str, Any]) -> dict[str, Any]:
        return await self._table_upsert_impl(
            plugin_id=plugin_id,
            table=table,
            row=row,
            enforce_rate_limit=False,
        )

    async def _table_upsert_impl(
        self,
        *,
        plugin_id: str,
        table: str,
        row: Mapping[str, Any],
        enforce_rate_limit: bool,
    ) -> dict[str, Any]:
        limits = self._limits_for(plugin_id)
        if enforce_rate_limit:
            self._enforce_rate_limit(plugin_id=plugin_id, op="table.upsert", limits=limits)

        table_spec = self._table_spec(plugin_id=plugin_id, table=table)
        payload = dict(row)

        if table_spec.primary_key not in payload:
            raise StorageQueryNotAllowed(
                f"Table '{table}' row must include primary key field '{table_spec.primary_key}'"
            )

        encoded_pk = _encode_pk(payload[table_spec.primary_key])
        serialized = _canonical_json(payload)
        row_bytes = _as_bytes(serialized)
        if row_bytes > limits.max_row_bytes:
            raise StorageLimitExceeded(
                f"Row exceeds max_row_bytes ({row_bytes}>{limits.max_row_bytes})"
            )

        now = _utc_now()
        async with self._session_factory() as session, session.begin():
            await self._ensure_table_count_limit(session=session, plugin_id=plugin_id, table=table, limits=limits)

            existing = await session.scalar(
                select(PluginRow).where(
                    PluginRow.plugin_id == plugin_id,
                    PluginRow.table_name == table,
                    PluginRow.pk == encoded_pk,
                )
            )

            if existing is None:
                rows_count = int(
                    await session.scalar(
                        select(func.count()).where(
                            PluginRow.plugin_id == plugin_id,
                            PluginRow.table_name == table,
                        )
                    )
                    or 0
                )
                if rows_count >= limits.max_rows_per_table:
                    raise StorageLimitExceeded(
                        f"Rows per table exceeded for '{table}' ({rows_count}>={limits.max_rows_per_table})"
                    )
                session.add(
                    PluginRow(
                        plugin_id=plugin_id,
                        table_name=table,
                        pk=encoded_pk,
                        row_json=serialized,
                        updated_at=now,
                        row_bytes=row_bytes,
                    )
                )
            else:
                existing.row_json = serialized
                existing.updated_at = now
                existing.row_bytes = row_bytes

            await session.execute(
                delete(PluginIndexRow).where(
                    PluginIndexRow.plugin_id == plugin_id,
                    PluginIndexRow.table_name == table,
                    PluginIndexRow.pk == encoded_pk,
                )
            )

            for field in table_spec.indexes:
                if field not in payload:
                    continue
                value = payload[field]
                if value is None:
                    continue
                session.add(
                    PluginIndexRow(
                        plugin_id=plugin_id,
                        table_name=table,
                        index_name=field,
                        index_value=_encode_index_value(value),
                        pk=encoded_pk,
                        updated_at=now,
                    )
                )

        return payload

    async def table_delete(self, *, plugin_id: str, table: str, pk: Any) -> bool:
        limits = self._limits_for(plugin_id)
        self._enforce_rate_limit(plugin_id=plugin_id, op="table.delete", limits=limits)
        _ = self._table_spec(plugin_id=plugin_id, table=table)

        encoded_pk = _encode_pk(pk)
        async with self._session_factory() as session, session.begin():
            row = await session.scalar(
                select(PluginRow).where(
                    PluginRow.plugin_id == plugin_id,
                    PluginRow.table_name == table,
                    PluginRow.pk == encoded_pk,
                )
            )
            if row is None:
                return False

            await session.execute(
                delete(PluginIndexRow).where(
                    PluginIndexRow.plugin_id == plugin_id,
                    PluginIndexRow.table_name == table,
                    PluginIndexRow.pk == encoded_pk,
                )
            )
            await session.delete(row)
            return True

    async def table_query(
        self,
        *,
        plugin_id: str,
        table: str,
        where: Mapping[str, Any],
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        limits = self._limits_for(plugin_id)
        self._enforce_rate_limit(plugin_id=plugin_id, op="table.query", limits=limits)

        table_spec = self._table_spec(plugin_id=plugin_id, table=table)
        predicates = dict(where)
        if not predicates:
            raise StorageQueryNotAllowed("table_query requires non-empty where")

        allowed_fields = {table_spec.primary_key, *table_spec.indexes}
        for field, value in predicates.items():
            if field not in allowed_fields:
                raise StorageQueryNotAllowed(
                    f"Field '{field}' is not queryable for table '{table}'"
                )
            if not _is_scalar(value):
                raise StorageQueryNotAllowed("table_query supports equality AND on scalar values only")

        clamped_limit = self._clamp_query_limit(limit=limit, limits=limits)

        async with self._session_factory() as session:
            candidate_sets: list[set[str]] = []

            for field, value in predicates.items():
                if field == table_spec.primary_key:
                    candidate_sets.append({_encode_pk(value)})
                    continue

                pks = set(
                    (await session.scalars(
                        select(PluginIndexRow.pk).where(
                            PluginIndexRow.plugin_id == plugin_id,
                            PluginIndexRow.table_name == table,
                            PluginIndexRow.index_name == field,
                            PluginIndexRow.index_value == _encode_index_value(value),
                        )
                    )).all()
                )
                candidate_sets.append(pks)

            if not candidate_sets:
                raise StorageQueryNotAllowed("table_query requires at least one predicate")

            candidate_pks = set.intersection(*candidate_sets) if candidate_sets else set()
            if not candidate_pks:
                return []

            rows = (await session.scalars(
                select(PluginRow)
                .where(
                    PluginRow.plugin_id == plugin_id,
                    PluginRow.table_name == table,
                    PluginRow.pk.in_(candidate_pks),
                )
                .order_by(PluginRow.pk)
                .limit(clamped_limit)
            )).all()

            results: list[dict[str, Any]] = []
            for row in rows:
                payload = json.loads(row.row_json)
                if isinstance(payload, dict):
                    results.append(payload)
            return results

    async def count_table_rows(self, *, plugin_id: str, table: str) -> int:
        _ = self._table_spec(plugin_id=plugin_id, table=table)
        async with self._session_factory() as session:
            return int(
                await session.scalar(
                    select(func.count()).where(
                        PluginRow.plugin_id == plugin_id,
                        PluginRow.table_name == table,
                    )
                )
                or 0
            )

    async def read_rows_batch(
        self,
        *,
        plugin_id: str,
        table: str,
        batch_size: int,
        after_pk: str | None = None,
    ) -> list[tuple[str, dict[str, Any]]]:
        _ = self._table_spec(plugin_id=plugin_id, table=table)
        limit = max(1, batch_size)

        statement = (
            select(PluginRow.pk, PluginRow.row_json)
            .where(
                PluginRow.plugin_id == plugin_id,
                PluginRow.table_name == table,
            )
            .order_by(PluginRow.pk)
            .limit(limit)
        )
        if after_pk is not None:
            statement = statement.where(PluginRow.pk > after_pk)

        async with self._session_factory() as session:
            rows = (await session.execute(statement)).all()

        result: list[tuple[str, dict[str, Any]]] = []
        for pk, row_json in rows:
            payload = json.loads(str(row_json))
            if isinstance(payload, dict):
                result.append((str(pk), payload))
        return result

    def _limits_for(self, plugin_id: str) -> StorageLimits:
        config = self._plugin_configs.get(plugin_id)
        if config is None:
            raise StorageQueryNotAllowed(f"Storage config for plugin '{plugin_id}' is not defined")
        return config.limits

    def _table_spec(self, *, plugin_id: str, table: str) -> StorageTableSpec:
        plugin_tables = self._tables.get(plugin_id)
        if plugin_tables is None:
            raise StorageQueryNotAllowed(f"Storage config for plugin '{plugin_id}' is not defined")
        table_spec = plugin_tables.get(table)
        if table_spec is None:
            raise StorageQueryNotAllowed(f"Table '{table}' is not allowed for plugin '{plugin_id}'")
        return table_spec

    def _clamp_query_limit(self, *, limit: int | None, limits: StorageLimits) -> int:
        if limit is None:
            return limits.max_query_limit
        return max(1, min(limit, limits.max_query_limit))

    def _enforce_rate_limit(self, *, plugin_id: str, op: str, limits: StorageLimits) -> None:
        self._rate_limiter.consume(plugin_id=plugin_id, op=op, qps=limits.max_qps)

    async def _ensure_table_count_limit(
        self,
        *,
        session: AsyncSession,
        plugin_id: str,
        table: str,
        limits: StorageLimits,
    ) -> None:
        table_count = int(
            await session.scalar(
                select(func.count(func.distinct(PluginRow.table_name))).where(
                    PluginRow.plugin_id == plugin_id,
                )
            )
            or 0
        )
        table_exists = await session.scalar(
            select(PluginRow.table_name)
            .where(
                PluginRow.plugin_id == plugin_id,
                PluginRow.table_name == table,
            )
            .limit(1)
        )
        if table_exists is None and table_count >= limits.max_tables:
            raise StorageLimitExceeded(
                f"Table count exceeded for plugin '{plugin_id}' ({table_count}>={limits.max_tables})"
            )


__all__ = ["UniversalStorage"]
