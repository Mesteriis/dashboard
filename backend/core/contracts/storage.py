from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator


class StorageLimits(BaseModel):
    max_tables: int = Field(default=32, ge=1, le=10_000)
    max_rows_per_table: int = Field(default=50_000, ge=1, le=10_000_000)
    max_row_bytes: int = Field(default=32_768, ge=32, le=10_000_000)
    max_kv_bytes: int = Field(default=16_384, ge=32, le=10_000_000)
    max_qps: float = Field(default=50.0, gt=0, le=100_000)
    max_query_limit: int = Field(default=200, ge=1, le=10_000)


class StorageTableSpec(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    primary_key: str = Field(min_length=1, max_length=128)
    indexes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _normalize(self) -> StorageTableSpec:
        normalized_indexes: list[str] = []
        for field in self.indexes:
            field_name = field.strip()
            if not field_name:
                continue
            if field_name == self.primary_key:
                continue
            if field_name not in normalized_indexes:
                normalized_indexes.append(field_name)
        self.indexes = normalized_indexes
        return self


StorageColumnType = Literal["string", "integer", "number", "boolean", "json", "datetime"]


class StorageDDLColumnSpec(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    type: StorageColumnType
    nullable: bool = True


class StorageDDLIndexSpec(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    columns: list[str] = Field(min_length=1)
    unique: bool = False

    @model_validator(mode="after")
    def _normalize(self) -> StorageDDLIndexSpec:
        normalized_columns: list[str] = []
        for field in self.columns:
            field_name = field.strip()
            if not field_name:
                continue
            if field_name not in normalized_columns:
                normalized_columns.append(field_name)
        if not normalized_columns:
            raise ValueError(f"Storage index '{self.name}' must define at least one column")
        self.columns = normalized_columns
        return self


class StorageDDLTableSpec(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    primary_key: str = Field(min_length=1, max_length=128)
    columns: list[StorageDDLColumnSpec] = Field(min_length=1)
    indexes: list[StorageDDLIndexSpec] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_columns(self) -> StorageDDLTableSpec:
        column_names: set[str] = set()
        for column in self.columns:
            if column.name in column_names:
                raise ValueError(f"Duplicate DDL column '{column.name}' in table '{self.name}'")
            column_names.add(column.name)

        if self.primary_key not in column_names:
            raise ValueError(f"DDL table '{self.name}' primary key '{self.primary_key}' is missing in columns")

        for index in self.indexes:
            for field in index.columns:
                if field not in column_names:
                    raise ValueError(
                        f"DDL index '{index.name}' references unknown field '{field}' in table '{self.name}'"
                    )
        return self


class StorageDDLSpec(BaseModel):
    version: int = Field(ge=1)
    tables: list[StorageDDLTableSpec] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_tables(self) -> StorageDDLSpec:
        names: set[str] = set()
        for table in self.tables:
            if table.name in names:
                raise ValueError(f"Duplicate DDL table spec: {table.name}")
            names.add(table.name)
        return self


class PluginStorageConfig(BaseModel):
    mode: Literal["core_universal", "core_physical_tables"] = "core_universal"
    ddl: StorageDDLSpec | None = None
    limits: StorageLimits = Field(default_factory=StorageLimits)
    tables: list[StorageTableSpec] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_tables(self) -> PluginStorageConfig:
        table_names: set[str] = set()
        for table in self.tables:
            if table.name in table_names:
                raise ValueError(f"Duplicate storage table spec: {table.name}")
            table_names.add(table.name)

        if len(table_names) > self.limits.max_tables:
            raise ValueError("Configured storage tables exceed max_tables limit")

        if self.mode == "core_physical_tables":
            if self.ddl is None:
                raise ValueError("Storage DDL spec is required for core_physical_tables mode")
            ddl_tables = {table.name: table for table in self.ddl.tables}
            for table in self.tables:
                ddl_table = ddl_tables.get(table.name)
                if ddl_table is None:
                    raise ValueError(
                        f"Storage table '{table.name}' is not present in DDL tables for core_physical_tables mode"
                    )
                if ddl_table.primary_key != table.primary_key:
                    raise ValueError(f"Storage table '{table.name}' primary key mismatch between tables and ddl specs")
                ddl_index_columns = {column_name for index in ddl_table.indexes for column_name in index.columns}
                for index_name in table.indexes:
                    if index_name not in ddl_index_columns:
                        raise ValueError(
                            f"Storage table '{table.name}' index '{index_name}' must be declared in DDL indexes"
                        )
        elif self.ddl is not None:
            raise ValueError("DDL spec is allowed only for core_physical_tables mode")
        return self


StorageRpcOperation = Literal[
    "kv.get",
    "kv.set",
    "kv.delete",
    "table.get",
    "table.upsert",
    "table.delete",
    "table.query",
]


class StorageRpcRequest(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    ts: datetime = Field(default_factory=lambda: datetime.now(UTC))
    plugin_id: str = Field(min_length=1, max_length=128)
    op: StorageRpcOperation
    table: str | None = Field(default=None, min_length=1, max_length=128)
    key: Any | None = None
    where: dict[str, Any] | None = None
    limit: int | None = Field(default=None, ge=1)
    row: dict[str, Any] | None = None
    secret: bool | None = None


class StorageRpcResponse(BaseModel):
    id: UUID
    ok: bool
    error: dict[str, Any] | None = None
    result: dict[str, Any] | None = None


__all__ = [
    "PluginStorageConfig",
    "StorageColumnType",
    "StorageDDLColumnSpec",
    "StorageDDLIndexSpec",
    "StorageDDLSpec",
    "StorageDDLTableSpec",
    "StorageLimits",
    "StorageRpcOperation",
    "StorageRpcRequest",
    "StorageRpcResponse",
    "StorageTableSpec",
]
