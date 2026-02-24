from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.contracts.errors import ApiError
from core.contracts.models import (
    ActionEnvelope,
    StorageMigrationActionPayload,
    StorageMigrationPlanEntry,
    StorageMigrationResult,
)
from core.events.protocols import EventPublisher
from core.storage import (
    PhysicalStorage,
    StorageDdlNotAllowed,
    StorageError,
    StorageLimitExceeded,
    StorageModeRouter,
    StorageQueryNotAllowed,
    StorageRateLimited,
    UniversalStorage,
)

from .locks import StorageMigrationLockManager

EVENT_MIGRATE_STARTED = "migrate.started"
EVENT_MIGRATE_PROGRESS = "migrate.progress"
EVENT_MIGRATE_COMPLETED = "migrate.completed"
EVENT_MIGRATE_FAILED = "migrate.failed"


@dataclass(frozen=True)
class _MigrationContext:
    action_id: str
    plugin_id: str
    from_mode: str
    to_mode: str
    tables: list[str]


class StorageMigrationRunner:
    def __init__(
        self,
        *,
        event_bus: EventPublisher,
        storage_router: StorageModeRouter,
        universal_storage: UniversalStorage,
        physical_storage: PhysicalStorage,
        lock_manager: StorageMigrationLockManager,
    ) -> None:
        self._event_bus = event_bus
        self._storage_router = storage_router
        self._universal_storage = universal_storage
        self._physical_storage = physical_storage
        self._lock_manager = lock_manager

    async def run(self, action: ActionEnvelope) -> dict[str, Any]:
        request = self._parse_payload(action)
        context = _MigrationContext(
            action_id=str(action.id),
            plugin_id=request.plugin_id,
            from_mode=request.from_mode,
            to_mode=request.to_mode,
            tables=request.tables,
        )

        self._validate_request(request)
        await self._emit_started(context=context, request=request)

        try:
            plan = await self._build_plan(request)

            if request.dry_run:
                result = StorageMigrationResult(
                    plugin_id=request.plugin_id,
                    from_mode=request.from_mode,
                    to_mode=request.to_mode,
                    strategy=request.strategy,
                    dry_run=True,
                    tables=request.tables,
                    plan=plan,
                    copied_rows={},
                    switched_tables=[],
                    status="planned",
                )
                await self._emit_completed(context=context, request=request, result=result)
                return result.model_dump(mode="json")

            copied_rows: dict[str, int] = {}
            switched_tables: list[str] = []

            with self._lock_manager.read_only_lock(plugin_id=request.plugin_id, tables=request.tables):
                if request.to_mode == "core_physical_tables":
                    await self._physical_storage.ensure_plugin_ready(request.plugin_id)

                for table in request.tables:
                    copied_rows[table] = await self._copy_table(
                        plugin_id=request.plugin_id,
                        table=table,
                        from_mode=request.from_mode,
                        to_mode=request.to_mode,
                        batch_size=request.batch_size,
                        action_id=context.action_id,
                    )
                    self._storage_router.set_table_mode(
                        plugin_id=request.plugin_id,
                        table=table,
                        mode=request.to_mode,
                    )
                    switched_tables.append(table)

            result = StorageMigrationResult(
                plugin_id=request.plugin_id,
                from_mode=request.from_mode,
                to_mode=request.to_mode,
                strategy=request.strategy,
                dry_run=False,
                tables=request.tables,
                plan=plan,
                copied_rows=copied_rows,
                switched_tables=switched_tables,
                status="completed",
            )
            await self._emit_completed(context=context, request=request, result=result)
            return result.model_dump(mode="json")
        except ApiError:
            await self._emit_failed(
                context=context,
                error="storage_migration_api_error",
            )
            raise
        except StorageError as exc:
            await self._emit_failed(
                context=context,
                error=f"{exc.code}: {exc.message}",
            )
            raise self._map_storage_error(exc) from exc
        except Exception as exc:
            await self._emit_failed(context=context, error=str(exc))
            raise ApiError(
                status_code=500,
                code="storage_migration_failed",
                message=str(exc),
            ) from exc

    @staticmethod
    def _map_storage_error(exc: StorageError) -> ApiError:
        if isinstance(exc, StorageRateLimited):
            status_code = 429
        elif isinstance(exc, StorageLimitExceeded | StorageQueryNotAllowed | StorageDdlNotAllowed):
            status_code = 422
        else:
            status_code = 500
        return ApiError(
            status_code=status_code,
            code=exc.code,
            message=exc.message,
        )

    def _parse_payload(self, action: ActionEnvelope) -> StorageMigrationActionPayload:
        payload = dict(action.payload)
        if action.dry_run:
            payload["dry_run"] = True

        try:
            return StorageMigrationActionPayload.model_validate(payload)
        except Exception as exc:
            raise ApiError(
                status_code=422,
                code="storage_migration_invalid_payload",
                message=str(exc),
            ) from exc

    def _validate_request(self, request: StorageMigrationActionPayload) -> None:
        plugin_config = self._storage_router.get_plugin_config(request.plugin_id)

        allowed_tables = {table.name for table in plugin_config.tables}
        invalid_tables = [table for table in request.tables if table not in allowed_tables]
        if invalid_tables:
            raise ApiError(
                status_code=422,
                code="storage_migration_table_not_allowed",
                message=(
                    f"Tables are not configured for plugin '{request.plugin_id}': {', '.join(sorted(invalid_tables))}"
                ),
            )

        for table in request.tables:
            current_mode = self._storage_router.get_table_mode(plugin_id=request.plugin_id, table=table)
            if current_mode != request.from_mode:
                raise ApiError(
                    status_code=409,
                    code="storage_migration_mode_mismatch",
                    message=(
                        f"Table '{table}' for plugin '{request.plugin_id}' is in mode "
                        f"'{current_mode}', expected '{request.from_mode}'"
                    ),
                )

        if request.to_mode == "core_physical_tables" and plugin_config.ddl is None:
            raise ApiError(
                status_code=422,
                code="storage_migration_missing_ddl",
                message=f"Plugin '{request.plugin_id}' has no DDL spec for physical tables migration",
            )

        if request.strategy != "read_only_lock":
            raise ApiError(
                status_code=422,
                code="storage_migration_strategy_not_supported",
                message="Only strategy 'read_only_lock' is currently supported",
            )

    async def _build_plan(self, request: StorageMigrationActionPayload) -> list[StorageMigrationPlanEntry]:
        plan: list[StorageMigrationPlanEntry] = []
        for table in request.tables:
            rows = await self._count_rows(plugin_id=request.plugin_id, table=table, mode=request.from_mode)
            plan.append(StorageMigrationPlanEntry(table=table, rows=rows))
        return plan

    async def _count_rows(self, *, plugin_id: str, table: str, mode: str) -> int:
        if mode == "core_universal":
            return await self._universal_storage.count_table_rows(plugin_id=plugin_id, table=table)
        if mode == "core_physical_tables":
            return await self._physical_storage.count_table_rows(plugin_id=plugin_id, table=table)
        raise ApiError(
            status_code=422,
            code="storage_migration_unknown_mode",
            message=f"Unsupported storage mode '{mode}'",
        )

    async def _copy_table(
        self,
        *,
        plugin_id: str,
        table: str,
        from_mode: str,
        to_mode: str,
        batch_size: int,
        action_id: str,
    ) -> int:
        after_pk: Any | None = None
        copied = 0

        while True:
            batch = await self._read_batch(
                plugin_id=plugin_id,
                table=table,
                mode=from_mode,
                batch_size=batch_size,
                after_pk=after_pk,
            )
            if not batch:
                break

            for pk_value, row in batch:
                await self._write_row(plugin_id=plugin_id, table=table, mode=to_mode, row=row)
                copied += 1
                after_pk = pk_value

            await self._event_bus.publish(
                event_type=EVENT_MIGRATE_PROGRESS,
                source="core.plugins.storage.migration",
                correlation_id=action_id,
                payload={
                    "action_id": action_id,
                    "plugin_id": plugin_id,
                    "table": table,
                    "copied": copied,
                },
            )

        return copied

    async def _read_batch(
        self,
        *,
        plugin_id: str,
        table: str,
        mode: str,
        batch_size: int,
        after_pk: Any | None,
    ) -> list[tuple[Any, dict[str, Any]]]:
        if mode == "core_universal":
            return await self._universal_storage.read_rows_batch(
                plugin_id=plugin_id,
                table=table,
                batch_size=batch_size,
                after_pk=after_pk,
            )
        if mode == "core_physical_tables":
            return await self._physical_storage.read_rows_batch(
                plugin_id=plugin_id,
                table=table,
                batch_size=batch_size,
                after_pk=after_pk,
            )
        raise ApiError(
            status_code=422,
            code="storage_migration_unknown_mode",
            message=f"Unsupported storage mode '{mode}'",
        )

    async def _write_row(self, *, plugin_id: str, table: str, mode: str, row: dict[str, Any]) -> None:
        if mode == "core_universal":
            await self._universal_storage.migration_table_upsert(plugin_id=plugin_id, table=table, row=row)
            return
        if mode == "core_physical_tables":
            await self._physical_storage.migration_table_upsert(plugin_id=plugin_id, table=table, row=row)
            return
        raise ApiError(
            status_code=422,
            code="storage_migration_unknown_mode",
            message=f"Unsupported storage mode '{mode}'",
        )

    async def _emit_started(self, *, context: _MigrationContext, request: StorageMigrationActionPayload) -> None:
        await self._event_bus.publish(
            event_type=EVENT_MIGRATE_STARTED,
            source="core.plugins.storage.migration",
            correlation_id=context.action_id,
            payload={
                "action_id": context.action_id,
                "plugin_id": context.plugin_id,
                "from_mode": context.from_mode,
                "to_mode": context.to_mode,
                "tables": context.tables,
                "dry_run": request.dry_run,
                "strategy": request.strategy,
            },
        )

    async def _emit_completed(
        self,
        *,
        context: _MigrationContext,
        request: StorageMigrationActionPayload,
        result: StorageMigrationResult,
    ) -> None:
        await self._event_bus.publish(
            event_type=EVENT_MIGRATE_COMPLETED,
            source="core.plugins.storage.migration",
            correlation_id=context.action_id,
            payload={
                "action_id": context.action_id,
                "plugin_id": context.plugin_id,
                "from_mode": context.from_mode,
                "to_mode": context.to_mode,
                "tables": context.tables,
                "dry_run": request.dry_run,
                "strategy": request.strategy,
                "status": result.status,
                "copied_rows": result.copied_rows,
                "switched_tables": result.switched_tables,
            },
        )

    async def _emit_failed(self, *, context: _MigrationContext, error: str) -> None:
        await self._event_bus.publish(
            event_type=EVENT_MIGRATE_FAILED,
            source="core.plugins.storage.migration",
            correlation_id=context.action_id,
            payload={
                "action_id": context.action_id,
                "plugin_id": context.plugin_id,
                "from_mode": context.from_mode,
                "to_mode": context.to_mode,
                "tables": context.tables,
                "error": error,
            },
        )


__all__ = [
    "EVENT_MIGRATE_COMPLETED",
    "EVENT_MIGRATE_FAILED",
    "EVENT_MIGRATE_PROGRESS",
    "EVENT_MIGRATE_STARTED",
    "StorageMigrationRunner",
]
