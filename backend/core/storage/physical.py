from __future__ import annotations

import asyncio
import json
import re
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from time import monotonic
from typing import Any

from core.contracts.storage import (
    PluginStorageConfig,
    StorageDDLColumnSpec,
    StorageDDLSpec,
    StorageDDLTableSpec,
    StorageLimits,
    StorageTableSpec,
)
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    MetaData,
    Table,
    Text,
    and_,
    delete,
    func,
    insert,
    inspect,
    select,
    text,
    update,
)
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.schema import CreateColumn

from .errors import (
    StorageDdlNotAllowed,
    StorageLimitExceeded,
    StorageQueryNotAllowed,
    StorageRateLimited,
)
from .models import PluginKvRow

_IDENTIFIER_RE = re.compile(r"[^a-z0-9_]+")
_UNDERSCORE_RE = re.compile(r"_+")


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _as_bytes(serialized: str) -> int:
    return len(serialized.encode("utf-8"))


def _is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, str | int | float | bool)


def sanitize_identifier(value: str, *, max_length: int = 48) -> str:
    normalized = value.strip().lower().replace("-", "_").replace(".", "_")
    normalized = _IDENTIFIER_RE.sub("_", normalized)
    normalized = _UNDERSCORE_RE.sub("_", normalized).strip("_")
    if not normalized:
        raise StorageDdlNotAllowed("Identifier cannot be empty after sanitization")
    if normalized[0].isdigit():
        normalized = f"p_{normalized}"
    return normalized[:max_length]


def physical_table_name(plugin_id: str, logical_table: str) -> str:
    plugin_safe = sanitize_identifier(plugin_id, max_length=40)
    table_safe = sanitize_identifier(logical_table, max_length=40)
    return f"plg__{plugin_safe}__{table_safe}"


def physical_index_name(*, physical_table: str, logical_index_name: str) -> str:
    base = f"ix__{physical_table}__{logical_index_name}"
    return sanitize_identifier(base, max_length=120)


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

        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                self._buckets[key] = _TokenBucket(tokens=capacity - 1.0, updated_at=now)
                return

            elapsed = max(0.0, now - bucket.updated_at)
            bucket.tokens = min(capacity, bucket.tokens + elapsed * qps)
            bucket.updated_at = now

            if bucket.tokens < 1.0:
                raise StorageRateLimited(
                    f"Rate limit exceeded for plugin '{plugin_id}' operation '{op}' (max_qps={qps})"
                )
            bucket.tokens -= 1.0


