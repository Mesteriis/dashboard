from __future__ import annotations

import asyncio
from contextlib import suppress
import logging
from dataclasses import dataclass
from pathlib import Path

from apps.health import (
    HealthChecker,
    HealthCheckRequestConsumer,
    HealthCheckResultConsumer,
    HealthRepository,
    HealthScheduler,
)
from apps.health.model import HealthSampleRow, MonitoredServiceRow, ServiceHealthStateRow
from config.settings import AppSettings, load_app_settings
from core.bus import ActionBusConsumer, BrokerActionRPC, BrokerStorageRPC, BusClient, StorageBusConsumer
from core.config import ConfigService
from core.contracts.storage import PluginStorageConfig, StorageDDLTableSpec, StorageLimits, StorageTableSpec
from core.events import BrokerEventPublisher, EventBus, EventPublishConsumer, EventPublisher
from core.gateway import ActionGateway
from core.plugins import PluginService as CorePluginService
from core.plugins.migrations import (
    StorageMigrationLockManager,
    StorageMigrationRunner,
    register_storage_migration_action,
)
from core.plugins.store import PluginInstaller, StoreClient
from core.storage import PhysicalStorage, StorageModeRouter, UniversalStorage, load_storage_ddl_specs
from core.storage.models import (
    ActionRow,
    AppStateRow,
    AuditLogRow,
    ConfigRevisionRow,
    PluginIndexRow,
    PluginKvRow,
    PluginRow,
)
from core.storage.repositories import ActionRepository, AuditRepository, ConfigRepository
from db.base import Base
from db.compat import ensure_runtime_schema_compatibility
from db.session import build_async_engine
from features.system import register_system_actions
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


@dataclass
class AppContainer:
    settings: AppSettings
    db_engine: AsyncEngine
    db_session_factory: async_sessionmaker[AsyncSession]
    config_repository: ConfigRepository
    action_repository: ActionRepository
    audit_repository: AuditRepository
    health_repository: HealthRepository
    event_bus: EventBus
    event_publisher: EventPublisher
    config_service: ConfigService
    gateway: ActionGateway
    plugin_storage: StorageModeRouter
    universal_storage: UniversalStorage
    physical_storage: PhysicalStorage
    storage_migration_lock_manager: StorageMigrationLockManager
    storage_migration_runner: StorageMigrationRunner
    bus_client: BusClient
    storage_rpc_client: BrokerStorageRPC
    action_rpc_client: BrokerActionRPC
    storage_bus_consumer: StorageBusConsumer
    action_bus_consumer: ActionBusConsumer
    event_publish_consumer: EventPublishConsumer
    health_check_request_consumer: HealthCheckRequestConsumer
    health_check_result_consumer: HealthCheckResultConsumer
    health_scheduler: HealthScheduler
    plugin_service: CorePluginService | None = None
    plugin_store_client: StoreClient | None = None
    plugin_installer: PluginInstaller | None = None
    plugin_watch_task: asyncio.Task[None] | None = None

    def _start_plugin_watcher(self) -> None:
        if self.settings.runtime_role != "backend":
            return
        if not self.plugin_service:
            return
        if self.plugin_watch_task and not self.plugin_watch_task.done():
            return
        interval = self.settings.plugin_watch_poll_sec
        self.plugin_watch_task = asyncio.create_task(
            self.plugin_service.watch_loop(interval_sec=interval),
            name="plugin-watch-loop",
        )
        logger.info("Plugin watcher started (poll=%.2fs)", interval)

    async def _stop_plugin_watcher(self) -> None:
        task = self.plugin_watch_task
        self.plugin_watch_task = None
        if not task:
            return
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

    async def startup(self) -> None:
        await self.bus_client.connect()
        async with self.db_engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        await ensure_runtime_schema_compatibility(self.db_engine)

        is_memory_bus = self.settings.broker_url.startswith("memory://")
        run_backend_local_consumers = self.settings.runtime_role == "backend" and (
            is_memory_bus or self.settings.enable_local_consumers
        )

        if self.settings.runtime_role == "worker":
            await self.physical_storage.install_all()
            await self.storage_bus_consumer.start()
            await self.action_bus_consumer.start()
            await self.health_check_request_consumer.start()
            await self.health_check_result_consumer.start()
            await self.health_scheduler.start()
            if self.plugin_service:
                await self.plugin_service.startup()
            return

        if run_backend_local_consumers:
            await self.event_publish_consumer.start()
            await self.physical_storage.install_all()
            await self.storage_bus_consumer.start()
            await self.action_bus_consumer.start()
            await self.health_check_request_consumer.start()
            await self.health_check_result_consumer.start()
            await self.health_scheduler.start()
            await self.config_service.startup_bootstrap()
            if self.plugin_service:
                await self.plugin_service.startup()
            self._start_plugin_watcher()
            return

        await self.event_publish_consumer.start()
        await self.config_service.startup_bootstrap()
        if self.plugin_service:
            await self.plugin_service.startup()
        self._start_plugin_watcher()

    async def shutdown(self) -> None:
        await self._stop_plugin_watcher()
        if self.plugin_service:
            await self.plugin_service.shutdown()
        is_memory_bus = self.settings.broker_url.startswith("memory://")
        run_backend_local_consumers = self.settings.runtime_role == "backend" and (
            is_memory_bus or self.settings.enable_local_consumers
        )

        if self.settings.runtime_role == "worker":
            await self.health_scheduler.stop()
            await self.health_check_result_consumer.stop()
            await self.health_check_request_consumer.stop()
            await self.action_bus_consumer.stop()
            await self.storage_bus_consumer.stop()
        elif run_backend_local_consumers:
            await self.health_scheduler.stop()
            await self.health_check_result_consumer.stop()
            await self.health_check_request_consumer.stop()
            await self.event_publish_consumer.stop()
            await self.action_bus_consumer.stop()
            await self.storage_bus_consumer.stop()
        else:
            await self.event_publish_consumer.stop()

        await self.bus_client.close()
        await self.db_engine.dispose()


