from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast

from db.models import HealthSample
from sqlalchemy import asc, delete, desc, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session, sessionmaker


@dataclass(frozen=True)
class HealthSampleWrite:
    item_id: str
    ts: datetime
    level: str
    latency_ms: int | None = None
    status_code: int | None = None


@dataclass(frozen=True)
class StoredHealthSample:
    item_id: str
    ts: datetime
    level: str
    latency_ms: int | None
    status_code: int | None


class HealthSampleRepository:
    def __init__(self, session_factory: sessionmaker[Session]):
        self._session_factory = session_factory

    def append_samples(self, samples: Iterable[HealthSampleWrite]) -> int:
        payload = list(samples)
        if not payload:
            return 0

        with self._session_factory() as session, session.begin():
            for sample in payload:
                session.add(
                    HealthSample(
                        item_id=sample.item_id,
                        ts=_as_utc(sample.ts),
                        level=sample.level,
                        latency_ms=sample.latency_ms,
                        status_code=sample.status_code,
                    )
                )
        return len(payload)

    def list_recent_by_item_ids(
        self,
        *,
        item_ids: Iterable[str],
        limit_per_item: int,
    ) -> dict[str, list[StoredHealthSample]]:
        ids = sorted({item_id for item_id in item_ids if item_id})
        if not ids:
            return {}

        limit = max(1, limit_per_item)
        statement = (
            select(HealthSample)
            .where(HealthSample.item_id.in_(ids))
            .order_by(
                asc(HealthSample.item_id),
                desc(HealthSample.ts),
                desc(HealthSample.id),
            )
        )

        by_item: dict[str, list[StoredHealthSample]] = defaultdict(list)
        with self._session_factory() as session:
            rows = session.scalars(statement).all()

        for row in rows:
            current = by_item[row.item_id]
            if len(current) >= limit:
                continue
            current.append(
                StoredHealthSample(
                    item_id=row.item_id,
                    ts=_as_utc(row.ts),
                    level=row.level,
                    latency_ms=row.latency_ms,
                    status_code=row.status_code,
                )
            )

        for item_id, values in by_item.items():
            values.reverse()
            by_item[item_id] = values

        return by_item.copy()

    def delete_samples_not_in_item_ids(self, item_ids: Iterable[str]) -> int:
        ids = sorted({item_id for item_id in item_ids if item_id})

        statement = delete(HealthSample)
        if ids:
            statement = statement.where(HealthSample.item_id.not_in(ids))

        with self._session_factory() as session, session.begin():
            result = cast(CursorResult[Any], session.execute(statement))
            return int(result.rowcount or 0)

    def trim_samples_per_item(
        self,
        *,
        item_ids: Iterable[str],
        limit_per_item: int,
    ) -> int:
        ids = sorted({item_id for item_id in item_ids if item_id})
        if not ids:
            return 0

        limit = max(1, limit_per_item)
        deleted_total = 0
        with self._session_factory() as session, session.begin():
            for item_id in ids:
                stale_ids = session.scalars(
                    select(HealthSample.id)
                    .where(HealthSample.item_id == item_id)
                    .order_by(desc(HealthSample.ts), desc(HealthSample.id))
                    .offset(limit)
                ).all()
                if not stale_ids:
                    continue
                result = cast(
                    CursorResult[Any],
                    session.execute(delete(HealthSample).where(HealthSample.id.in_(stale_ids))),
                )
                deleted_total += int(result.rowcount or 0)

        return deleted_total

    def delete_samples_older_than(self, cutoff: datetime) -> int:
        """Delete all samples older than the specified cutoff datetime."""
        statement = delete(HealthSample).where(HealthSample.ts < cutoff)
        with self._session_factory() as session, session.begin():
            result = cast(CursorResult[Any], session.execute(statement))
            return int(result.rowcount or 0)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


__all__ = ["HealthSampleRepository", "HealthSampleWrite", "StoredHealthSample"]
