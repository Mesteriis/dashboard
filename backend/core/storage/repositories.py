from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from core.contracts.models import ActionEnvelope, ActionStatus, ActiveState, AuditEvent, ConfigRevision
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .models import ActionRow, AppStateRow, AuditLogRow, ConfigRevisionRow


@dataclass(frozen=True)
class ActiveConfigSnapshot:
    active_state: ActiveState
    revision: ConfigRevision


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(serialized: str) -> str:
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _merge_patch(base: Any, patch: Any) -> Any:
    if not isinstance(patch, dict):
        return patch
    if not isinstance(base, dict):
        base = {}

    merged = dict(base)
    for key, value in patch.items():
        if value is None:
            merged.pop(key, None)
            continue
        if isinstance(value, dict):
            merged[key] = _merge_patch(merged.get(key), value)
            continue
        merged[key] = value
    return merged


class ConfigRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def fetch_active(self) -> ActiveConfigSnapshot | None:
        async with self._session_factory() as session:
            state = await session.get(AppStateRow, 1)
            if state is None:
                return None
            revision_row = await session.scalar(
                select(ConfigRevisionRow).where(ConfigRevisionRow.revision == state.active_revision)
            )
            if revision_row is None:
                return None
            return ActiveConfigSnapshot(
                active_state=self._to_active_state(state),
                revision=self._to_config_revision(revision_row),
            )

    async def fetch_revision(self, revision: int) -> ConfigRevision | None:
        async with self._session_factory() as session:
            row = await session.scalar(select(ConfigRevisionRow).where(ConfigRevisionRow.revision == revision))
            if row is None:
                return None
            return self._to_config_revision(row)

    async def list_revisions(self, *, limit: int = 100) -> list[ConfigRevision]:
        statement = (
            select(ConfigRevisionRow)
            .order_by(ConfigRevisionRow.revision.desc(), ConfigRevisionRow.id.desc())
            .limit(max(1, limit))
        )
        async with self._session_factory() as session:
            rows = (await session.scalars(statement)).all()
            return [self._to_config_revision(row) for row in rows]

    async def create_revision(
        self,
        *,
        payload: dict[str, Any],
        source: str,
        actor: str | None,
        reason: str | None = None,
    ) -> ActiveConfigSnapshot:
        serialized = _canonical_json(payload)
        payload_hash = _sha256(serialized)
        now = datetime.now(UTC)

        async with self._session_factory() as session, session.begin():
            active = await session.get(AppStateRow, 1)
            max_revision = await session.scalar(select(func.max(ConfigRevisionRow.revision)))
            next_revision = int(max_revision or 0) + 1
            parent_revision = active.active_revision if active is not None else None

            row = ConfigRevisionRow(
                revision=next_revision,
                parent_revision=parent_revision,
                payload_json=serialized,
                payload_sha256=payload_hash,
                source=source,
                created_at=now,
                created_by=actor,
            )
            session.add(row)
            await session.flush()

            if active is None:
                state = AppStateRow(
                    id=1,
                    active_revision=next_revision,
                    state_seq=1,
                    updated_at=now,
                    updated_by=actor,
                    reason=reason,
                )
                session.add(state)
            else:
                active.active_revision = next_revision
                active.state_seq = max(1, int(active.state_seq) + 1)
                active.updated_at = now
                active.updated_by = actor
                active.reason = reason

        snapshot = await self.fetch_active()
        if snapshot is None:
            raise RuntimeError("Active config state is not initialized after create_revision")
        return snapshot

    async def patch_active(
        self,
        *,
        patch: dict[str, Any],
        actor: str | None,
        source: str = "patch",
    ) -> ActiveConfigSnapshot:
        active = await self.fetch_active()
        if active is None:
            raise RuntimeError("Cannot patch config without active revision")
        merged = _merge_patch(active.revision.payload, patch)
        if not isinstance(merged, dict):
            raise ValueError("Config patch result must be an object")
        return await self.create_revision(payload=merged, source=source, actor=actor, reason="config_patch")

    async def rollback_to(self, *, revision: int, actor: str | None, source: str = "rollback") -> ActiveConfigSnapshot:
        target = await self.fetch_revision(revision)
        if target is None:
            raise KeyError(revision)
        return await self.create_revision(
            payload=target.payload,
            source=source,
            actor=actor,
            reason=f"rollback_to:{revision}",
        )

    @staticmethod
    def _to_active_state(row: AppStateRow) -> ActiveState:
        return ActiveState(
            active_revision=int(row.active_revision),
            state_seq=int(row.state_seq),
            updated_at=_as_utc(row.updated_at),
            updated_by=row.updated_by,
            reason=row.reason,
        )

    @staticmethod
    def _to_config_revision(row: ConfigRevisionRow) -> ConfigRevision:
        payload = json.loads(row.payload_json)
        if not isinstance(payload, dict):
            raise ValueError("Stored config revision payload must be an object")
        return ConfigRevision(
            revision=int(row.revision),
            parent_revision=int(row.parent_revision) if row.parent_revision is not None else None,
            sha256=row.payload_sha256,
            source=row.source,
            payload=payload,
            created_at=_as_utc(row.created_at),
            created_by=row.created_by,
        )


class ActionRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def create_queued(self, action: ActionEnvelope) -> ActionStatus:
        now = datetime.now(UTC)
        async with self._session_factory() as session, session.begin():
            existing = await session.get(ActionRow, str(action.id))
            if existing is None:
                session.add(
                    ActionRow(
                        id=str(action.id),
                        type=action.type,
                        capability=action.capability,
                        requested_by=action.requested_by,
                        requested_at=_as_utc(action.requested_at),
                        status="queued",
                        payload_json=_canonical_json(action.payload),
                        dry_run=bool(action.dry_run),
                        idempotency_key=action.idempotency_key,
                        trace_id=action.trace_id,
                        created_at=now,
                    )
                )
        status = await self.get(action.id)
        if status is None:
            raise RuntimeError("Action was not persisted")
        return status

    async def set_status(
        self,
        *,
        action_id: UUID,
        status: str,
        result: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
    ) -> ActionStatus:
        now = datetime.now(UTC)
        async with self._session_factory() as session, session.begin():
            row = await session.get(ActionRow, str(action_id))
            if row is None:
                raise KeyError(str(action_id))
            row.status = status
            if status == "running":
                row.started_at = now
            if status in {"succeeded", "failed", "cancelled", "blocked"}:
                row.finished_at = now
            if result is not None:
                row.result_json = _canonical_json(result)
            if error is not None:
                row.error_json = _canonical_json(error)

        updated = await self.get(action_id)
        if updated is None:
            raise RuntimeError("Action disappeared after status update")
        return updated

    async def get(self, action_id: UUID) -> ActionStatus | None:
        async with self._session_factory() as session:
            row = await session.get(ActionRow, str(action_id))
            if row is None:
                return None
            return self._to_action_status(row)

    async def list_history(self, *, limit: int = 100) -> list[ActionStatus]:
        statement = select(ActionRow).order_by(ActionRow.created_at.desc()).limit(max(1, limit))
        async with self._session_factory() as session:
            rows = (await session.scalars(statement)).all()
            return [self._to_action_status(row) for row in rows]

    @staticmethod
    def _to_action_status(row: ActionRow) -> ActionStatus:
        result = json.loads(row.result_json) if row.result_json else None
        error = json.loads(row.error_json) if row.error_json else None
        return ActionStatus(
            id=UUID(row.id),
            type=row.type,
            capability=row.capability,
            requested_by=row.requested_by,
            requested_at=_as_utc(row.requested_at),
            status=row.status,
            dry_run=bool(row.dry_run),
            result=result if isinstance(result, dict) else None,
            error=error if isinstance(error, dict) else None,
        )


class AuditRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def append(self, event: AuditEvent) -> None:
        async with self._session_factory() as session, session.begin():
            session.add(
                AuditLogRow(
                    ts=_as_utc(event.ts),
                    actor=event.actor,
                    action_id=str(event.action_id) if event.action_id else None,
                    capability=event.capability,
                    resource=event.resource,
                    decision=event.decision,
                    outcome=event.outcome,
                    reason=event.reason,
                    metadata_json=_canonical_json(event.metadata),
                )
            )


__all__ = ["ActionRepository", "ActiveConfigSnapshot", "AuditRepository", "ConfigRepository"]
