from __future__ import annotations

from core.contracts.models import ActionEnvelope
from core.events.protocols import EventPublisher
from core.gateway import ActionGateway
from core.storage import PhysicalStorage, StorageModeRouter, UniversalStorage

from .locks import StorageMigrationLockManager
from .runner import StorageMigrationRunner

ACTION_STORAGE_MIGRATE = "core.plugin.storage.migrate"
CAPABILITY_STORAGE_MIGRATE = "core.plugin.storage.migrate"


def register_storage_migration_action(
    gateway: ActionGateway,
    *,
    event_bus: EventPublisher,
    storage_router: StorageModeRouter,
    universal_storage: UniversalStorage,
    physical_storage: PhysicalStorage,
    lock_manager: StorageMigrationLockManager,
) -> StorageMigrationRunner:
    runner = StorageMigrationRunner(
        event_bus=event_bus,
        storage_router=storage_router,
        universal_storage=universal_storage,
        physical_storage=physical_storage,
        lock_manager=lock_manager,
    )

    async def _executor(action: ActionEnvelope) -> dict[str, object]:
        return await runner.run(action)

    gateway.register_action(
        action_type=ACTION_STORAGE_MIGRATE,
        capability=CAPABILITY_STORAGE_MIGRATE,
        description="Migrate plugin logical storage tables between mode A/B",
        executor=_executor,
        dry_run_supported=True,
    )
    return runner


__all__ = [
    "ACTION_STORAGE_MIGRATE",
    "CAPABILITY_STORAGE_MIGRATE",
    "register_storage_migration_action",
]
