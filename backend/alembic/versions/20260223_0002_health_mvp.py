"""Health monitoring MVP tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260223_0002"
down_revision = "20260223_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "monitored_service",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("item_id", sa.String(length=255), nullable=False, unique=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("check_type", sa.String(length=16), nullable=False),
        sa.Column("target", sa.String(length=1024), nullable=False),
        sa.Column("interval_sec", sa.Integer(), nullable=False),
        sa.Column("timeout_ms", sa.Integer(), nullable=False),
        sa.Column("latency_threshold_ms", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_monitored_service_enabled_updated",
        "monitored_service",
        ["enabled", "updated_at"],
    )
    op.create_index(
        "ix_monitored_service_item_id",
        "monitored_service",
        ["item_id"],
    )

    op.create_table(
        "health_sample",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("service_id", sa.String(length=36), sa.ForeignKey("monitored_service.id", ondelete="CASCADE")),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("ix_health_sample_service_ts", "health_sample", ["service_id", "ts"])
    op.create_index("ix_health_sample_ts", "health_sample", ["ts"])

    op.create_table(
        "service_health_state",
        sa.Column(
            "service_id",
            sa.String(length=36),
            sa.ForeignKey("monitored_service.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("current_status", sa.String(length=16), nullable=False),
        sa.Column("last_change_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("avg_latency", sa.Float(), nullable=True),
        sa.Column("success_rate", sa.Float(), nullable=False),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_service_health_state_status", "service_health_state", ["current_status"])


def downgrade() -> None:
    op.drop_index("ix_service_health_state_status", table_name="service_health_state")
    op.drop_table("service_health_state")

    op.drop_index("ix_health_sample_ts", table_name="health_sample")
    op.drop_index("ix_health_sample_service_ts", table_name="health_sample")
    op.drop_table("health_sample")

    op.drop_index("ix_monitored_service_enabled_updated", table_name="monitored_service")
    op.drop_index("ix_monitored_service_item_id", table_name="monitored_service")
    op.drop_table("monitored_service")
