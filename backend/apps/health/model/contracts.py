from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

HealthCheckType = Literal["http", "tcp", "icmp"]
HealthStatus = Literal["online", "degraded", "down", "unknown"]


class MonitoredService(BaseModel):
    id: UUID
    item_id: str = Field(min_length=1, max_length=255)
    name: str = Field(min_length=1, max_length=128)
    check_type: HealthCheckType
    target: str = Field(min_length=1, max_length=1024)
    interval_sec: int = Field(ge=1, le=3600)
    timeout_ms: int = Field(ge=100, le=120_000)
    latency_threshold_ms: int = Field(ge=1, le=120_000)
    tls_verify: bool = True
    enabled: bool
    created_at: datetime
    updated_at: datetime


class MonitoredServiceSpec(BaseModel):
    id: UUID
    item_id: str = Field(min_length=1, max_length=255)
    name: str = Field(min_length=1, max_length=128)
    check_type: HealthCheckType
    target: str = Field(min_length=1, max_length=1024)
    interval_sec: int = Field(ge=1, le=3600)
    timeout_ms: int = Field(ge=100, le=120_000)
    latency_threshold_ms: int = Field(ge=1, le=120_000)
    tls_verify: bool = True
    enabled: bool


class HealthSample(BaseModel):
    id: int
    service_id: UUID
    ts: datetime
    success: bool
    latency_ms: int | None = None
    error_message: str | None = None


class ServiceHealthState(BaseModel):
    service_id: UUID
    current_status: HealthStatus
    last_change_ts: datetime
    avg_latency: float | None = None
    success_rate: float = Field(ge=0.0, le=1.0)
    consecutive_failures: int = Field(ge=0)
    updated_at: datetime


class HealthCheckRequestedV1(BaseModel):
    schema_version: Literal["v1"] = "v1"
    service_id: UUID
    item_id: str = Field(min_length=1, max_length=255)
    check_type: HealthCheckType
    target: str
    timeout_ms: int = Field(ge=100, le=120_000)
    latency_threshold_ms: int = Field(ge=1, le=120_000)
    tls_verify: bool = True
    window_size: int = Field(ge=1, le=500)
    ts: datetime = Field(default_factory=lambda: datetime.now(UTC))


class HealthCheckResultV1(BaseModel):
    schema_version: Literal["v1"] = "v1"
    service_id: UUID
    item_id: str = Field(min_length=1, max_length=255)
    check_type: HealthCheckType
    target: str
    success: bool
    latency_ms: int | None = Field(default=None, ge=0)
    error_message: str | None = None
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class HealthStatusChangedV1(BaseModel):
    schema_version: Literal["v1"] = "v1"
    event_id: UUID = Field(default_factory=uuid4)
    service_id: UUID
    item_id: str = Field(min_length=1, max_length=255)
    previous_status: HealthStatus | None = None
    current_status: HealthStatus
    avg_latency_ms: float | None = None
    success_rate: float = Field(ge=0.0, le=1.0)
    consecutive_failures: int = Field(ge=0)
    window_size: int = Field(ge=1, le=500)
    changed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EvaluatedHealthState(BaseModel):
    status: HealthStatus
    avg_latency_ms: float | None = None
    success_rate: float = Field(ge=0.0, le=1.0)
    error_rate: float = Field(ge=0.0, le=1.0)
    consecutive_failures: int = Field(ge=0)
    sample_count: int = Field(ge=0)


__all__ = [
    "EvaluatedHealthState",
    "HealthCheckRequestedV1",
    "HealthCheckResultV1",
    "HealthCheckType",
    "HealthSample",
    "HealthStatus",
    "HealthStatusChangedV1",
    "MonitoredService",
    "MonitoredServiceSpec",
    "ServiceHealthState",
]
