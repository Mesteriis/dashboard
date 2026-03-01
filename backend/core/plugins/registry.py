from __future__ import annotations

import logging
from datetime import UTC, datetime
import importlib
import importlib.util
import inspect
from pathlib import Path
import sys
import types
from typing import Any

from .loader import (
    PluginLocation,
    PluginLoader,
    PluginManifestParser,
    PluginScanner,
    PluginUIConfigParser,
)
from .page_manifest import resolve_page_manifest, serialize_resolution
from .schemas import PluginInfo, PluginManifest, PluginState, PluginUIConfig

logger = logging.getLogger(__name__)


class PluginRegistry:
    """
    Central registry for all plugins.
    Manages plugin lifecycle: discovery, loading, activation, and teardown.
    """
    
    def __init__(
        self,
        scanner: PluginScanner,
        loader: PluginLoader | None = None,
        setup_kwargs: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize plugin registry.
        
        Args:
            scanner: Plugin scanner for discovery
            loader: Plugin loader for runtime loading
        """
        self.scanner = scanner
        self.loader = loader or PluginLoader()
        self._setup_kwargs = dict(setup_kwargs or {})
        self._plugins: dict[str, PluginInfo] = {}
        self._initialized = False

    def set_setup_kwargs(self, setup_kwargs: dict[str, Any] | None = None) -> None:
        self._setup_kwargs = dict(setup_kwargs or {})

    def _call_with_supported_kwargs(self, fn: Any, kwargs: dict[str, Any]) -> Any:
        if not kwargs:
            return fn()

        signature = inspect.signature(fn)
        params = signature.parameters
        if any(param.kind == inspect.Parameter.VAR_KEYWORD for param in params.values()):
            return fn(**kwargs)

        accepted: dict[str, Any] = {}
        for name, param in params.items():
            if param.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.VAR_POSITIONAL):
                continue
            if name in kwargs:
                accepted[name] = kwargs[name]
        return fn(**accepted)
    
    def initialize(self) -> None:
        """Initialize the registry by scanning for plugins."""
        if self._initialized:
            return
        
        logger.info("Initializing plugin registry...")
        self.scan()
        self._initialized = True
        logger.info(f"Plugin registry initialized with {len(self._plugins)} plugins")
    
    def scan(self) -> dict[str, PluginInfo]:
        """
        Scan for plugins and update registry.
        
        Returns:
            Dictionary of plugin ID to PluginInfo
        """
        logger.debug("Scanning for plugins...")
        locations = self.scanner.scan()
        
        for location in locations:
            if location.package_name not in self._plugins:
                plugin_info = self._create_plugin_info(location)
                self._plugins[location.package_name] = plugin_info
                logger.info(f"Registered plugin: {location.package_name}")
        
        return self._plugins.copy()

    def sync(self) -> dict[str, list[str]]:
        """
        Rescan plugin directories and synchronize in-memory registry.
        Adds newly discovered plugins, refreshes metadata for existing ones, and
        removes entries for plugin directories that disappeared.
        """
        locations = self.scanner.scan()
        discovered = {location.package_name: location for location in locations}

        added: list[str] = []
        removed: list[str] = []

        for plugin_id, location in discovered.items():
            existing = self._plugins.get(plugin_id)
            if existing is None:
                plugin_info = self._create_plugin_info(location)
                self._plugins[plugin_id] = plugin_info
                added.append(plugin_id)
                logger.info(f"Registered plugin: {plugin_id}")
                continue

            existing.path = location.path
            existing.scope = location.scope
            self._plugins[plugin_id] = existing

        for plugin_id in list(self._plugins.keys()):
            if plugin_id in discovered:
                continue
            self.unload_plugin(plugin_id)
            self._plugins.pop(plugin_id, None)
            removed.append(plugin_id)
            logger.info(f"Removed plugin from registry: {plugin_id}")

        return {
            "added": added,
            "removed": removed,
        }

    def refresh_plugin_metadata(self, plugin_id: str) -> PluginInfo | None:
        plugin = self._plugins.get(plugin_id)
        if plugin is None or plugin.path is None:
            return None
        manifest = self._load_manifest_from_path(plugin.path)
        if manifest is not None:
            plugin.manifest = manifest
        plugin.ui_config = self._load_ui_config_from_path(plugin.path)
        plugin.metadata["page_manifest"] = serialize_resolution(
            resolve_page_manifest(
                plugin_id=plugin.id,
                plugin_version=plugin.manifest.version,
                plugin_path=plugin.path,
            )
        )
        self._plugins[plugin_id] = plugin
        return plugin
    
    def _create_plugin_info(self, location: PluginLocation) -> PluginInfo:
        """Create PluginInfo from discovered location."""
        # Try to load manifest from manifest.py first
        manifest = self._load_manifest_from_path(location.path)
        
        if manifest is None:
            # Create minimal manifest
            manifest = PluginManifest(
                name=location.package_name,
                version="0.0.0",
                description=f"Plugin: {location.package_name}",
            )
        
        # Try to load UI config
        ui_config = self._load_ui_config_from_path(location.path)
        
        plugin_info = PluginInfo(
            id=location.package_name,
            manifest=manifest,
            ui_config=ui_config,
            state=PluginState.DISCOVERED,
            scope=location.scope,
            path=location.path,
        )
        plugin_info.metadata["page_manifest"] = serialize_resolution(
            resolve_page_manifest(
                plugin_id=plugin_info.id,
                plugin_version=plugin_info.manifest.version,
                plugin_path=plugin_info.path,
            )
        )
        return plugin_info
    
    def _load_manifest_from_path(self, path: Path) -> PluginManifest | None:
        """Load manifest from plugin path."""
        plugin_parent = str(path.parent)
        plugin_name = path.name
        if plugin_parent not in sys.path:
            sys.path.insert(0, plugin_parent)
        importlib.invalidate_caches()

        manifest_file = path / "manifest.py"
        if manifest_file.exists():
            try:
                package = sys.modules.get(plugin_name)
                if package is None:
                    package = types.ModuleType(plugin_name)
                    package.__path__ = [str(path)]  # type: ignore[attr-defined]
                    sys.modules[plugin_name] = package

                module_name = f"{plugin_name}.manifest"
                spec = importlib.util.spec_from_file_location(module_name, manifest_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)
                    return PluginManifestParser.parse_from_module(module)
            except Exception as exc:
                logger.warning(f"Failed to load manifest from {manifest_file}: {exc}")

        init_file = path / "__init__.py"
        if init_file.exists():
            try:
                spec = importlib.util.spec_from_file_location(
                    plugin_name,
                    init_file,
                    submodule_search_locations=[str(path)],
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[plugin_name] = module
                    spec.loader.exec_module(module)
                    return PluginManifestParser.parse_from_module(module)
            except Exception as exc:
                logger.warning(f"Failed to load manifest from {init_file}: {exc}")

        return None
    
    def _load_ui_config_from_path(self, path: Path) -> PluginUIConfig | None:
        """Load UI config from plugin path."""
        # Try ui.yaml
        import yaml
        
        ui_yaml = path / "ui.yaml"
        if ui_yaml.exists():
            try:
                with open(ui_yaml, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if isinstance(data, dict):
                    return PluginUIConfigParser.parse_from_dict(data)
            except Exception as exc:
                logger.warning(f"Failed to load UI config from {ui_yaml}: {exc}")
        
        # Try ui_config.py
        ui_config_file = path / "ui_config.py"
        if ui_config_file.exists():
            try:
                plugin_parent = str(path.parent)
                plugin_name = path.name
                if plugin_parent not in sys.path:
                    sys.path.insert(0, plugin_parent)
                importlib.invalidate_caches()
                package = sys.modules.get(plugin_name)
                if package is None:
                    package = types.ModuleType(plugin_name)
                    package.__path__ = [str(path)]  # type: ignore[attr-defined]
                    sys.modules[plugin_name] = package
                module_name = f"{plugin_name}.ui_config"
                spec = importlib.util.spec_from_file_location(module_name, ui_config_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)
                    return PluginUIConfigParser.parse_from_module(module)
            except Exception as exc:
                logger.warning(f"Failed to load UI config from {ui_config_file}: {exc}")
        
        return None
    
    def get_plugin(self, plugin_id: str) -> PluginInfo | None:
        """Get plugin by ID."""
        return self._plugins.get(plugin_id)
    
    def list_plugins(self) -> list[PluginInfo]:
        """List all registered plugins."""
        return list(self._plugins.values())
    
    def list_active(self) -> list[PluginInfo]:
        """List all active plugins."""
        return [p for p in self._plugins.values() if p.state == PluginState.ACTIVE]
    
    def load_plugin(self, plugin_id: str) -> PluginInfo:
        """
        Load a plugin into memory.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            Updated PluginInfo
        """
        plugin = self._plugins.get(plugin_id)
        if plugin is None:
            raise ValueError(f"Plugin not found: {plugin_id}")
        
        if plugin.state == PluginState.ACTIVE:
            logger.debug(f"Plugin {plugin_id} is already active")
            return plugin
        
        plugin = self.loader.load_plugin(plugin)

        # If loaded successfully, try to initialize
        if plugin.state == PluginState.ACTIVE and plugin.module and hasattr(plugin.module, "setup"):
            try:
                self._call_with_supported_kwargs(plugin.module.setup, self._setup_kwargs)
                logger.info(f"Initialized plugin: {plugin_id}")
            except Exception as exc:
                plugin.state = PluginState.ERROR
                plugin.error = f"Setup failed: {exc}"
                logger.exception(f"Plugin {plugin_id} setup failed: {exc}")
        
        plugin.loaded_at = datetime.now(UTC)
        self._plugins[plugin_id] = plugin
        return plugin
    
    def unload_plugin(self, plugin_id: str) -> bool:
        """
        Unload a plugin from memory.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            True if successfully unloaded
        """
        plugin = self._plugins.get(plugin_id)
        if plugin is None:
            return False
        
        if plugin.state != PluginState.ACTIVE:
            logger.debug(f"Plugin {plugin_id} is not active")
            return False
        
        # Call teardown if available
        if plugin.module and hasattr(plugin.module, "teardown"):
            try:
                plugin.module.teardown()
            except Exception as exc:
                logger.warning(f"Plugin {plugin_id} teardown failed: {exc}")
        
        # Unload module
        success = self.loader.unload_plugin(plugin_id)
        
        if success:
            plugin.state = PluginState.DISCOVERED
            plugin.module = None
            plugin.loaded_at = None
            self._plugins[plugin_id] = plugin
            logger.info(f"Unloaded plugin: {plugin_id}")
        
        return success
    
    def reload_plugin(self, plugin_id: str) -> PluginInfo:
        """Reload a plugin."""
        self.unload_plugin(plugin_id)
        return self.load_plugin(plugin_id)
    
    def enable_plugin(self, plugin_id: str) -> PluginInfo:
        """Enable a disabled plugin."""
        plugin = self._plugins.get(plugin_id)
        if plugin is None:
            raise ValueError(f"Plugin not found: {plugin_id}")
        
        if plugin.state == PluginState.DISABLED:
            plugin.state = PluginState.DISCOVERED
            self._plugins[plugin_id] = plugin
        
        return self.load_plugin(plugin_id)
    
    def disable_plugin(self, plugin_id: str) -> bool:
        """Disable a plugin."""
        plugin = self._plugins.get(plugin_id)
        if plugin is None:
            return False
        
        self.unload_plugin(plugin_id)
        plugin.state = PluginState.DISABLED
        self._plugins[plugin_id] = plugin
        logger.info(f"Disabled plugin: {plugin_id}")
        return True
    
    def get_plugin_module(self, plugin_id: str) -> Any | None:
        """Get loaded plugin module."""
        return self.loader.get_module(plugin_id)
    
    def is_plugin_loaded(self, plugin_id: str) -> bool:
        """Check if plugin is loaded."""
        return self.loader.is_loaded(plugin_id)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert registry to dictionary."""
        return {
            "plugins": [p.to_dict() for p in self._plugins.values()],
            "total": len(self._plugins),
            "active": len([p for p in self._plugins.values() if p.state == PluginState.ACTIVE]),
            "discovered": len([p for p in self._plugins.values() if p.state == PluginState.DISCOVERED]),
            "error": len([p for p in self._plugins.values() if p.state == PluginState.ERROR]),
            "disabled": len([p for p in self._plugins.values() if p.state == PluginState.DISABLED]),
        }


__all__ = ["PluginRegistry"]
