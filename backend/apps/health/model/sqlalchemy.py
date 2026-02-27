from __future__ import annotations

from datetime import UTC, datetime

from db.base import Base
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(UTC)


class MonitoredServiceRow(Base):
    __tablename__ = "monitored_service"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    item_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    check_type: Mapped[str] = mapped_column(String(16), nullable=False)
    target: Mapped[str] = mapped_column(String(1024), nullable=False)
    interval_sec: Mapped[int] = mapped_column(Integer, nullable=False)
    timeout_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    latency_threshold_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    tls_verify: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (
        Index("ix_monitored_service_enabled_updated", "enabled", "updated_at"),
        Index("ix_monitored_service_item_id", "item_id"),
    )


class HealthSampleRow(Base):
    __tablename__ = "health_sample"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    service_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("monitored_service.id", ondelete="CASCADE"),
        nullable=False,
    )
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_health_sample_service_ts", "service_id", "ts"),
        Index("ix_health_sample_ts", "ts"),
    )


class ServiceHealthStateRow(Base):
    __tablename__ = "service_health_state"

    service_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("monitored_service.id", ondelete="CASCADE"),
        primary_key=True,
    )
    current_status: Mapped[str] = mapped_column(String(16), nullable=False)
    last_change_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    avg_latency: Mapped[float | None] = mapped_column(Float, nullable=True)
    success_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (Index("ix_service_health_state_status", "current_status"),)


__all__ = [
    "HealthSampleRow",
    "MonitoredServiceRow",
    "ServiceHealthStateRow",
]
