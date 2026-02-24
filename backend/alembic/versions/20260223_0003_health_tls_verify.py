"""Add tls_verify flag for monitored health services."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260223_0003"
down_revision = "20260223_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "monitored_service",
        sa.Column("tls_verify", sa.Boolean(), nullable=True, server_default=sa.true()),
    )
    op.execute("UPDATE monitored_service SET tls_verify = TRUE WHERE tls_verify IS NULL")
    op.alter_column("monitored_service", "tls_verify", nullable=False)


def downgrade() -> None:
    op.drop_column("monitored_service", "tls_verify")
