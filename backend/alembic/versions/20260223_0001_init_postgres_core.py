"""Initial Postgres schema for Oko core and plugin storage."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260223_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "config_revisions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("revision", sa.Integer(), nullable=False, unique=True),
        sa.Column("parent_revision", sa.Integer(), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("payload_sha256", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=True),
    )

    op.create_table(
        "app_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("active_revision", sa.Integer(), sa.ForeignKey("config_revisions.revision"), nullable=False),
        sa.Column("state_seq", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", sa.String(length=128), nullable=True),
        sa.Column("reason", sa.String(length=255), nullable=True),
    )

    op.create_table(
        "actions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("type", sa.String(length=128), nullable=False),
        sa.Column("capability", sa.String(length=128), nullable=False),
        sa.Column("requested_by", sa.String(length=128), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("error_json", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("trace_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_actions_created_at", "actions", ["created_at"])
    op.create_index("ix_actions_type_status", "actions", ["type", "status"])
    op.create_index("ix_actions_idempotency_key", "actions", ["idempotency_key"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("action_id", sa.String(length=36), nullable=True),
        sa.Column("capability", sa.String(length=128), nullable=False),
        sa.Column("resource", sa.String(length=255), nullable=True),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
    )
    op.create_index("ix_audit_log_ts", "audit_log", ["ts"])
    op.create_index("ix_audit_log_actor", "audit_log", ["actor"])

    op.create_table(
        "plugin_kv",
        sa.Column("plugin_id", sa.String(length=128), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("is_secret", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value_bytes", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("plugin_id", "key", name="pk_plugin_kv"),
    )
    op.create_index("ix_plugin_kv_plugin_updated", "plugin_kv", ["plugin_id", "updated_at"])

    op.create_table(
        "plugin_rows",
        sa.Column("plugin_id", sa.String(length=128), nullable=False),
        sa.Column("table", sa.String(length=128), nullable=False),
        sa.Column("pk", sa.String(length=255), nullable=False),
        sa.Column("row_json", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("row_bytes", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("plugin_id", "table", "pk", name="pk_plugin_rows"),
    )
    op.create_index("ix_plugin_rows_plugin_table", "plugin_rows", ["plugin_id", "table"])
    op.create_index("ix_plugin_rows_plugin_table_updated", "plugin_rows", ["plugin_id", "table", "updated_at"])

    op.create_table(
        "plugin_indexes",
        sa.Column("plugin_id", sa.String(length=128), nullable=False),
        sa.Column("table", sa.String(length=128), nullable=False),
        sa.Column("index_name", sa.String(length=128), nullable=False),
        sa.Column("index_value", sa.String(length=512), nullable=False),
        sa.Column("pk", sa.String(length=255), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("plugin_id", "table", "index_name", "pk", name="pk_plugin_indexes"),
    )
    op.create_index(
        "ix_plugin_indexes_lookup",
        "plugin_indexes",
        ["plugin_id", "table", "index_name", "index_value"],
    )
    op.create_index("ix_plugin_indexes_pk", "plugin_indexes", ["plugin_id", "table", "pk"])


def downgrade() -> None:
    op.drop_index("ix_plugin_indexes_pk", table_name="plugin_indexes")
    op.drop_index("ix_plugin_indexes_lookup", table_name="plugin_indexes")
    op.drop_table("plugin_indexes")

    op.drop_index("ix_plugin_rows_plugin_table_updated", table_name="plugin_rows")
    op.drop_index("ix_plugin_rows_plugin_table", table_name="plugin_rows")
    op.drop_table("plugin_rows")

    op.drop_index("ix_plugin_kv_plugin_updated", table_name="plugin_kv")
    op.drop_table("plugin_kv")

    op.drop_index("ix_audit_log_actor", table_name="audit_log")
    op.drop_index("ix_audit_log_ts", table_name="audit_log")
    op.drop_table("audit_log")

    op.drop_index("ix_actions_idempotency_key", table_name="actions")
    op.drop_index("ix_actions_type_status", table_name="actions")
    op.drop_index("ix_actions_created_at", table_name="actions")
    op.drop_table("actions")

    op.drop_table("app_state")
    op.drop_table("config_revisions")