class SafeDdlEngine:
    def __init__(
        self,
        *,
        engine: AsyncEngine,
        plugin_configs: Mapping[str, PluginStorageConfig],
    ) -> None:
        self._engine = engine
        self._plugin_configs = {
            plugin_id: config
            for plugin_id, config in plugin_configs.items()
            if config.mode == "core_physical_tables"
        }
        self._lock = asyncio.Lock()

    async def install_all(self) -> None:
        for plugin_id in sorted(self._plugin_configs):
            await self.install_or_upgrade(plugin_id=plugin_id)

    async def install_or_upgrade(self, *, plugin_id: str) -> None:
        config = self._plugin_configs.get(plugin_id)
        if config is None or config.ddl is None:
            raise StorageDdlNotAllowed(f"Plugin '{plugin_id}' is not configured for core_physical_tables mode")

        async with self._lock, self._engine.begin() as connection:
            await connection.run_sync(
                self._install_or_upgrade_on_connection,
                plugin_id,
                config,
            )

    def _install_or_upgrade_on_connection(
        self,
        connection: Any,
        plugin_id: str,
        config: PluginStorageConfig,
    ) -> None:
        ddl = config.ddl
        if ddl is None:
            raise StorageDdlNotAllowed(f"Plugin '{plugin_id}' DDL spec is missing")

        table_specs = {table.name: table for table in config.tables}
        if len(table_specs) > config.limits.max_tables:
            raise StorageDdlNotAllowed(
                "Plugin "
                f"'{plugin_id}' table specs exceed max_tables limit "
                f"({len(table_specs)}>{config.limits.max_tables})"
            )

        inspector = inspect(connection)
        existing_tables = set(inspector.get_table_names())

        for ddl_table in ddl.tables:
            logical_table = ddl_table.name
            if logical_table not in table_specs:
                continue

            physical_table = physical_table_name(plugin_id, logical_table)
            if physical_table not in existing_tables:
                self._create_table(
                    connection=connection,
                    physical_table=physical_table,
                    ddl_table=ddl_table,
                )
                existing_tables.add(physical_table)
                continue

            self._upgrade_table(
                connection=connection,
                physical_table=physical_table,
                ddl_table=ddl_table,
            )

    def _create_table(
        self,
        *,
        connection: Any,
        physical_table: str,
        ddl_table: StorageDDLTableSpec,
    ) -> None:
        metadata = MetaData()
        columns = [
            self._build_column(column, primary_key=column.name == ddl_table.primary_key)
            for column in ddl_table.columns
        ]
        table = Table(physical_table, metadata, *columns)
        metadata.create_all(bind=connection, tables=[table])
        self._create_missing_indexes(connection=connection, physical_table=physical_table, ddl_table=ddl_table)

    def _upgrade_table(self, *, connection: Any, physical_table: str, ddl_table: StorageDDLTableSpec) -> None:
        inspector = inspect(connection)
        existing_columns = {column["name"]: column for column in inspector.get_columns(physical_table)}
        desired_columns = {column.name: column for column in ddl_table.columns}

        missing_from_spec = sorted(set(existing_columns) - set(desired_columns))
        if missing_from_spec:
            raise StorageDdlNotAllowed(
                f"Destructive DDL change for table '{physical_table}' is not allowed; "
                f"existing columns missing in spec: {', '.join(missing_from_spec)}"
            )

        for column_name, column_spec in desired_columns.items():
            if column_name not in existing_columns:
                if column_name == ddl_table.primary_key:
                    raise StorageDdlNotAllowed(
                        f"Adding primary key column '{column_name}' to existing table '{physical_table}' is not allowed"
                    )
                self._add_column(connection=connection, physical_table=physical_table, column=column_spec)

        self._create_missing_indexes(connection=connection, physical_table=physical_table, ddl_table=ddl_table)

    def _create_missing_indexes(
        self,
        *,
        connection: Any,
        physical_table: str,
        ddl_table: StorageDDLTableSpec,
    ) -> None:
        inspector = inspect(connection)
        existing_indexes = {index["name"] for index in inspector.get_indexes(physical_table)}
        table = Table(physical_table, MetaData(), autoload_with=connection)

        for index_spec in ddl_table.indexes:
            index_name = physical_index_name(physical_table=physical_table, logical_index_name=index_spec.name)
            if index_name in existing_indexes:
                continue
            columns = [table.c[column_name] for column_name in index_spec.columns]
            Index(index_name, *columns, unique=index_spec.unique).create(bind=connection)

    def _add_column(self, *, connection: Any, physical_table: str, column: StorageDDLColumnSpec) -> None:
        ddl_column = self._build_column(column, primary_key=False)
        compiled_column = str(CreateColumn(ddl_column).compile(dialect=connection.dialect))
        sql = text(f"ALTER TABLE {self._quote_identifier(physical_table)} ADD COLUMN {compiled_column}")
        connection.execute(sql)

    def _build_column(self, column: StorageDDLColumnSpec, *, primary_key: bool) -> Column[Any]:
        return Column(
            column.name,
            self._column_type(column),
            nullable=False if primary_key else bool(column.nullable),
            primary_key=primary_key,
        )

    @staticmethod
    def _quote_identifier(name: str) -> str:
        escaped = name.replace('"', '""')
        return f'"{escaped}"'

    @staticmethod
    def _column_type(column: StorageDDLColumnSpec) -> Any:
        if column.type == "string":
            return Text()
        if column.type == "integer":
            return Integer()
        if column.type == "number":
            return Float()
        if column.type == "boolean":
            return Boolean()
        if column.type == "json":
            return Text()
        if column.type == "datetime":
            return DateTime(timezone=True)
        raise StorageDdlNotAllowed(f"Unsupported DDL column type '{column.type}'")


