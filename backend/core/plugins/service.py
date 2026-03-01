from __future__ import annotations

import asyncio
import inspect
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .loader import PluginScanner
from .registry import PluginRegistry
from .router import PluginRouter
from .schemas import PluginInfo, PluginState

logger = logging.getLogger(__name__)


@dataclass
class PluginService:
    """
    Main plugin service that orchestrates all plugin components.
    This is the primary interface for interacting with the plugin system.
    """
    registry: PluginRegistry
    router: PluginRouter
    _fingerprints: dict[str, tuple[int, int]] = field(default_factory=dict)
    _runtime_started: bool = False
    _started_plugins: set[str] = field(default_factory=set)
    
    @classmethod
    def create(
        cls,
        plugin_dirs: tuple[Path, ...],
        base_path: str = "/plugins",
        api_base_path: str = "/api/v1/plugins",
        plugin_setup_kwargs: dict[str, Any] | None = None,
    ) -> PluginService:
        """
        Create and initialize plugin service.
        
        Args:
            plugin_dirs: Directories to scan for plugins
            base_path: Base path for plugin pages
            api_base_path: Base path for plugin APIs
            plugin_setup_kwargs: Optional kwargs injected into plugin `setup(...)`
            
        Returns:
            Initialized PluginService instance
        """
        # Create scanner
        scanner = PluginScanner(plugin_dirs=plugin_dirs)
        
        # Create registry
        registry = PluginRegistry(scanner=scanner, setup_kwargs=plugin_setup_kwargs)
        registry.initialize()
        
        # Create router
        router = PluginRouter(registry=registry, base_path=base_path, api_base_path=api_base_path)
        
        # Auto-load active plugins
        for plugin in registry.list_plugins():
            if plugin.state == PluginState.DISCOVERED:
                try:
                    registry.load_plugin(plugin.id)
                except Exception as exc:
                    logger.warning(f"Failed to auto-load plugin {plugin.id}: {exc}")
        
        # Mount routes for active plugins
        router.mount_all_active()

        service = cls(registry=registry, router=router)
        service._refresh_fingerprints()
        return service
    
    def list_plugins(self) -> list[PluginInfo]:
        """List all plugins."""
        return self.registry.list_plugins()
    
    def get_plugin(self, plugin_id: str) -> PluginInfo | None:
        """Get plugin by ID."""
        return self.registry.get_plugin(plugin_id)
    
    def load_plugin(self, plugin_id: str) -> PluginInfo:
        """Load a plugin."""
        plugin = self.registry.load_plugin(plugin_id)
        self.router._mount_plugin_routes(plugin)
        if self._runtime_started:
            self._schedule_startup_hook(plugin)
        return plugin
    
    def unload_plugin(self, plugin_id: str) -> bool:
        """Unload a plugin."""
        plugin = self.registry.get_plugin(plugin_id)
        if plugin is not None and self._runtime_started:
            self._schedule_shutdown_hook(plugin)
        success = self.registry.unload_plugin(plugin_id)
        if success:
            self.router._unmount_plugin_routes(plugin_id)
        return success
    
    def reload_plugin(self, plugin_id: str) -> PluginInfo:
        """Reload a plugin."""
        plugin = self.registry.get_plugin(plugin_id)
        if plugin is not None and self._runtime_started:
            self._schedule_shutdown_hook(plugin)
        self.router._unmount_plugin_routes(plugin_id)
        plugin = self.registry.reload_plugin(plugin_id)
        self.router._mount_plugin_routes(plugin)
        if self._runtime_started:
            self._schedule_startup_hook(plugin)
        return plugin
    
    def enable_plugin(self, plugin_id: str) -> PluginInfo:
        """Enable a plugin."""
        plugin = self.registry.enable_plugin(plugin_id)
        self.router._mount_plugin_routes(plugin)
        if self._runtime_started:
            self._schedule_startup_hook(plugin)
        return plugin
    
    def disable_plugin(self, plugin_id: str) -> bool:
        """Disable a plugin."""
        plugin = self.registry.get_plugin(plugin_id)
        if plugin is not None and self._runtime_started:
            self._schedule_shutdown_hook(plugin)
        success = self.registry.disable_plugin(plugin_id)
        if success:
            self.router._unmount_plugin_routes(plugin_id)
        return success
    
    def to_dict(self) -> dict:
        """Get plugin service state as dictionary."""
        return self.registry.to_dict()

    def _schedule_startup_hook(self, plugin: PluginInfo) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(
            self._invoke_plugin_hook(plugin, hook_name="on_startup", mark_started=True),
            name=f"plugin-startup-{plugin.id}",
        )

    def _schedule_shutdown_hook(self, plugin: PluginInfo) -> None:
        self._started_plugins.discard(plugin.id)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(
            self._invoke_plugin_hook(plugin, hook_name="on_shutdown", mark_started=False),
            name=f"plugin-shutdown-{plugin.id}",
        )

    async def _invoke_plugin_hook(
        self,
        plugin: PluginInfo,
        *,
        hook_name: str,
        mark_started: bool,
    ) -> None:
        if plugin.module is None:
            return

        hook = getattr(plugin.module, hook_name, None)
        if hook is None:
            if mark_started:
                self._started_plugins.add(plugin.id)
            else:
                self._started_plugins.discard(plugin.id)
            return

        if mark_started and plugin.id in self._started_plugins:
            return

        try:
            result = hook()
            if inspect.isawaitable(result):
                await result
            if mark_started:
                self._started_plugins.add(plugin.id)
            else:
                self._started_plugins.discard(plugin.id)
        except Exception:
            logger.exception("Plugin hook failed: %s (%s)", plugin.id, hook_name)

    async def startup(self) -> None:
        self._runtime_started = True
        for plugin in self.registry.list_active():
            await self._invoke_plugin_hook(plugin, hook_name="on_startup", mark_started=True)

    async def shutdown(self) -> None:
        active_plugins: list[PluginInfo] = []
        for plugin_id in list(self._started_plugins):
            plugin = self.registry.get_plugin(plugin_id)
            if plugin is not None:
                active_plugins.append(plugin)
        for plugin in active_plugins:
            await self._invoke_plugin_hook(plugin, hook_name="on_shutdown", mark_started=False)
        self._runtime_started = False

    def _plugin_fingerprint(self, path: Path | None) -> tuple[int, int]:
        if path is None or not path.exists():
            return (0, 0)
        files = [
            entry
            for entry in path.rglob("*")
            if entry.is_file()
            and "__pycache__" not in entry.parts
            and entry.suffix != ".pyc"
        ]
        if not files:
            return (0, 0)
        latest_mtime_ns = max(int(entry.stat().st_mtime_ns) for entry in files)
        return (len(files), latest_mtime_ns)

    def _refresh_fingerprints(self) -> None:
        self._fingerprints = {
            plugin.id: self._plugin_fingerprint(plugin.path)
            for plugin in self.registry.list_plugins()
        }

    def refresh_runtime(self) -> dict[str, list[str]]:
        summary: dict[str, list[str]] = {
            "added": [],
            "removed": [],
            "reloaded": [],
            "failed": [],
        }
        sync_result = self.registry.sync()
        summary["added"].extend(sync_result["added"])
        summary["removed"].extend(sync_result["removed"])

        for plugin_id in sync_result["removed"]:
            self.router._unmount_plugin_routes(plugin_id)
            self._started_plugins.discard(plugin_id)
            self._fingerprints.pop(plugin_id, None)

        for plugin_id in sync_result["added"]:
            plugin = self.registry.get_plugin(plugin_id)
            if plugin is None:
                continue
            if plugin.state == PluginState.DISCOVERED:
                try:
                    plugin = self.registry.load_plugin(plugin.id)
                except Exception:
                    logger.exception("Failed to auto-load newly discovered plugin %s", plugin.id)
                    summary["failed"].append(plugin.id)
                    continue
            if plugin.state == PluginState.ACTIVE:
                self.router._mount_plugin_routes(plugin)
                if self._runtime_started:
                    self._schedule_startup_hook(plugin)
            self._fingerprints[plugin.id] = self._plugin_fingerprint(plugin.path)

        for plugin in self.registry.list_plugins():
            if plugin.state == PluginState.DISABLED:
                self._fingerprints[plugin.id] = self._plugin_fingerprint(plugin.path)
                continue
            current = self._plugin_fingerprint(plugin.path)
            previous = self._fingerprints.get(plugin.id)
            if previous == current:
                continue
            try:
                plugin = self.registry.refresh_plugin_metadata(plugin.id) or plugin
                if plugin.state == PluginState.ACTIVE:
                    self.reload_plugin(plugin.id)
                    summary["reloaded"].append(plugin.id)
                elif plugin.state == PluginState.DISCOVERED:
                    loaded = self.registry.load_plugin(plugin.id)
                    if loaded.state == PluginState.ACTIVE:
                        self.router._mount_plugin_routes(loaded)
                        if self._runtime_started:
                            self._schedule_startup_hook(loaded)
                        summary["reloaded"].append(plugin.id)
            except Exception:
                logger.exception("Failed to refresh plugin %s", plugin.id)
                summary["failed"].append(plugin.id)
            finally:
                self._fingerprints[plugin.id] = self._plugin_fingerprint(plugin.path)

        return summary

    async def watch_loop(self, interval_sec: float = 1.5) -> None:
        poll = max(0.2, float(interval_sec))
        logger.info("Plugin watch loop running (poll=%.2fs)", poll)
        while True:
            await asyncio.sleep(poll)
            try:
                summary = self.refresh_runtime()
                if any(summary[key] for key in ("added", "removed", "reloaded", "failed")):
                    logger.info("Plugin runtime refresh: %s", summary)
            except Exception:
                logger.exception("Plugin watch loop cycle failed")


__all__ = ["PluginService"]
