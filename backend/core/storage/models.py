from __future__ import annotations

from datetime import UTC, datetime

from db.base import Base
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, PrimaryKeyConstraint, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(UTC)


class ConfigRevisionRow(Base):
    __tablename__ = "config_revisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    parent_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)


class AppStateRow(Base):
    __tablename__ = "app_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    active_revision: Mapped[int] = mapped_column(Integer, ForeignKey("config_revisions.revision"), nullable=False)
    state_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)


class ActionRow(Base):
    __tablename__ = "actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    type: Mapped[str] = mapped_column(String(128), nullable=False)
    capability: Mapped[str] = mapped_column(String(128), nullable=False)
    requested_by: Mapped[str] = mapped_column(String(128), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_actions_created_at", "created_at"),
        Index("ix_actions_type_status", "type", "status"),
        Index("ix_actions_idempotency_key", "idempotency_key"),
    )


class AuditLogRow(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    action_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    capability: Mapped[str] = mapped_column(String(128), nullable=False)
    resource: Mapped[str | None] = mapped_column(String(255), nullable=True)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.current_timestamp(),
    )

    __table_args__ = (
        Index("ix_audit_log_ts", "ts"),
        Index("ix_audit_log_actor", "actor"),
    )


class PluginKvRow(Base):
    __tablename__ = "plugin_kv"

    plugin_id: Mapped[str] = mapped_column(String(128), nullable=False)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    is_secret: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    value_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("plugin_id", "key", name="pk_plugin_kv"),
        Index("ix_plugin_kv_plugin_updated", "plugin_id", "updated_at"),
    )


class PluginRow(Base):
    __tablename__ = "plugin_rows"

    plugin_id: Mapped[str] = mapped_column(String(128), nullable=False)
    table_name: Mapped[str] = mapped_column("table", String(128), nullable=False)
    pk: Mapped[str] = mapped_column(String(255), nullable=False)
    row_json: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    row_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("plugin_id", "table", "pk", name="pk_plugin_rows"),
        Index("ix_plugin_rows_plugin_table", "plugin_id", "table"),
        Index("ix_plugin_rows_plugin_table_updated", "plugin_id", "table", "updated_at"),
    )


class PluginIndexRow(Base):
    __tablename__ = "plugin_indexes"

    plugin_id: Mapped[str] = mapped_column(String(128), nullable=False)
    table_name: Mapped[str] = mapped_column("table", String(128), nullable=False)
    index_name: Mapped[str] = mapped_column(String(128), nullable=False)
    index_value: Mapped[str] = mapped_column(String(512), nullable=False)
    pk: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    __table_args__ = (
        PrimaryKeyConstraint("plugin_id", "table", "index_name", "pk", name="pk_plugin_indexes"),
        Index("ix_plugin_indexes_lookup", "plugin_id", "table", "index_name", "index_value"),
        Index("ix_plugin_indexes_pk", "plugin_id", "table", "pk"),
    )


__all__ = [
    "ActionRow",
    "AppStateRow",
    "AuditLogRow",
    "ConfigRevisionRow",
    "PluginIndexRow",
    "PluginKvRow",
    "PluginRow",
]
