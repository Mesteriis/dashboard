"""Plugin Store client for syncing and installing plugins."""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

import httpx

from core.plugins.schemas import PluginInfo, PluginManifest, PluginScope, PluginState

logger = logging.getLogger(__name__)


@dataclass
class StorePlugin:
    """Plugin information from store."""
    id: str
    name: str
    version: str
    description: str | None = None
    author: str | None = None
    source: str = "zip_upload"
    manifest: dict | None = None


@dataclass
class StoreClient:
    """Client for interacting with plugin store service."""
    store_url: str
    timeout: float = 30.0

    @classmethod
    def create(cls, store_url: str, timeout: float = 30.0) -> StoreClient:
        """Create store client."""
        # Remove trailing /api/v1 if present
        base_url = store_url.rstrip("/")
        if base_url.endswith("/api/v1"):
            base_url = base_url[:-7]
        return cls(store_url=base_url, timeout=timeout)

    async def sync_plugins(self) -> list[StorePlugin]:
        """Sync plugin list from store."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(f"{self.store_url}/api/v1/rpc/plugins")
                response.raise_for_status()
                data = response.json()

                return [
                    StorePlugin(
                        id=p["id"],
                        name=p["name"],
                        version=p["version"],
                        description=p.get("description"),
                        author=p.get("author"),
                        source=p.get("source", "zip_upload"),
                        manifest=p.get("manifest"),
                    )
                    for p in data.get("plugins", [])
                ]
            except httpx.HTTPError as e:
                logger.error(f"Failed to sync plugins from store: {e}")
                return []
            except Exception as e:
                logger.error(f"Unexpected error syncing plugins: {e}")
                return []

    async def get_plugin_manifest(self, plugin_id: str) -> dict | None:
        """Get plugin manifest from store."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(f"{self.store_url}/api/v1/rpc/plugins/{plugin_id}/manifest")
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Failed to get plugin manifest: {e}")
                return None

    async def download_plugin(self, plugin_id: str) -> str | None:
        """
        Download plugin from store.
        Returns path to plugin files.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.store_url}/api/v1/rpc/plugins/download",
                    json={"plugin_id": plugin_id},
                )
                response.raise_for_status()
                data = response.json()
                return data.get("plugin_path")
            except httpx.HTTPError as e:
                logger.error(f"Failed to download plugin: {e}")
                return None

    async def health_check(self) -> bool:
        """Check if store is available."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(f"{self.store_url}/api/v1/rpc/health")
                return response.status_code == 200
            except httpx.HTTPError:
                return False


@dataclass
class PluginInstaller:
    """Service for installing plugins from store to local directory."""
    install_dir: Path
    store_client: StoreClient

    @classmethod
    def create(cls, install_dir: Path, store_url: str) -> PluginInstaller:
        """Create plugin installer."""
        store_client = StoreClient.create(store_url=store_url)
        return cls(install_dir=install_dir, store_client=store_client)

    def _resolve_plugin_root(self, source_path: Path, expected_name: str) -> Path | None:
        """
        Resolve plugin package root inside downloaded directory.
        Supports both flat archives and archives with an extra top-level folder.
        """
        expected = expected_name.strip()
        candidates: list[Path] = []
        if expected:
            candidates.append(source_path / expected)
        candidates.append(source_path)
        candidates.extend([entry for entry in source_path.iterdir() if entry.is_dir()])

        for candidate in candidates:
            if not candidate.exists() or not candidate.is_dir():
                continue
            if (candidate / "__init__.py").exists() and (candidate / "manifest.py").exists():
                return candidate

        for candidate in source_path.rglob("*"):
            if not candidate.is_dir():
                continue
            if (candidate / "__init__.py").exists() and (candidate / "manifest.py").exists():
                return candidate

        return None

    async def install_plugin(self, plugin_id: str) -> PluginInfo | None:
        """
        Install plugin from store to local directory.
        
        Args:
            plugin_id: Plugin ID in store
            
        Returns:
            PluginInfo if successful, None otherwise
        """
        # Get plugin manifest
        manifest_data = await self.store_client.get_plugin_manifest(plugin_id)
        if not manifest_data:
            logger.error(f"Failed to get manifest for plugin {plugin_id}")
            return None

        # Download plugin
        plugin_path = await self.store_client.download_plugin(plugin_id)
        if not plugin_path:
            logger.error(f"Failed to download plugin {plugin_id}")
            return None

        source_path = Path(plugin_path)
        if not source_path.exists():
            logger.error(f"Plugin path does not exist: {plugin_path}")
            return None

        plugin_name = str(manifest_data.get("name", plugin_id) or plugin_id).strip()
        plugin_root = self._resolve_plugin_root(source_path=source_path, expected_name=plugin_name)
        if plugin_root is None:
            logger.error("Failed to locate plugin root inside downloaded path: %s", source_path)
            return None

        # Create install directory
        self.install_dir.mkdir(parents=True, exist_ok=True)

        # Install to local directory
        dest_path = self.install_dir / plugin_name
        if dest_path.exists():
            shutil.rmtree(dest_path)

        shutil.copytree(plugin_root, dest_path)
        logger.info(f"Installed plugin {plugin_name} to {dest_path}")

        # Create PluginInfo
        manifest = PluginManifest(
            name=plugin_name or "unknown",
            version=manifest_data.get("version", "0.0.0"),
            description=manifest_data.get("description"),
            author=manifest_data.get("author"),
            homepage=manifest_data.get("homepage"),
            license=manifest_data.get("license"),
            tags=tuple(manifest_data.get("tags", [])),
            capabilities=tuple(manifest_data.get("capabilities", [])),
        )

        return PluginInfo(
            id=manifest.name,
            manifest=manifest,
            ui_config=None,  # Will be loaded by plugin loader
            state=PluginState.DISCOVERED,
            scope=PluginScope.EXTERNAL,
            path=dest_path,
        )

    async def uninstall_plugin(self, plugin_id: str) -> bool:
        """
        Uninstall plugin from local directory.
        
        Args:
            plugin_id: Plugin ID (also used as directory name)
            
        Returns:
            True if successful
        """
        plugin_path = self.install_dir / plugin_id
        if not plugin_path.exists():
            logger.warning(f"Plugin not found: {plugin_path}")
            return False

        shutil.rmtree(plugin_path)
        logger.info(f"Uninstalled plugin {plugin_id}")
        return True

    async def list_installed_plugins(self) -> list[Path]:
        """List installed plugin directories."""
        if not self.install_dir.exists():
            return []
        return [d for d in self.install_dir.iterdir() if d.is_dir()]

__all__ = ["PluginInstaller", "StoreClient", "StorePlugin"]
