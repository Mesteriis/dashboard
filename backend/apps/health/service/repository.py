from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from apps.health.model.contracts import (
    HealthCheckResultV1,
    HealthSample,
    MonitoredService,
    MonitoredServiceSpec,
    ServiceHealthState,
)
from apps.health.model.sqlalchemy import (
    HealthSampleRow,
    MonitoredServiceRow,
    ServiceHealthStateRow,
)
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class HealthRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def list_services(self) -> list[MonitoredService]:
        statement = select(MonitoredServiceRow).order_by(MonitoredServiceRow.name.asc(), MonitoredServiceRow.id.asc())
        async with self._session_factory() as session:
            rows = (await session.scalars(statement)).all()
        return [self._to_service(row) for row in rows]

    async def list_enabled_services(self) -> list[MonitoredService]:
        statement = (
            select(MonitoredServiceRow)
            .where(MonitoredServiceRow.enabled.is_(True))
            .order_by(MonitoredServiceRow.name.asc(), MonitoredServiceRow.id.asc())
        )
        async with self._session_factory() as session:
            rows = (await session.scalars(statement)).all()
        return [self._to_service(row) for row in rows]

    async def get_service(self, service_id: UUID) -> MonitoredService | None:
        async with self._session_factory() as session:
            row = await session.get(MonitoredServiceRow, str(service_id))
        if row is None:
            return None
        return self._to_service(row)

    async def create_service(
        self,
        *,
        item_id: str,
        name: str,
        check_type: str,
        target: str,
        interval_sec: int,
        timeout_ms: int,
        latency_threshold_ms: int,
        tls_verify: bool = True,
        enabled: bool,
    ) -> MonitoredService:
        now = datetime.now(UTC)
        row = MonitoredServiceRow(
            id=str(uuid4()),
            item_id=item_id,
            name=name,
            check_type=check_type,
            target=target,
            interval_sec=interval_sec,
            timeout_ms=timeout_ms,
            latency_threshold_ms=latency_threshold_ms,
            tls_verify=tls_verify,
            enabled=enabled,
            created_at=now,
            updated_at=now,
        )
        async with self._session_factory() as session, session.begin():
            session.add(row)
        return self._to_service(row)

    async def sync_services(self, specs: list[MonitoredServiceSpec]) -> None:
        now = datetime.now(UTC)
        spec_by_id = {str(spec.id): spec for spec in specs}

        async with self._session_factory() as session, session.begin():
            existing_rows = (await session.scalars(select(MonitoredServiceRow))).all()
            existing_by_id = {row.id: row for row in existing_rows}

            for service_id, spec in spec_by_id.items():
                row = existing_by_id.get(service_id)
                if row is None:
                    session.add(
                        MonitoredServiceRow(
                            id=service_id,
                            item_id=spec.item_id,
                            name=spec.name,
                            check_type=spec.check_type,
                            target=spec.target,
                            interval_sec=spec.interval_sec,
                            timeout_ms=spec.timeout_ms,
                            latency_threshold_ms=spec.latency_threshold_ms,
                            tls_verify=spec.tls_verify,
                            enabled=spec.enabled,
                            created_at=now,
                            updated_at=now,
                        )
                    )
                    continue

                row.name = spec.name
                row.item_id = spec.item_id
                row.check_type = spec.check_type
                row.target = spec.target
                row.interval_sec = spec.interval_sec
                row.timeout_ms = spec.timeout_ms
                row.latency_threshold_ms = spec.latency_threshold_ms
                row.tls_verify = spec.tls_verify
                row.enabled = spec.enabled
                row.updated_at = now

            for row in existing_rows:
                if row.id in spec_by_id:
                    continue
                if row.enabled:
                    row.enabled = False
                    row.updated_at = now

    async def update_service(self, service_id: UUID, patch: dict[str, Any]) -> MonitoredService | None:
        if not patch:
            return await self.get_service(service_id)

        async with self._session_factory() as session, session.begin():
            row = await session.get(MonitoredServiceRow, str(service_id))
            if row is None:
                return None
            for key, value in patch.items():
                if hasattr(row, key):
                    setattr(row, key, value)
            row.updated_at = datetime.now(UTC)
        return await self.get_service(service_id)

    async def delete_service(self, service_id: UUID) -> bool:
        async with self._session_factory() as session, session.begin():
            row = await session.get(MonitoredServiceRow, str(service_id))
            if row is None:
                return False
            await session.delete(row)
            return True

    async def insert_sample(self, sample: HealthCheckResultV1) -> HealthSample:
        row = HealthSampleRow(
            service_id=str(sample.service_id),
            ts=_as_utc(sample.checked_at),
            success=sample.success,
            latency_ms=sample.latency_ms,
            error_message=sample.error_message,
        )
        async with self._session_factory() as session, session.begin():
            session.add(row)
            await session.flush()
        return self._to_sample(row)

    async def list_latest_samples(self, service_id: UUID, *, limit: int) -> list[HealthSample]:
        statement = (
            select(HealthSampleRow)
            .where(HealthSampleRow.service_id == str(service_id))
            .order_by(HealthSampleRow.ts.desc(), HealthSampleRow.id.desc())
            .limit(max(1, limit))
        )
        async with self._session_factory() as session:
            rows = (await session.scalars(statement)).all()
        return [self._to_sample(row) for row in rows]

    async def list_snapshot_items(self) -> list[dict[str, object]]:
        statement = (
            select(MonitoredServiceRow, ServiceHealthStateRow)
            .join(
                ServiceHealthStateRow,
                ServiceHealthStateRow.service_id == MonitoredServiceRow.id,
            )
            .where(MonitoredServiceRow.enabled.is_(True))
        )
        async with self._session_factory() as session:
            rows = (await session.execute(statement)).all()

        payload: list[dict[str, object]] = []
        for service_row, state_row in rows:
            status = str(state_row.current_status or "unknown").strip().lower()
            if status not in {"online", "degraded", "down", "unknown"}:
                status = "unknown"
            payload.append(
                {
                    "item_id": str(service_row.item_id),
                    "ok": status in {"online", "degraded"},
                    "status": status,
                    "level": status,
                    "latency_ms": round(state_row.avg_latency) if state_row.avg_latency is not None else None,
                    "success_rate": float(state_row.success_rate),
                    "consecutive_failures": int(state_row.consecutive_failures),
                    "error": "check failed" if status == "down" else None,
                    "reason": None,
                }
            )
        return payload

    async def get_state(self, service_id: UUID) -> ServiceHealthState | None:
        async with self._session_factory() as session:
            row = await session.get(ServiceHealthStateRow, str(service_id))
        if row is None:
            return None
        return self._to_state(row)

    async def upsert_state(
        self,
        *,
        service_id: UUID,
        status: str,
        last_change_ts: datetime,
        avg_latency: float | None,
        success_rate: float,
        consecutive_failures: int,
    ) -> ServiceHealthState:
        now = datetime.now(UTC)
        async with self._session_factory() as session, session.begin():
            row = await session.get(ServiceHealthStateRow, str(service_id))
            if row is None:
                row = ServiceHealthStateRow(
                    service_id=str(service_id),
                    current_status=status,
                    last_change_ts=_as_utc(last_change_ts),
                    avg_latency=avg_latency,
                    success_rate=success_rate,
                    consecutive_failures=consecutive_failures,
                    updated_at=now,
                )
                session.add(row)
            else:
                row.current_status = status
                row.last_change_ts = _as_utc(last_change_ts)
                row.avg_latency = avg_latency
                row.success_rate = success_rate
                row.consecutive_failures = consecutive_failures
                row.updated_at = now
        latest = await self.get_state(service_id)
        if latest is None:
            raise RuntimeError("Failed to upsert health state")
        return latest

    async def delete_samples_older_than(self, cutoff_ts: datetime) -> int:
        statement = delete(HealthSampleRow).where(HealthSampleRow.ts < _as_utc(cutoff_ts))
        async with self._session_factory() as session, session.begin():
            result = await session.execute(statement)
        return int(result.rowcount or 0)

    @staticmethod
    def _to_service(row: MonitoredServiceRow) -> MonitoredService:
        return MonitoredService(
            id=UUID(row.id),
            item_id=row.item_id,
            name=row.name,
            check_type=row.check_type,  # type: ignore[arg-type]
            target=row.target,
            interval_sec=int(row.interval_sec),
            timeout_ms=int(row.timeout_ms),
            latency_threshold_ms=int(row.latency_threshold_ms),
            tls_verify=bool(row.tls_verify),
            enabled=bool(row.enabled),
            created_at=_as_utc(row.created_at),
            updated_at=_as_utc(row.updated_at),
        )

    @staticmethod
    def _to_sample(row: HealthSampleRow) -> HealthSample:
        return HealthSample(
            id=int(row.id),
            service_id=UUID(str(row.service_id)),
            ts=_as_utc(row.ts),
            success=bool(row.success),
            latency_ms=int(row.latency_ms) if row.latency_ms is not None else None,
            error_message=row.error_message,
        )

    @staticmethod
    def _to_state(row: ServiceHealthStateRow) -> ServiceHealthState:
        return ServiceHealthState(
            service_id=UUID(row.service_id),
            current_status=row.current_status,  # type: ignore[arg-type]
            last_change_ts=_as_utc(row.last_change_ts),
            avg_latency=float(row.avg_latency) if row.avg_latency is not None else None,
            success_rate=float(row.success_rate),
            consecutive_failures=int(row.consecutive_failures),
            updated_at=_as_utc(row.updated_at),
        )


__all__ = ["HealthRepository"]
