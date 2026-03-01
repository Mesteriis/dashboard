from __future__ import annotations

import importlib.util
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .schemas import PluginInfo, PluginManifest, PluginScope, PluginState, PluginUIConfig

logger = logging.getLogger(__name__)


@dataclass
class PluginLocation:
    """Represents a discovered plugin location."""
    path: Path
    package_name: str
    scope: PluginScope


class PluginScanner:
    """
    Scans for plugins in specified directories.
    Supports runtime discovery of Python packages that follow the plugin convention.
    """
    
    MANIFEST_FILES = ("manifest.py", "__init__.py")
    UI_CONFIG_FILES = ("ui.yaml", "ui_config.py")
    
    def __init__(
        self,
        plugin_dirs: tuple[Path, ...],
        namespace: str = "dashboard_plugins",
    ) -> None:
        """
        Initialize plugin scanner.
        
        Args:
            plugin_dirs: Directories to scan for plugins
            namespace: Python namespace for plugin packages
        """
        self.plugin_dirs = tuple(dir for dir in plugin_dirs if dir.exists())
        self.namespace = namespace
        self._discovered: dict[str, PluginLocation] = {}
    
    def scan(self) -> list[PluginLocation]:
        """
        Scan all configured directories for plugins.
        
        Returns:
            List of discovered plugin locations
        """
        self._discovered.clear()
        
        for plugin_dir in self.plugin_dirs:
            self._scan_directory(plugin_dir)
        
        return list(self._discovered.values())
    
    def _scan_directory(self, directory: Path, scope: PluginScope = PluginScope.EXTERNAL) -> None:
        """Scan a single directory for plugin packages."""
        if not directory.exists():
            return
        
        # Check if directory itself is a plugin
        if self._is_plugin_package(directory):
            self._register_plugin(directory, scope)
            return
        
        # Scan subdirectories
        for item in directory.iterdir():
            if item.is_dir() and not item.name.startswith(("_", ".")):
                if self._is_plugin_package(item):
                    self._register_plugin(item, scope)
    
    def _is_plugin_package(self, path: Path) -> bool:
        """Check if a path contains a valid plugin package."""
        if not path.is_dir():
            return False
        
        # Must have __init__.py
        init_file = path / "__init__.py"
        if not init_file.exists():
            return False
        
        # Must have manifest (manifest.py or manifest info in __init__.py)
        for manifest_file in self.MANIFEST_FILES:
            if (path / manifest_file).exists():
                return True
        
        return False
    
    def _register_plugin(self, path: Path, scope: PluginScope) -> None:
        """Register a discovered plugin."""
        package_name = path.name
        self._discovered[package_name] = PluginLocation(
            path=path,
            package_name=package_name,
            scope=scope,
        )
        logger.debug(f"Discovered plugin: {package_name} at {path}")
    
    def get_discovered(self) -> dict[str, PluginLocation]:
        """Get all discovered plugins."""
        return self._discovered.copy()


class PluginLoader:
    """
    Loads and unloads Python plugin modules at runtime.
    Uses importlib to dynamically import plugin packages.
    """
    
    def __init__(self) -> None:
        self._loaded_modules: dict[str, Any] = {}
    
    def load_plugin(self, plugin_info: PluginInfo) -> PluginInfo:
        """
        Load a plugin module into memory.
        
        Args:
            plugin_info: Plugin information with path
            
        Returns:
            Updated PluginInfo with loaded module
        """
        if plugin_info.path is None:
            plugin_info.state = PluginState.ERROR
            plugin_info.error = "Plugin path is None"
            return plugin_info
        
        if not plugin_info.path.exists():
            plugin_info.state = PluginState.ERROR
            plugin_info.error = f"Plugin path does not exist: {plugin_info.path}"
            return plugin_info
        
        try:
            plugin_info.state = PluginState.LOADING
            
            # Add plugin parent directory to sys.path if not already there
            plugin_parent = str(plugin_info.path.parent)
            if plugin_parent not in sys.path:
                sys.path.insert(0, plugin_parent)
            
            # Load the module
            spec = importlib.util.spec_from_file_location(
                plugin_info.id,
                plugin_info.path / "__init__.py",
            )
            
            if spec is None or spec.loader is None:
                raise ImportError(f"Cannot load spec for plugin: {plugin_info.id}")
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[plugin_info.id] = module
            spec.loader.exec_module(module)
            
            self._loaded_modules[plugin_info.id] = module
            plugin_info.module = module
            plugin_info.state = PluginState.ACTIVE
            
            logger.info(f"Loaded plugin: {plugin_info.id} v{plugin_info.manifest.version}")
            
        except Exception as exc:
            plugin_info.state = PluginState.ERROR
            plugin_info.error = f"Failed to load plugin: {exc}"
            logger.exception(f"Failed to load plugin {plugin_info.id}: {exc}")
        
        return plugin_info
    
    def unload_plugin(self, plugin_id: str) -> bool:
        """
        Unload a plugin module from memory.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            True if successfully unloaded
        """
        if plugin_id not in self._loaded_modules:
            return False
        
        try:
            module = self._loaded_modules.pop(plugin_id)
            
            # Call plugin teardown if available
            if hasattr(module, "teardown"):
                try:
                    module.teardown()
                except Exception as exc:
                    logger.warning(f"Plugin {plugin_id} teardown failed: {exc}")
            
            # Remove from sys.modules
            if plugin_id in sys.modules:
                del sys.modules[plugin_id]
            
            logger.info(f"Unloaded plugin: {plugin_id}")
            return True
            
        except Exception as exc:
            logger.exception(f"Failed to unload plugin {plugin_id}: {exc}")
            return False
    
    def is_loaded(self, plugin_id: str) -> bool:
        """Check if a plugin is currently loaded."""
        return plugin_id in self._loaded_modules
    
    def get_module(self, plugin_id: str) -> Any | None:
        """Get loaded plugin module."""
        return self._loaded_modules.get(plugin_id)
    
    def list_loaded(self) -> list[str]:
        """List all loaded plugin IDs."""
        return list(self._loaded_modules.keys())