def _storage_ddl_file(base_dir: Path) -> Path:
    return base_dir / "contracts" / "storage" / "tables.yaml"


def _default_plugin_storage_configs(base_dir: Path) -> dict[str, PluginStorageConfig]:
    ddl_specs = load_storage_ddl_specs(_storage_ddl_file(base_dir))
    if not ddl_specs:
        return {}

    def _table_index_columns(table: StorageDDLTableSpec) -> list[str]:
        # StorageTableSpec expects indexed field names, while DDL tables carry index objects.
        normalized: list[str] = []
        for index_spec in table.indexes:
            for column in index_spec.columns:
                column_name = column.strip()
                if not column_name:
                    continue
                if column_name == table.primary_key:
                    continue
                if column_name not in normalized:
                    normalized.append(column_name)
        return normalized

    return {
        plugin_id: PluginStorageConfig(
            mode="core_physical_tables",
            ddl=ddl_spec,
            limits=StorageLimits(
                max_tables=8,
                max_rows_per_table=20_000,
                max_row_bytes=262_144,
                max_kv_bytes=16_384,
                max_qps=60.0,
                max_query_limit=250,
            ),
            tables=[
                StorageTableSpec(
                    name=table.name,
                    primary_key=table.primary_key,
                    indexes=_table_index_columns(table),
                )
                for table in ddl_spec.tables
            ],
        )
        for plugin_id, ddl_spec in ddl_specs.items()
    }


def _default_storage_capabilities(plugin_configs: dict[str, PluginStorageConfig]) -> dict[str, set[str]]:
    allowed_ops = {
        "storage.kv.get",
        "storage.kv.set",
        "storage.kv.delete",
        "storage.table.get",
        "storage.table.upsert",
        "storage.table.delete",
        "storage.table.query",
    }
    return {plugin_id: set(allowed_ops) for plugin_id in plugin_configs}


def _ensure_core_models_loaded() -> None:
    _ = (
        ConfigRevisionRow,
        AppStateRow,
        ActionRow,
        AuditLogRow,
        PluginKvRow,
        PluginRow,
        PluginIndexRow,
        MonitoredServiceRow,
        HealthSampleRow,
        ServiceHealthStateRow,
    )


