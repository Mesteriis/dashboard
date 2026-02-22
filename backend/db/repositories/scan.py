from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from db.models import LanScanSnapshot
from sqlalchemy import delete, desc, select
from sqlalchemy.orm import Session, sessionmaker


@dataclass(frozen=True)
class StoredLanScanSnapshot:
    id: int
    generated_at: datetime
    payload_json: str
    created_at: datetime


class LanScanSnapshotRepository:
    def __init__(self, session_factory: sessionmaker[Session]):
        self._session_factory = session_factory

    def fetch_latest(self) -> StoredLanScanSnapshot | None:
        statement = select(LanScanSnapshot).order_by(
            desc(LanScanSnapshot.generated_at),
            desc(LanScanSnapshot.id),
        )
        with self._session_factory() as session:
            row = session.scalars(statement).first()
            if row is None:
                return None
            return _to_stored_snapshot(row)

    def save_snapshot(
        self,
        *,
        generated_at: datetime,
        payload_json: str,
        created_at: datetime | None = None,
    ) -> StoredLanScanSnapshot:
        generated_ts = _as_utc(generated_at)
        created_ts = _as_utc(created_at) if created_at is not None else datetime.now(UTC)

        with self._session_factory() as session:
            with session.begin():
                row = LanScanSnapshot(
                    generated_at=generated_ts,
                    payload_json=payload_json,
                    created_at=created_ts,
                )
                session.add(row)
            session.refresh(row)
            return _to_stored_snapshot(row)

    def prune_old(self, *, keep_last: int) -> int:
        keep = max(1, keep_last)

        with self._session_factory() as session:
            rows = session.scalars(
                select(LanScanSnapshot.id).order_by(
                    desc(LanScanSnapshot.generated_at),
                    desc(LanScanSnapshot.id),
                )
            ).all()
            stale_ids = rows[keep:]
            if not stale_ids:
                return 0

            session.execute(delete(LanScanSnapshot).where(LanScanSnapshot.id.in_(stale_ids)))
            session.commit()
            return len(stale_ids)


def _to_stored_snapshot(row: LanScanSnapshot) -> StoredLanScanSnapshot:
    return StoredLanScanSnapshot(
        id=int(row.id),
        generated_at=_as_utc(row.generated_at),
        payload_json=row.payload_json,
        created_at=_as_utc(row.created_at),
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


__all__ = ["LanScanSnapshotRepository", "StoredLanScanSnapshot"]
