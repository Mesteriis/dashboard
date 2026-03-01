from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRoute

from .registry import PluginRegistry
from .schemas import PluginInfo, PluginState

logger = logging.getLogger(__name__)


class PluginRouter:
    """
    Dynamic router for plugin pages and APIs.
    Creates routes at runtime based on loaded plugins.
    """
    
    def __init__(
        self,
        registry: PluginRegistry,
        base_path: str = "/plugins",
        api_base_path: str = "/api/v1/plugins",
    ) -> None:
        """
        Initialize plugin router.
        
        Args:
            registry: Plugin registry instance
            base_path: Base path for plugin pages
            api_base_path: Base path for plugin APIs
        """
        self.registry = registry
        self.base_path = base_path.rstrip("/")
        self.api_base_path = api_base_path.rstrip("/")
        
        # Main plugin router (mounted to app)
        self.router = APIRouter(prefix=self.base_path, tags=["plugins"])
        
        # API router for plugin-specific APIs
        self.api_router = APIRouter(prefix=self.api_base_path, tags=["plugins-api"])
        
        # Track mounted plugin routes
        self._mounted_plugins: set[str] = set()
        self._plugin_mount_meta: dict[str, dict[str, str]] = {}
        
        # Setup base routes
        self._setup_base_routes()
    
    def _setup_base_routes(self) -> None:
        """Setup base plugin management routes."""
        
        @self.api_router.get("")
        async def list_plugins() -> dict[str, Any]:
            """List all plugins."""
            return self.registry.to_dict()
        
        @self.api_router.get("/{plugin_id}")
        async def get_plugin(plugin_id: str) -> dict[str, Any]:
            """Get plugin details."""
            plugin = self.registry.get_plugin(plugin_id)
            if plugin is None:
                return {"error": "Plugin not found", "plugin_id": plugin_id}
            return plugin.to_dict()
        
        @self.api_router.post("/{plugin_id}/load")
        async def load_plugin(plugin_id: str) -> dict[str, Any]:
            """Load a plugin."""
            try:
                plugin = self.registry.load_plugin(plugin_id)
                self._mount_plugin_routes(plugin)
                return {"status": "loaded", "plugin": plugin.to_dict()}
            except ValueError as exc:
                return {"error": str(exc), "status": "failed"}
            except Exception as exc:
                return {"error": f"Failed to load plugin: {exc}", "status": "failed"}
        
        @self.api_router.post("/{plugin_id}/unload")
        async def unload_plugin(plugin_id: str) -> dict[str, Any]:
            """Unload a plugin."""
            success = self.registry.unload_plugin(plugin_id)
            if success:
                self._unmount_plugin_routes(plugin_id)
                return {"status": "unloaded", "plugin_id": plugin_id}
            return {"error": "Failed to unload plugin", "plugin_id": plugin_id}
        
        @self.api_router.post("/{plugin_id}/reload")
        async def reload_plugin(plugin_id: str) -> dict[str, Any]:
            """Reload a plugin."""
            try:
                plugin = self.registry.reload_plugin(plugin_id)
                return {"status": "reloaded", "plugin": plugin.to_dict()}
            except Exception as exc:
                return {"error": f"Failed to reload plugin: {exc}", "status": "failed"}
        
        @self.api_router.post("/{plugin_id}/enable")
        async def enable_plugin(plugin_id: str) -> dict[str, Any]:
            """Enable a plugin."""
            try:
                plugin = self.registry.enable_plugin(plugin_id)
                self._mount_plugin_routes(plugin)
                return {"status": "enabled", "plugin": plugin.to_dict()}
            except Exception as exc:
                return {"error": f"Failed to enable plugin: {exc}", "status": "failed"}
        
        @self.api_router.post("/{plugin_id}/disable")
        async def disable_plugin(plugin_id: str) -> dict[str, Any]:
            """Disable a plugin."""
            success = self.registry.disable_plugin(plugin_id)
            if success:
                self._unmount_plugin_routes(plugin_id)
                return {"status": "disabled", "plugin_id": plugin_id}
            return {"error": "Failed to disable plugin", "plugin_id": plugin_id}
    
    def _mount_plugin_routes(self, plugin: PluginInfo) -> None:
        """Mount routes for a specific plugin."""
        if plugin.id in self._mounted_plugins:
            logger.debug(f"Plugin {plugin.id} routes already mounted")
            return
        
        if plugin.state != PluginState.ACTIVE:
            logger.debug(f"Cannot mount routes for inactive plugin {plugin.id}")
            return
        
        ui_config = plugin.ui_config
        if ui_config is None:
            logger.debug(f"No UI config for plugin {plugin.id}, skipping route mounting")
            return

        page_route = ""
        api_prefix = ""
        
        # Mount plugin page route if has_page is True
        if ui_config.has_page and ui_config.page_path:
            page_route = ui_config.page_path.lstrip("/")
            self._mount_plugin_page(plugin)
        
        # Mount plugin API routes if defined
        if ui_config.api_prefix or ui_config.api_routes:
            api_prefix = (ui_config.api_prefix or plugin.id).strip("/")
            self._mount_plugin_api_routes(plugin)
        
        # Mount static files if defined
        if ui_config.static_dir and plugin.path:
            self._mount_plugin_static(plugin)
        
        self._mounted_plugins.add(plugin.id)
        self._plugin_mount_meta[plugin.id] = {
            "page_route": page_route,
            "api_prefix": api_prefix,
        }
        logger.info(f"Mounted routes for plugin: {plugin.id}")
    
    def _unmount_plugin_routes(self, plugin_id: str) -> None:
        """Unmount routes for a specific plugin."""
        meta = self._plugin_mount_meta.pop(plugin_id, {})
        page_route = meta.get("page_route", "").strip("/")
        api_prefix = meta.get("api_prefix", "").strip("/")

        if page_route:
            self._remove_route_path(self.router, f"{self.base_path}/{page_route}")

        if api_prefix:
            self._remove_route_prefix(self.api_router, f"{self.api_base_path}/{api_prefix}")

        if plugin_id in self._mounted_plugins:
            self._mounted_plugins.remove(plugin_id)
            logger.info(f"Unmounted routes for plugin: {plugin_id}")

    def _remove_route_path(self, router: APIRouter, path: str) -> None:
        normalized = path.rstrip("/")
        if not normalized:
            normalized = "/"
        routes = [
            route
            for route in router.routes
            if not isinstance(route, APIRoute)
            or (route.path.rstrip("/") or "/") != normalized
        ]
        router.routes[:] = routes

    def _remove_route_prefix(self, router: APIRouter, path_prefix: str) -> None:
        normalized = path_prefix.rstrip("/")
        routes = [
            route
            for route in router.routes
            if not isinstance(route, APIRoute)
            or not (route.path.rstrip("/") or "/").startswith(normalized)
        ]
        router.routes[:] = routes
    
    def _mount_plugin_page(self, plugin: PluginInfo) -> None:
        """Mount plugin page route."""
        ui_config = plugin.ui_config
        if not ui_config or not ui_config.page_path:
            return
        
        # Create route for plugin page
        # The page_path should be relative to base_path
        page_route = ui_config.page_path.lstrip("/")
        plugin_id = plugin.id

        @self.router.get(f"/{page_route}", response_class=HTMLResponse)
        async def plugin_page_handler(request: Request) -> HTMLResponse:
            current = self.registry.get_plugin(plugin_id)
            if current is None:
                return HTMLResponse(
                    content="<h1>Plugin not found</h1>",
                    status_code=404,
                )

            try:
                if current.module and hasattr(current.module, "handle_page"):
                    result = current.module.handle_page(request)
                    if hasattr(result, "__await__"):
                        result = await result
                    if isinstance(result, str):
                        return HTMLResponse(content=result)
                    if isinstance(result, dict):
                        return HTMLResponse(
                            content=result.get("html", ""),
                            status_code=result.get("status_code", 200),
                        )
                    return HTMLResponse(content=str(result))

                return HTMLResponse(content=self._render_plugin_page(current, request))
            except Exception as exc:
                logger.exception("Plugin page handler failed for %s: %s", plugin_id, exc)
                return HTMLResponse(
                    content=f"<h1>Error</h1><p>Failed to load plugin page: {exc}</p>",
                    status_code=500,
                )
    
    def _render_plugin_page(self, plugin: PluginInfo, request: Request) -> str:
        """Render default plugin page."""
        ui_config = plugin.ui_config
        title = ui_config.page_title if ui_config else plugin.manifest.name
        icon = ui_config.page_icon if ui_config else "🔌"
        
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - {plugin.manifest.name}</title>
    <style>
        :root {{
            --bg-primary: #050a0f;
            --bg-card: rgba(255,255,255,0.04);
            --border: rgba(255,255,255,0.08);
            --text-primary: #ffffff;
            --text-secondary: rgba(255,255,255,0.7);
            --accent: #2dd4bf;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 2rem; }}
        .header {{
            display: flex;
            align-items: center;
            gap: 1rem;
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border);
        }}
        .icon {{ font-size: 2.5rem; }}
        .title {{ font-size: 2rem; font-weight: 600; }}
        .version {{
            background: var(--bg-card);
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.875rem;
            color: var(--text-secondary);
        }}
        .card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-top: 1rem;
        }}
        .info-item {{
            padding: 0.75rem;
            background: rgba(255,255,255,0.02);
            border-radius: 8px;
        }}
        .info-label {{
            font-size: 0.75rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .info-value {{
            font-size: 1rem;
            margin-top: 0.25rem;
        }}
        .status {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            border-radius: 8px;
            font-weight: 500;
        }}
        .status-active {{ background: rgba(45, 212, 191, 0.1); color: var(--accent); }}
        .status-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: currentColor;
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        .content {{ margin-top: 2rem; }}
        .tags {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-top: 1rem;
        }}
        .tag {{
            background: var(--bg-card);
            padding: 0.25rem 0.75rem;
            border-radius: 6px;
            font-size: 0.875rem;
            color: var(--text-secondary);
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <span class="icon">{icon}</span>
            <div>
                <h1 class="title">{title}</h1>
                <span class="version">v{plugin.manifest.version}</span>
            </div>
        </div>
        
        <div class="card">
            <div class="status status-active">
                <span class="status-dot"></span>
                Active
            </div>
            
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">Plugin ID</div>
                    <div class="info-value">{plugin.id}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Description</div>
                    <div class="info-value">{plugin.manifest.description}</div>
                </div>
                {f'<div class="info-item"><div class="info-label">Author</div><div class="info-value">{plugin.manifest.author or "N/A"}</div></div>' if plugin.manifest.author else ''}
                {f'<div class="info-item"><div class="info-label">License</div><div class="info-value">{plugin.manifest.license or "N/A"}</div></div>' if plugin.manifest.license else ''}
            </div>
            
            {f'''
            <div class="tags">
                {''.join(f'<span class="tag">{tag}</span>' for tag in plugin.manifest.tags)}
            </div>
            ''' if plugin.manifest.tags else ''}
        </div>
        
        <div class="content">
            <div class="card">
                <h2 style="margin-bottom: 1rem;">Plugin Capabilities</h2>
                {self._render_capabilities(plugin)}
            </div>
        </div>
    </div>
</body>
</html>
"""
    
    def _render_capabilities(self, plugin: PluginInfo) -> str:
        """Render plugin capabilities section."""
        capabilities = plugin.manifest.capabilities
        if not capabilities:
            return "<p style='color: var(--text-secondary);'>No capabilities registered</p>"
        
        items = "".join(f"<li>{cap}</li>" for cap in capabilities)
        return f"<ul style='list-style: disc; padding-left: 1.5rem;'>{items}</ul>"
    
    def _mount_plugin_api_routes(self, plugin: PluginInfo) -> None:
        """Mount plugin-specific API routes."""
        ui_config = plugin.ui_config
        if not ui_config:
            return
        
        # If plugin module has API router, include it
        if plugin.module and hasattr(plugin.module, "api_router"):
            plugin_api_router = plugin.module.api_router
            if isinstance(plugin_api_router, APIRouter):
                api_prefix = ui_config.api_prefix or plugin.id
                self.api_router.include_router(
                    plugin_api_router,
                    prefix=f"/{api_prefix}",
                )
                logger.info(f"Mounted API routes for plugin {plugin.id} at /{api_prefix}")
    
    def _mount_plugin_static(self, plugin: PluginInfo) -> None:
        """Mount plugin static files."""
        # This would be implemented with FastAPI's StaticFiles
        # For now, just log that static files are available
        ui_config = plugin.ui_config
        if not ui_config or not plugin.path:
            return
        
        static_dir = plugin.path / ui_config.static_dir
        if static_dir.exists():
            logger.info(f"Plugin {plugin.id} static files available at {static_dir}")
    
    def mount_all_active(self) -> None:
        """Mount routes for all active plugins."""
        for plugin in self.registry.list_active():
            self._mount_plugin_routes(plugin)
    
    def get_router(self) -> APIRouter:
        """Get the main plugin router."""
        return self.router
    
    def get_api_router(self) -> APIRouter:
        """Get the plugin API router."""
        return self.api_router


__all__ = ["PluginRouter"]
