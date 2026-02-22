from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from db.models import DashboardConfigRecord, DashboardConfigRevision

_ACTIVE_CONFIG_ID = 1


@dataclass(frozen=True)
class StoredDashboardConfig:
    revision: int
    payload_json: str
    payload_sha256: str
    source: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class StoredDashboardConfigRevision:
    revision: int
    payload_json: str
    payload_sha256: str
    source: str
    created_at: datetime


class DashboardConfigRepository:
    def __init__(self, session_factory: sessionmaker[Session]):
        self._session_factory = session_factory

    def fetch_active(self) -> StoredDashboardConfig | None:
        with self._session_factory() as session:
            record = session.get(DashboardConfigRecord, _ACTIVE_CONFIG_ID)
            if record is None:
                return None
            return _to_stored_record(record)

    def save_active(
        self,
        *,
        payload_json: str,
        payload_sha256: str,
        source: str,
        now: datetime | None = None,
    ) -> StoredDashboardConfig:
        timestamp = _as_utc(now) if now is not None else datetime.now(UTC)

        with self._session_factory() as session:
            with session.begin():
                record = session.get(DashboardConfigRecord, _ACTIVE_CONFIG_ID)
                if record is None:
                    revision = 1
                    record = DashboardConfigRecord(
                        id=_ACTIVE_CONFIG_ID,
                        revision=revision,
                        payload_json=payload_json,
                        payload_sha256=payload_sha256,
                        source=source,
                        created_at=timestamp,
                        updated_at=timestamp,
                    )
                    session.add(record)
                else:
                    revision = max(1, int(record.revision) + 1)
                    record.revision = revision
                    record.payload_json = payload_json
                    record.payload_sha256 = payload_sha256
                    record.source = source
                    record.updated_at = timestamp

                session.add(
                    DashboardConfigRevision(
                        revision=revision,
                        payload_json=payload_json,
                        payload_sha256=payload_sha256,
                        source=source,
                        created_at=timestamp,
                    )
                )

            session.refresh(record)
            return _to_stored_record(record)

    def list_revisions(self) -> list[StoredDashboardConfigRevision]:
        statement = select(DashboardConfigRevision).order_by(
            DashboardConfigRevision.revision.asc(),
            DashboardConfigRevision.id.asc(),
        )
        with self._session_factory() as session:
            rows = session.scalars(statement).all()
        return [_to_stored_revision(row) for row in rows]


def _to_stored_record(record: DashboardConfigRecord) -> StoredDashboardConfig:
    return StoredDashboardConfig(
        revision=int(record.revision),
        payload_json=record.payload_json,
        payload_sha256=record.payload_sha256,
        source=record.source,
        created_at=_as_utc(record.created_at),
        updated_at=_as_utc(record.updated_at),
    )


def _to_stored_revision(revision: DashboardConfigRevision) -> StoredDashboardConfigRevision:
    return StoredDashboardConfigRevision(
        revision=int(revision.revision),
        payload_json=revision.payload_json,
        payload_sha256=revision.payload_sha256,
        source=revision.source,
        created_at=_as_utc(revision.created_at),
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


__all__ = [
    "DashboardConfigRepository",
    "StoredDashboardConfig",
    "StoredDashboardConfigRevision",
]