class PluginManifestParser:
    """Parses plugin manifest from Python module or YAML file."""
    
    @staticmethod
    def parse_from_module(module: Any) -> PluginManifest | None:
        """Extract manifest from loaded Python module."""
        # Check for PLUGIN_MANIFEST attribute
        if hasattr(module, "PLUGIN_MANIFEST"):
            manifest_data = getattr(module, "PLUGIN_MANIFEST")
            if isinstance(manifest_data, dict):
                return PluginManifest(**manifest_data)
        
        # Check for individual constants
        required_fields = ["PLUGIN_NAME", "PLUGIN_VERSION", "PLUGIN_DESCRIPTION"]
        if not all(hasattr(module, field) for field in required_fields):
            return None
        
        return PluginManifest(
            name=getattr(module, "PLUGIN_NAME"),
            version=getattr(module, "PLUGIN_VERSION"),
            description=getattr(module, "PLUGIN_DESCRIPTION", ""),
            author=getattr(module, "PLUGIN_AUTHOR", None),
            homepage=getattr(module, "PLUGIN_HOMEPAGE", None),
            license=getattr(module, "PLUGIN_LICENSE", None),
            tags=tuple(getattr(module, "PLUGIN_TAGS", [])),
            min_dashboard_version=getattr(module, "PLUGIN_MIN_DASHBOARD_VERSION", None),
            dependencies=tuple(getattr(module, "PLUGIN_DEPENDENCIES", [])),
            capabilities=tuple(getattr(module, "PLUGIN_CAPABILITIES", [])),
        )
    
    @staticmethod
    def parse_from_dict(data: dict[str, Any]) -> PluginManifest:
        """Parse manifest from dictionary (e.g., YAML)."""
        return PluginManifest(
            name=data.get("name", ""),
            version=data.get("version", "0.0.0"),
            description=data.get("description", ""),
            author=data.get("author"),
            homepage=data.get("homepage"),
            license=data.get("license"),
            tags=tuple(data.get("tags", [])),
            min_dashboard_version=data.get("min_dashboard_version"),
            dependencies=tuple(data.get("dependencies", [])),
            capabilities=tuple(data.get("capabilities", [])),
        )


class PluginUIConfigParser:
    """Parses plugin UI configuration from YAML or Python module."""
    
    @staticmethod
    def parse_from_dict(data: dict[str, Any]) -> PluginUIConfig:
        """Parse UI config from dictionary (e.g., YAML)."""
        return PluginUIConfig(
            has_page=data.get("has_page", False),
            page_path=data.get("page_path"),
            page_title=data.get("page_title"),
            page_icon=data.get("page_icon"),
            show_in_menu=data.get("show_in_menu", True),
            menu_group=data.get("menu_group"),
            menu_order=data.get("menu_order", 100),
            provides_widgets=data.get("provides_widgets", False),
            widgets=tuple(data.get("widgets", [])),
            static_dir=data.get("static_dir"),
            css_files=tuple(data.get("css_files", [])),
            js_files=tuple(data.get("js_files", [])),
            api_prefix=data.get("api_prefix"),
            api_routes=tuple(data.get("api_routes", [])),
            required_permissions=tuple(data.get("required_permissions", [])),
        )
    
    @staticmethod
    def parse_from_module(module: Any) -> PluginUIConfig | None:
        """Extract UI config from loaded Python module."""
        if hasattr(module, "PLUGIN_UI_CONFIG"):
            config_data = getattr(module, "PLUGIN_UI_CONFIG")
            if isinstance(config_data, dict):
                return PluginUIConfigParser.parse_from_dict(config_data)
        
        # Check for individual UI constants
        if not hasattr(module, "PLUGIN_HAS_PAGE"):
            return None
        
        return PluginUIConfig(
            has_page=getattr(module, "PLUGIN_HAS_PAGE", False),
            page_path=getattr(module, "PLUGIN_PAGE_PATH", None),
            page_title=getattr(module, "PLUGIN_PAGE_TITLE", None),
            page_icon=getattr(module, "PLUGIN_PAGE_ICON", None),
            show_in_menu=getattr(module, "PLUGIN_SHOW_IN_MENU", True),
            menu_group=getattr(module, "PLUGIN_MENU_GROUP", None),
            menu_order=getattr(module, "PLUGIN_MENU_ORDER", 100),
            provides_widgets=getattr(module, "PLUGIN_PROVIDES_WIDGETS", False),
            widgets=tuple(getattr(module, "PLUGIN_WIDGETS", [])),
            static_dir=getattr(module, "PLUGIN_STATIC_DIR", None),
            css_files=tuple(getattr(module, "PLUGIN_CSS_FILES", [])),
            js_files=tuple(getattr(module, "PLUGIN_JS_FILES", [])),
            api_prefix=getattr(module, "PLUGIN_API_PREFIX", None),
            api_routes=tuple(getattr(module, "PLUGIN_API_ROUTES", [])),
            required_permissions=tuple(getattr(module, "PLUGIN_REQUIRED_PERMISSIONS", [])),
        )


__all__ = [
    "PluginLoader",
    "PluginLocation",
    "PluginManifestParser",
    "PluginScanner",
    "PluginUIConfigParser",
]
