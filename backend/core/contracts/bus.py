from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

BusMessageType = Literal[
    "storage.kv.get",
    "storage.kv.set",
    "storage.kv.delete",
    "storage.table.get",
    "storage.table.upsert",
    "storage.table.delete",
    "storage.table.query",
    "action.execute",
    "event.publish",
    "health.check.request",
    "health.check.result",
]


class BusTraceV1(BaseModel):
    trace_id: str | None = None
    source: str | None = None
    idempotency_key: str | None = None


class BusMessageV1(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    ts: datetime = Field(default_factory=lambda: datetime.now(UTC))
    type: BusMessageType
    plugin_id: str = Field(min_length=1, max_length=128)
    payload: dict[str, Any] = Field(default_factory=dict)
    reply_to: str | None = None
    correlation_id: str | None = None
    trace: BusTraceV1 | None = None


class BusReplyV1(BaseModel):
    correlation_id: str
    ok: bool
    error: dict[str, Any] | None = None
    result: dict[str, Any] | None = None


class StorageKvGetPayload(BaseModel):
    key: str = Field(min_length=1, max_length=255)
    secret: bool = False


class StorageKvSetPayload(BaseModel):
    key: str = Field(min_length=1, max_length=255)
    value: Any
    secret: bool = False


class StorageKvDeletePayload(BaseModel):
    key: str = Field(min_length=1, max_length=255)


class StorageTableGetPayload(BaseModel):
    table: str = Field(min_length=1, max_length=128)
    key: Any


class StorageTableUpsertPayload(BaseModel):
    table: str = Field(min_length=1, max_length=128)
    row: dict[str, Any] = Field(default_factory=dict)


class StorageTableDeletePayload(BaseModel):
    table: str = Field(min_length=1, max_length=128)
    key: Any


class StorageTableQueryPayload(BaseModel):
    table: str = Field(min_length=1, max_length=128)
    where: dict[str, Any] = Field(default_factory=dict)
    limit: int | None = Field(default=None, ge=1)


class ActionExecutePayload(BaseModel):
    action: dict[str, Any]
    actor: str = Field(min_length=1, max_length=128)


class EventPublishPayload(BaseModel):
    event_type: str = Field(min_length=1)
    source: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None
    revision: int | None = Field(default=None, ge=1)


class HealthCheckRequestPayload(BaseModel):
    schema_version: Literal["v1"] = "v1"
    service_id: str = Field(min_length=1, max_length=36)
    item_id: str = Field(min_length=1, max_length=255)
    check_type: Literal["http", "tcp", "icmp"]
    target: str = Field(min_length=1, max_length=1024)
    timeout_ms: int = Field(ge=100, le=120_000)
    latency_threshold_ms: int = Field(ge=1, le=120_000)
    window_size: int = Field(ge=1, le=500)
    ts: datetime = Field(default_factory=lambda: datetime.now(UTC))


class HealthCheckResultPayload(BaseModel):
    schema_version: Literal["v1"] = "v1"
    service_id: str = Field(min_length=1, max_length=36)
    item_id: str = Field(min_length=1, max_length=255)
    check_type: Literal["http", "tcp", "icmp"]
    target: str = Field(min_length=1, max_length=1024)
    success: bool
    latency_ms: int | None = Field(default=None, ge=0)
    error_message: str | None = None
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


__all__ = [
    "ActionExecutePayload",
    "BusMessageType",
    "BusMessageV1",
    "BusReplyV1",
    "BusTraceV1",
    "EventPublishPayload",
    "HealthCheckRequestPayload",
    "HealthCheckResultPayload",
    "StorageKvDeletePayload",
    "StorageKvGetPayload",
    "StorageKvSetPayload",
    "StorageTableDeletePayload",
    "StorageTableGetPayload",
    "StorageTableQueryPayload",
    "StorageTableUpsertPayload",
]