def build_container(base_dir: Path | None = None) -> AppContainer:
    settings = load_app_settings(base_dir=base_dir)
    db_engine = build_async_engine(settings.database_url)
    db_session_factory = async_sessionmaker(
        bind=db_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    plugin_storage_configs = _default_plugin_storage_configs(settings.base_dir)
    physical_configs = {
        plugin_id: config
        for plugin_id, config in plugin_storage_configs.items()
        if config.mode == "core_physical_tables"
    }

    _ensure_core_models_loaded()

    config_repository = ConfigRepository(db_session_factory)
    action_repository = ActionRepository(db_session_factory)
    audit_repository = AuditRepository(db_session_factory)
    health_repository = HealthRepository(db_session_factory)

    bus_client = BusClient(
        broker_url=settings.broker_url,
        prefetch_count=settings.broker_prefetch_count,
    )
    event_bus = EventBus()
    event_publisher: EventPublisher = BrokerEventPublisher(bus_client=bus_client)

    universal_storage = UniversalStorage(
        session_factory=db_session_factory,
        plugin_configs=plugin_storage_configs,
    )
    physical_storage = PhysicalStorage(
        session_factory=db_session_factory,
        plugin_configs=physical_configs,
    )
    storage_migration_lock_manager = StorageMigrationLockManager()
    plugin_storage = StorageModeRouter(
        plugin_configs=plugin_storage_configs,
        universal_storage=universal_storage,
        physical_storage=physical_storage,
        lock_manager=storage_migration_lock_manager,
    )

    storage_rpc_client = BrokerStorageRPC(
        bus_client=bus_client,
        timeout_sec=settings.storage_rpc_timeout_sec,
    )
    action_rpc_client = BrokerActionRPC(
        bus_client=bus_client,
        timeout_sec=settings.action_rpc_timeout_sec,
    )

    config_service = ConfigService(
        repository=config_repository,
        event_bus=event_publisher,
        bootstrap_file=settings.config_file,
    )
    gateway = ActionGateway(
        actions=action_repository,
        audit=audit_repository,
        events=event_publisher,
        execute_enabled=settings.actions_execute_enabled,
    )
    register_system_actions(gateway)
    storage_migration_runner = register_storage_migration_action(
        gateway,
        event_bus=event_publisher,
        storage_router=plugin_storage,
        universal_storage=universal_storage,
        physical_storage=physical_storage,
        lock_manager=storage_migration_lock_manager,
    )

    storage_bus_consumer = StorageBusConsumer(
        bus_client=bus_client,
        storage=plugin_storage,
        plugin_configs=plugin_storage_configs,
        capabilities=_default_storage_capabilities(plugin_storage_configs),
    )
    action_bus_consumer = ActionBusConsumer(
        bus_client=bus_client,
        gateway=gateway,
    )
    event_publish_consumer = EventPublishConsumer(
        bus_client=bus_client,
        event_bus=event_bus,
    )
    health_checker = HealthChecker(icmp_enabled=settings.health_icmp_enabled)
    health_check_request_consumer = HealthCheckRequestConsumer(
        bus_client=bus_client,
        checker=health_checker,
    )
    health_check_result_consumer = HealthCheckResultConsumer(
        bus_client=bus_client,
        repository=health_repository,
        event_publisher=event_publisher,
        window_size=settings.health_window_size,
    )
    health_scheduler = HealthScheduler(
        bus_client=bus_client,
        repository=health_repository,
        config_repository=config_repository,
        tick_sec=settings.health_scheduler_tick_sec,
        heartbeat_sec=settings.health_scheduler_heartbeat_sec,
        window_size=settings.health_window_size,
        retention_days=settings.health_retention_days,
        default_interval_sec=settings.health_default_interval_sec,
        default_timeout_ms=settings.health_default_timeout_ms,
        default_latency_threshold_ms=settings.health_default_latency_threshold_ms,
    )

    # Initialize plugin service
    plugin_dirs = (settings.base_dir / "plugins",)  # Production plugins
    plugin_dirs[0].mkdir(parents=True, exist_ok=True)
    plugin_service = CorePluginService.create(
        plugin_dirs=tuple(d for d in plugin_dirs if d.exists()),
        base_path="/plugins",
        api_base_path="/api/v1/plugins",
        plugin_setup_kwargs={
            "action_gateway": gateway,
            "event_bus": event_publisher,
            "config_service": config_service,
            "storage_rpc": storage_rpc_client,
            "runtime_role": settings.runtime_role,
        },
    )

    # Initialize plugin store client
    store_url = settings.store_url
    plugin_store_client = None
    plugin_installer = None
    if store_url:
        plugin_store_client = StoreClient.create(store_url=store_url)
        plugin_installer = PluginInstaller.create(
            install_dir=settings.base_dir / "plugins",
            store_url=store_url,
        )

    return AppContainer(
        settings=settings,
        db_engine=db_engine,
        db_session_factory=db_session_factory,
        config_repository=config_repository,
        action_repository=action_repository,
        audit_repository=audit_repository,
        health_repository=health_repository,
        event_bus=event_bus,
        event_publisher=event_publisher,
        config_service=config_service,
        gateway=gateway,
        plugin_storage=plugin_storage,
        universal_storage=universal_storage,
        physical_storage=physical_storage,
        storage_migration_lock_manager=storage_migration_lock_manager,
        storage_migration_runner=storage_migration_runner,
        bus_client=bus_client,
        storage_rpc_client=storage_rpc_client,
        action_rpc_client=action_rpc_client,
        storage_bus_consumer=storage_bus_consumer,
        action_bus_consumer=action_bus_consumer,
        event_publish_consumer=event_publish_consumer,
        health_check_request_consumer=health_check_request_consumer,
        health_check_result_consumer=health_check_result_consumer,
        health_scheduler=health_scheduler,
        plugin_service=plugin_service,
        plugin_store_client=plugin_store_client,
        plugin_installer=plugin_installer,
    )


__all__ = ["AppContainer", "build_container"]