class PhysicalStorage:
    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        plugin_configs: Mapping[str, PluginStorageConfig],
    ) -> None:
        self._session_factory = session_factory
        engine = session_factory.kw.get("bind")
        if not isinstance(engine, AsyncEngine):
            raise RuntimeError("Session factory must be bound to SQLAlchemy AsyncEngine")
        self._engine = engine

        self._plugin_configs = {
            plugin_id: config
            for plugin_id, config in plugin_configs.items()
            if config.mode == "core_physical_tables"
        }
        self._table_specs: dict[str, dict[str, StorageTableSpec]] = {
            plugin_id: {table.name: table for table in config.tables}
            for plugin_id, config in self._plugin_configs.items()
        }
        self._ddl_tables: dict[str, dict[str, StorageDDLTableSpec]] = {
            plugin_id: self._ddl_table_map(config.ddl)
            for plugin_id, config in self._plugin_configs.items()
        }

        self._ddl_engine = SafeDdlEngine(engine=self._engine, plugin_configs=self._plugin_configs)
        self._migrated_plugins: set[str] = set()
        self._migrate_lock = threading.Lock()
        self._table_cache: dict[tuple[str, str], Table] = {}
        self._rate_limiter = _RateLimiter()

    async def install_all(self) -> None:
        await self._ddl_engine.install_all()
        with self._migrate_lock:
            self._migrated_plugins = set(self._plugin_configs)
            self._table_cache = {}

    async def ensure_plugin_ready(self, plugin_id: str) -> None:
        _ = self._limits_for(plugin_id)
        await self._ensure_plugin_migrated(plugin_id)

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

        table_obj, table_spec, ddl_table = await self._resolve_table(plugin_id=plugin_id, table=table)
        pk_value = self._serialize_column_value(ddl_table.columns_map[table_spec.primary_key], pk, for_query=True)

        async with self._session_factory() as session:
            row = (await session.execute(
                select(table_obj).where(table_obj.c[table_spec.primary_key] == pk_value).limit(1)
            )).mappings().first()
            if row is None:
                return None
            return self._decode_row(ddl_table=ddl_table, row=dict(row))

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

        table_obj, table_spec, ddl_table = await self._resolve_table(plugin_id=plugin_id, table=table)
        payload = self._normalize_payload(ddl_table=ddl_table, payload=dict(row), require_all_required=True)

        if table_spec.primary_key not in payload:
            raise StorageQueryNotAllowed(
                f"Table '{table}' row must include primary key field '{table_spec.primary_key}'"
            )

        row_bytes = _as_bytes(_canonical_json(self._decode_row(ddl_table=ddl_table, row=dict(payload))))
        if row_bytes > limits.max_row_bytes:
            raise StorageLimitExceeded(
                f"Row exceeds max_row_bytes ({row_bytes}>{limits.max_row_bytes})"
            )

        pk_field = table_spec.primary_key
        pk_value = payload[pk_field]

        async with self._session_factory() as session, session.begin():
            exists = (await session.execute(
                select(table_obj.c[pk_field]).where(table_obj.c[pk_field] == pk_value).limit(1)
            )).scalar_one_or_none()

            if exists is None:
                rows_count = int((await session.execute(select(func.count()).select_from(table_obj))).scalar_one() or 0)
                if rows_count >= limits.max_rows_per_table:
                    raise StorageLimitExceeded(
                        f"Rows per table exceeded for '{table}' ({rows_count}>={limits.max_rows_per_table})"
                    )
                await session.execute(insert(table_obj).values(**payload))
            else:
                await session.execute(
                    update(table_obj)
                    .where(table_obj.c[pk_field] == pk_value)
                    .values(**payload)
                )

        return self._decode_row(ddl_table=ddl_table, row=dict(payload))

    async def table_delete(self, *, plugin_id: str, table: str, pk: Any) -> bool:
        limits = self._limits_for(plugin_id)
        self._enforce_rate_limit(plugin_id=plugin_id, op="table.delete", limits=limits)

        table_obj, table_spec, ddl_table = await self._resolve_table(plugin_id=plugin_id, table=table)
        pk_value = self._serialize_column_value(ddl_table.columns_map[table_spec.primary_key], pk, for_query=True)

        async with self._session_factory() as session, session.begin():
            deleted = (await session.execute(
                delete(table_obj).where(table_obj.c[table_spec.primary_key] == pk_value)
            )).rowcount
            return bool(deleted)

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

        table_obj, table_spec, ddl_table = await self._resolve_table(plugin_id=plugin_id, table=table)
        predicates = dict(where)
        if not predicates:
            raise StorageQueryNotAllowed("table_query requires non-empty where")

        allowed_fields = {table_spec.primary_key, *table_spec.indexes}
        conditions = []
        for field, value in predicates.items():
            if field not in allowed_fields:
                raise StorageQueryNotAllowed(
                    f"Field '{field}' is not queryable for table '{table}'"
                )
            if not _is_scalar(value):
                raise StorageQueryNotAllowed("table_query supports equality AND on scalar values only")
            column_spec = ddl_table.columns_map.get(field)
            if column_spec is None:
                raise StorageQueryNotAllowed(f"Field '{field}' is missing in DDL for table '{table}'")
            encoded = self._serialize_column_value(column_spec, value, for_query=True)
            conditions.append(table_obj.c[field] == encoded)

        clamped_limit = self._clamp_query_limit(limit=limit, limits=limits)
        statement = (
            select(table_obj)
            .where(and_(*conditions))
            .order_by(table_obj.c[table_spec.primary_key])
            .limit(clamped_limit)
        )

        async with self._session_factory() as session:
            rows = (await session.execute(statement)).mappings().all()
            return [self._decode_row(ddl_table=ddl_table, row=dict(row)) for row in rows]

    async def count_table_rows(self, *, plugin_id: str, table: str) -> int:
        table_obj, _, _ = await self._resolve_table(plugin_id=plugin_id, table=table)
        async with self._session_factory() as session:
            return int((await session.execute(select(func.count()).select_from(table_obj))).scalar_one() or 0)

    async def read_rows_batch(
        self,
        *,
        plugin_id: str,
        table: str,
        batch_size: int,
        after_pk: Any | None = None,
    ) -> list[tuple[Any, dict[str, Any]]]:
        table_obj, table_spec, ddl_table = await self._resolve_table(plugin_id=plugin_id, table=table)
        pk_field = table_spec.primary_key
        pk_column = table_obj.c[pk_field]
        pk_spec = ddl_table.columns_map[pk_field]

        statement = select(table_obj).order_by(pk_column).limit(max(1, batch_size))
        if after_pk is not None:
            encoded_pk = self._serialize_column_value(pk_spec, after_pk, for_query=True)
            statement = statement.where(pk_column > encoded_pk)

        async with self._session_factory() as session:
            rows = (await session.execute(statement)).mappings().all()

        result: list[tuple[Any, dict[str, Any]]] = []
        for raw_row in rows:
            row_dict = dict(raw_row)
            decoded = self._decode_row(ddl_table=ddl_table, row=row_dict)
            result.append((decoded[pk_field], decoded))
        return result

    async def _resolve_table(
        self,
        *,
        plugin_id: str,
        table: str,
    ) -> tuple[Table, StorageTableSpec, _PhysicalTableSpec]:
        table_spec = self._table_spec(plugin_id=plugin_id, table=table)
        ddl_table = self._ddl_table(plugin_id=plugin_id, table=table)
        await self._ensure_plugin_migrated(plugin_id)

        cache_key = (plugin_id, table)
        table_obj = self._table_cache.get(cache_key)
        if table_obj is None:
            table_obj = self._materialize_table(plugin_id=plugin_id, ddl_table=ddl_table)
            self._table_cache[cache_key] = table_obj
        return table_obj, table_spec, ddl_table

    def _table_spec(self, *, plugin_id: str, table: str) -> StorageTableSpec:
        plugin_tables = self._table_specs.get(plugin_id)
        if plugin_tables is None:
            raise StorageQueryNotAllowed(f"Storage config for plugin '{plugin_id}' is not defined")
        table_spec = plugin_tables.get(table)
        if table_spec is None:
            raise StorageQueryNotAllowed(f"Table '{table}' is not allowed for plugin '{plugin_id}'")
        return table_spec

    def _ddl_table(self, *, plugin_id: str, table: str) -> _PhysicalTableSpec:
        plugin_tables = self._ddl_tables.get(plugin_id)
        if plugin_tables is None:
            raise StorageQueryNotAllowed(f"Storage DDL for plugin '{plugin_id}' is not defined")
        ddl_table = plugin_tables.get(table)
        if ddl_table is None:
            raise StorageQueryNotAllowed(f"Table '{table}' DDL is missing for plugin '{plugin_id}'")
        return ddl_table

    async def _ensure_plugin_migrated(self, plugin_id: str) -> None:
        with self._migrate_lock:
            if plugin_id in self._migrated_plugins:
                return
        await self._ddl_engine.install_or_upgrade(plugin_id=plugin_id)
        with self._migrate_lock:
            self._migrated_plugins.add(plugin_id)
            self._table_cache = {
                cache_key: table
                for cache_key, table in self._table_cache.items()
                if cache_key[0] != plugin_id
            }

    def _materialize_table(self, *, plugin_id: str, ddl_table: _PhysicalTableSpec) -> Table:
        table_name = physical_table_name(plugin_id, ddl_table.name)
        columns = [
            Column(
                column.name,
                SafeDdlEngine._column_type(column),
                nullable=False if column.name == ddl_table.primary_key else bool(column.nullable),
                primary_key=column.name == ddl_table.primary_key,
            )
            for column in ddl_table.columns
        ]
        return Table(table_name, MetaData(), *columns)

    def _limits_for(self, plugin_id: str) -> StorageLimits:
        config = self._plugin_configs.get(plugin_id)
        if config is None:
            raise StorageQueryNotAllowed(f"Storage config for plugin '{plugin_id}' is not defined")
        return config.limits

    def _clamp_query_limit(self, *, limit: int | None, limits: StorageLimits) -> int:
        if limit is None:
            return limits.max_query_limit
        return max(1, min(limit, limits.max_query_limit))

    def _enforce_rate_limit(self, *, plugin_id: str, op: str, limits: StorageLimits) -> None:
        self._rate_limiter.consume(plugin_id=plugin_id, op=op, qps=limits.max_qps)

    def _normalize_payload(
        self,
        *,
        ddl_table: _PhysicalTableSpec,
        payload: dict[str, Any],
        require_all_required: bool,
    ) -> dict[str, Any]:
        normalized: dict[str, Any] = {}

        for field_name, value in payload.items():
            column_spec = ddl_table.columns_map.get(field_name)
            if column_spec is None:
                raise StorageQueryNotAllowed(
                    f"Field '{field_name}' is not declared in DDL table '{ddl_table.name}'"
                )
            normalized[field_name] = self._serialize_column_value(column_spec, value, for_query=False)

        if require_all_required:
            for column in ddl_table.columns:
                if column.name in normalized:
                    continue
                if not column.nullable:
                    raise StorageQueryNotAllowed(
                        f"Field '{column.name}' is required by DDL table '{ddl_table.name}'"
                    )

        return normalized

    def _serialize_column_value(self, column: StorageDDLColumnSpec, value: Any, *, for_query: bool) -> Any:
        if value is None:
            if not column.nullable:
                raise StorageQueryNotAllowed(f"Field '{column.name}' does not allow null")
            return None

        if column.type == "string":
            return str(value)

        if column.type == "datetime":
            if isinstance(value, datetime):
                if value.tzinfo is None:
                    return value.replace(tzinfo=UTC)
                return value.astimezone(UTC)
            if isinstance(value, str):
                normalized = value.strip()
                if normalized.endswith("Z"):
                    normalized = f"{normalized[:-1]}+00:00"
                try:
                    parsed = datetime.fromisoformat(normalized)
                except ValueError as exc:
                    raise StorageQueryNotAllowed(
                        f"Field '{column.name}' expects datetime (ISO-8601 string)"
                    ) from exc
                if parsed.tzinfo is None:
                    return parsed.replace(tzinfo=UTC)
                return parsed.astimezone(UTC)
            raise StorageQueryNotAllowed(f"Field '{column.name}' expects datetime")

        if column.type == "integer":
            if isinstance(value, bool):
                raise StorageQueryNotAllowed(f"Field '{column.name}' expects integer")
            if not isinstance(value, int):
                raise StorageQueryNotAllowed(f"Field '{column.name}' expects integer")
            return int(value)

        if column.type == "number":
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise StorageQueryNotAllowed(f"Field '{column.name}' expects number")
            return float(value)

        if column.type == "boolean":
            if not isinstance(value, bool):
                raise StorageQueryNotAllowed(f"Field '{column.name}' expects boolean")
            return bool(value)

        if column.type == "json":
            if for_query and not _is_scalar(value):
                raise StorageQueryNotAllowed(f"Field '{column.name}' supports scalar equality only")
            try:
                return _canonical_json(value)
            except TypeError as exc:
                raise StorageQueryNotAllowed(f"Field '{column.name}' must be JSON serializable") from exc

        raise StorageQueryNotAllowed(f"Unsupported DDL type '{column.type}' for field '{column.name}'")

    @staticmethod
    def _decode_row(*, ddl_table: _PhysicalTableSpec, row: Mapping[str, Any]) -> dict[str, Any]:
        decoded: dict[str, Any] = {}
        for column in ddl_table.columns:
            value = row.get(column.name)
            decoded[column.name] = PhysicalStorage._decode_value(column=column, value=value)
        return decoded

    @staticmethod
    def _decode_value(*, column: StorageDDLColumnSpec, value: Any) -> Any:
        if value is None:
            return None

        if column.type == "json" and isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None

        if column.type == "boolean":
            return bool(value)

        if column.type == "integer":
            return int(value)

        if column.type == "number":
            return float(value)

        if column.type == "datetime" and isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=UTC).isoformat()
            return value.astimezone(UTC).isoformat()

        if column.type in {"string", "datetime"}:
            return str(value)

        return value

    @staticmethod
    def _ddl_table_map(ddl: StorageDDLSpec | None) -> dict[str, _PhysicalTableSpec]:
        if ddl is None:
            return {}
        return {
            table.name: _PhysicalTableSpec(
                name=table.name,
                primary_key=table.primary_key,
                columns=tuple(table.columns),
                columns_map={column.name: column for column in table.columns},
            )
            for table in ddl.tables
        }


@dataclass(frozen=True)
class _PhysicalTableSpec:
    name: str
    primary_key: str
    columns: tuple[StorageDDLColumnSpec, ...]
    columns_map: dict[str, StorageDDLColumnSpec]


__all__ = [
    "PhysicalStorage",
    "SafeDdlEngine",
    "physical_index_name",
    "physical_table_name",
    "sanitize_identifier",
]
