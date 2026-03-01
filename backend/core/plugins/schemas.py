from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class PluginState(str, Enum):
    """Plugin lifecycle state."""
    DISCOVERED = "discovered"
    LOADING = "loading"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"


class PluginScope(str, Enum):
    """Plugin visibility scope."""
    INTERNAL = "internal"  # Built-in plugins
    EXTERNAL = "external"  # User-installed plugins
    REMOTE = "remote"  # Remote plugins (future)


@dataclass(frozen=True)
class PluginManifest:
    """
    Plugin manifest - metadata about the plugin.
    This is typically defined in plugin's __init__.py or manifest.py
    """
    name: str
    version: str
    description: str
    author: str | None = None
    homepage: str | None = None
    license: str | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)
    min_dashboard_version: str | None = None
    dependencies: tuple[str, ...] = field(default_factory=tuple)
    capabilities: tuple[str, ...] = field(default_factory=tuple)
    actions: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    events: tuple[dict[str, Any], ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PluginUIConfig:
    """
    Plugin UI configuration - defines how plugin integrates into dashboard UI.
    This is typically defined in plugin's ui.yaml or ui_config.py
    """
    # Page configuration
    has_page: bool = False
    page_path: str | None = None  # URL path for plugin page (e.g., "/plugins/autodiscover")
    page_title: str | None = None
    page_icon: str | None = None
    
    # Navigation configuration
    show_in_menu: bool = True  # Whether to show in sidebar menu
    menu_group: str | None = None  # Menu group/category
    menu_order: int = 100  # Order in menu (lower = higher priority)
    
    # Widget configuration
    provides_widgets: bool = False
    widgets: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    
    # Static assets
    static_dir: str | None = None  # Relative path to static assets
    css_files: tuple[str, ...] = field(default_factory=tuple)
    js_files: tuple[str, ...] = field(default_factory=tuple)
    
    # API routes
    api_prefix: str | None = None  # Custom API route prefix
    api_routes: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    
    # Permissions
    required_permissions: tuple[str, ...] = field(default_factory=tuple)


@dataclass
class PluginInfo:
    """Complete plugin information combining manifest and runtime state."""
    id: str  # Unique plugin identifier (usually same as package name)
    manifest: PluginManifest
    ui_config: PluginUIConfig | None = None
    state: PluginState = PluginState.DISCOVERED
    scope: PluginScope = PluginScope.EXTERNAL
    path: Path | None = None  # Filesystem path to plugin
    module: Any = None  # Loaded Python module
    error: str | None = None  # Error message if state is ERROR
    loaded_at: Any = None  # datetime when plugin was loaded
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "name": self.manifest.name,
            "version": self.manifest.version,
            "description": self.manifest.description,
            "author": self.manifest.author,
            "homepage": self.manifest.homepage,
            "license": self.manifest.license,
            "tags": list(self.manifest.tags),
            "state": self.state.value,
            "scope": self.scope.value,
            "path": str(self.path) if self.path else None,
            "error": self.error,
            "ui_config": {
                "has_page": self.ui_config.has_page,
                "page_path": self.ui_config.page_path,
                "page_title": self.ui_config.page_title,
                "page_icon": self.ui_config.page_icon,
                "show_in_menu": self.ui_config.show_in_menu,
                "menu_group": self.ui_config.menu_group,
                "menu_order": self.ui_config.menu_order,
                "provides_widgets": self.ui_config.provides_widgets,
                "api_prefix": self.ui_config.api_prefix,
            } if self.ui_config else None,
            "capabilities": list(self.manifest.capabilities),
            "metadata": self.metadata,
        }


__all__ = [
    "PluginInfo",
    "PluginManifest",
    "PluginScope",
    "PluginState",
    "PluginUIConfig",
]
