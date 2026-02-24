from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ConfigRevision(BaseModel):
    revision: int = Field(ge=1)
    parent_revision: int | None = Field(default=None, ge=1)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source: Literal["bootstrap", "import", "patch", "rollback", "api", "system"]
    payload: dict[str, Any]
    created_at: datetime
    created_by: str | None = None


class ActiveState(BaseModel):
    active_revision: int = Field(ge=1)
    state_seq: int = Field(ge=1)
    updated_at: datetime
    updated_by: str | None = None
    reason: str | None = None


class ConfigStateResponse(BaseModel):
    active_state: ActiveState
    revision: ConfigRevision


class ConfigImportRequest(BaseModel):
    format: Literal["yaml", "json", "toml"] = "yaml"
    payload: str = Field(min_length=1)
    source: Literal["bootstrap", "import", "api"] = "import"


class ConfigPatchRequest(BaseModel):
    patch: dict[str, Any]
    source: Literal["patch", "api"] = "patch"


class ConfigValidateRequest(BaseModel):
    format: Literal["yaml", "json", "toml"] = "yaml"
    payload: str = Field(min_length=1)


class ConfigValidationResponse(BaseModel):
    valid: bool
    issues: list[dict[str, str]] = Field(default_factory=list)
    config: dict[str, Any] | None = None


class ConfigRollbackRequest(BaseModel):
    revision: int = Field(ge=1)
    source: Literal["rollback", "api"] = "rollback"


class ActionEnvelope(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    type: str = Field(min_length=1)
    requested_by: str = Field(min_length=1)
    requested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    capability: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = False
    idempotency_key: str | None = None
    trace_id: str | None = None


class ActionStatus(BaseModel):
    id: UUID
    type: str
    capability: str
    requested_by: str
    requested_at: datetime
    status: Literal["queued", "validated", "running", "succeeded", "failed", "cancelled", "blocked"]
    dry_run: bool
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None


class ActionValidationResponse(BaseModel):
    action_id: UUID
    valid: bool
    status: Literal["validated", "blocked"]


class ActionExecutionResponse(BaseModel):
    action_id: UUID
    status: Literal["queued", "running", "succeeded", "failed", "blocked"]
    result: dict[str, Any] | None = None


class ActionRegistryEntry(BaseModel):
    type: str
    capability: str
    description: str
    dry_run_supported: bool = True


class WidgetRegistryEntry(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: str
    version: str
    json_schema: dict[str, Any] = Field(default_factory=dict, alias="schema", serialization_alias="schema")
    capabilities: list[str] = Field(default_factory=list)


class EventEnvelope(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    type: str = Field(min_length=1)
    event_version: int = Field(default=1, ge=1)
    revision: int = Field(ge=1)
    ts: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source: str = Field(min_length=1)
    correlation_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class AuditEvent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    ts: datetime = Field(default_factory=lambda: datetime.now(UTC))
    actor: str = Field(min_length=1)
    action_id: UUID | None = None
    capability: str = Field(min_length=1)
    resource: str | None = None
    decision: Literal["allow", "deny"]
    outcome: Literal["validated", "executed", "failed", "blocked"]
    reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


StorageMode = Literal["core_universal", "core_physical_tables"]
StorageMigrationStrategy = Literal["read_only_lock", "dual_write"]


class StorageMigrationActionPayload(BaseModel):
    plugin_id: str = Field(min_length=1, max_length=128)
    from_mode: StorageMode
    to_mode: StorageMode
    tables: list[str] = Field(min_length=1)
    dry_run: bool = False
    strategy: StorageMigrationStrategy = "read_only_lock"
    batch_size: int = Field(default=500, ge=1, le=10_000)

    @model_validator(mode="after")
    def _validate(self) -> StorageMigrationActionPayload:
        normalized_tables: list[str] = []
        for table in self.tables:
            table_name = table.strip()
            if not table_name:
                continue
            if table_name not in normalized_tables:
                normalized_tables.append(table_name)
        if not normalized_tables:
            raise ValueError("Storage migration requires at least one table")
        self.tables = normalized_tables

        if self.from_mode == self.to_mode:
            raise ValueError("Storage migration from_mode and to_mode must be different")
        return self


class StorageMigrationPlanEntry(BaseModel):
    table: str
    rows: int = Field(ge=0)


class StorageMigrationResult(BaseModel):
    plugin_id: str
    from_mode: StorageMode
    to_mode: StorageMode
    strategy: StorageMigrationStrategy
    dry_run: bool
    tables: list[str]
    plan: list[StorageMigrationPlanEntry] = Field(default_factory=list)
    copied_rows: dict[str, int] = Field(default_factory=dict)
    switched_tables: list[str] = Field(default_factory=list)
    status: Literal["planned", "completed"]


__all__ = [
    "ActionEnvelope",
    "ActionExecutionResponse",
    "ActionRegistryEntry",
    "ActionStatus",
    "ActionValidationResponse",
    "ActiveState",
    "AuditEvent",
    "ConfigImportRequest",
    "ConfigPatchRequest",
    "ConfigRevision",
    "ConfigRollbackRequest",
    "ConfigStateResponse",
    "ConfigValidateRequest",
    "ConfigValidationResponse",
    "EventEnvelope",
    "StorageMigrationActionPayload",
    "StorageMigrationPlanEntry",
    "StorageMigrationResult",
    "StorageMigrationStrategy",
    "StorageMode",
    "WidgetRegistryEntry",
]
