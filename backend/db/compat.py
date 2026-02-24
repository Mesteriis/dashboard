from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def ensure_runtime_schema_compatibility(engine: AsyncEngine) -> None:
    # Older local databases may have monitored_service without item_id.
    # Align schema so health worker does not crash during sync.
    if engine.dialect.name != "postgresql":
        return

    async with engine.begin() as connection:
        await connection.execute(
            text("ALTER TABLE monitored_service ADD COLUMN IF NOT EXISTS item_id VARCHAR(255)")
        )
        await connection.execute(
            text("UPDATE monitored_service SET item_id = id WHERE item_id IS NULL OR item_id = ''")
        )
        await connection.execute(
            text("ALTER TABLE monitored_service ALTER COLUMN item_id SET NOT NULL")
        )
        await connection.execute(
            text("CREATE UNIQUE INDEX IF NOT EXISTS ix_monitored_service_item_id ON monitored_service (item_id)")
        )
        await connection.execute(
            text("ALTER TABLE monitored_service ADD COLUMN IF NOT EXISTS tls_verify BOOLEAN")
        )
        await connection.execute(
            text("UPDATE monitored_service SET tls_verify = TRUE WHERE tls_verify IS NULL")
        )
        await connection.execute(
            text("ALTER TABLE monitored_service ALTER COLUMN tls_verify SET NOT NULL")
        )


__all__ = ["ensure_runtime_schema_compatibility"]
