"""Plugin storage service for managing plugin lifecycle."""

import hashlib
import json
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from store.schemas import PluginInfo, PluginManifest, PluginSource

logger = structlog.get_logger(__name__)
HARDCODED_STORAGE_PATH = Path(__file__).resolve().parents[2] / "store" / "plugins"


class PluginStorageService:
    """Service for managing plugin storage and lifecycle."""

    def __init__(self):
        self.storage_path = HARDCODED_STORAGE_PATH
        self.metadata_file = self.storage_path / "plugins.json"
        self._plugins: dict[str, PluginInfo] = {}
        self._ensure_storage_exists()
        self._load_metadata()
        self._sync_local_plugins()

    def _ensure_storage_exists(self) -> None:
        """Ensure storage directory exists."""
        self.storage_path.mkdir(parents=True, exist_ok=True)
        (self.storage_path / "uploads").mkdir(exist_ok=True)

    def _load_metadata(self) -> None:
        """Load plugin metadata from disk."""
        if self.metadata_file.exists():
            try:
                data = json.loads(self.metadata_file.read_text())
                for plugin_id, plugin_data in data.items():
                    self._plugins[plugin_id] = PluginInfo(**plugin_data)
                logger.info("Loaded plugin metadata", count=len(self._plugins))
            except Exception as e:
                logger.error("Failed to load plugin metadata", error=str(e))
                self._plugins = {}

    def _sync_local_plugins(self) -> None:
        """
        Discover plugin folders placed directly in storage path.

        This keeps catalog usable even when plugins.json is absent/stale.
        """
        discovered = 0
        for entry in self.storage_path.iterdir():
            if not entry.is_dir():
                continue
            if entry.name.startswith((".", "_")):
                continue
            if entry.name == "uploads":
                continue

            manifest_path = self._find_manifest(entry)
            if not manifest_path:
                continue

            manifest = self._parse_manifest(manifest_path)
            plugin_id = entry.name
            now = datetime.now()

            existing = self._plugins.get(plugin_id)
            plugin_info = PluginInfo(
                id=plugin_id,
                name=(manifest.name if manifest else plugin_id) or plugin_id,
                version=(manifest.version if manifest else "0.0.0") or "0.0.0",
                description=manifest.description if manifest else None,
                author=manifest.author if manifest else None,
                source=PluginSource.LOCAL,
                source_url=str(entry),
                manifest=manifest,
                created_at=existing.created_at if existing else now,
                updated_at=now,
                metadata={
                    **(existing.metadata if existing else {}),
                    "local_path": str(entry),
                },
            )
            self._plugins[plugin_id] = plugin_info
            discovered += 1

        if discovered:
            logger.info("Discovered local plugins from storage path", count=discovered)
            self._save_metadata()

    def _save_metadata(self) -> None:
        """Save plugin metadata to disk."""
        try:
            data = {
                plugin_id: plugin.model_dump(mode="json")
                for plugin_id, plugin in self._plugins.items()
            }
            self.metadata_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error("Failed to save plugin metadata", error=str(e))

    def _generate_plugin_id(self, name: str, version: str) -> str:
        """Generate unique plugin ID."""
        unique_str = f"{name}:{version}:{datetime.now().isoformat()}"
        return hashlib.sha256(unique_str.encode()).hexdigest()[:16]

    def _extract_zip(self, zip_path: Path, extract_to: Path) -> None:
        """Extract ZIP file to destination."""
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_to)

    def _find_manifest(self, plugin_dir: Path) -> Path | None:
        """Find manifest.py in plugin directory."""
        # Check root
        manifest = plugin_dir / "manifest.py"
        if manifest.exists():
            return manifest

        # Check subdirectories (in case ZIP contains folder)
        for subdir in plugin_dir.iterdir():
            if subdir.is_dir():
                sub_manifest = subdir / "manifest.py"
                if sub_manifest.exists():
                    return sub_manifest

        return None

    def _parse_manifest(self, manifest_path: Path) -> PluginManifest | None:
        """Parse manifest.py file."""
        try:
            # Read manifest as text and extract variables
            content = manifest_path.read_text()
            manifest_vars: dict[str, Any] = {}

            # Simple parsing of manifest variables
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue

                # Parse variable assignments
                parts = line.split("=", 1)
                if len(parts) == 2:
                    var_name = parts[0].strip()
                    var_value = parts[1].strip()

                    # Remove quotes
                    if var_value.startswith(("'", '"')) and var_value.endswith(
                        ("'", '"')
                    ):
                        var_value = var_value[1:-1]
                    # Parse tuples
                    elif var_value.startswith("(") and var_value.endswith(")"):
                        items = var_value[1:-1].split(",")
                        var_value = tuple(
                            item.strip().strip("'\"") for item in items if item.strip()
                        )

                    manifest_vars[var_name] = var_value

            return PluginManifest(
                name=manifest_vars.get("PLUGIN_NAME", "unknown"),
                version=manifest_vars.get("PLUGIN_VERSION", "0.0.0"),
                description=manifest_vars.get("PLUGIN_DESCRIPTION"),
                author=manifest_vars.get("PLUGIN_AUTHOR"),
                homepage=manifest_vars.get("PLUGIN_HOMEPAGE"),
                license=manifest_vars.get("PLUGIN_LICENSE"),
                tags=manifest_vars.get("PLUGIN_TAGS"),
                capabilities=manifest_vars.get("PLUGIN_CAPABILITIES"),
            )
        except Exception as e:
            logger.error("Failed to parse manifest", error=str(e))
            return None

    def _validate_plugin(self, plugin_dir: Path) -> tuple[bool, str | None]:
        """Validate plugin structure."""
        # Check for manifest
        manifest = self._find_manifest(plugin_dir)
        if not manifest:
            return False, "manifest.py not found"

        # Parse manifest
        manifest_data = self._parse_manifest(manifest)
        if not manifest_data:
            return False, "Failed to parse manifest.py"

        if not manifest_data.name or manifest_data.name == "unknown":
            return False, "PLUGIN_NAME is required in manifest"

        return True, None

    def store_plugin_from_zip(
        self, zip_path: Path, plugin_name: str | None = None
    ) -> PluginInfo:
        """Store plugin from uploaded ZIP file."""
        plugin_id = f"zip_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        upload_dir = self.storage_path / "uploads" / plugin_id
        upload_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Copy ZIP to storage
            dest_zip = upload_dir / "plugin.zip"
            shutil.copy2(zip_path, dest_zip)

            # Extract
            extract_dir = upload_dir / "extracted"
            extract_dir.mkdir(exist_ok=True)
            self._extract_zip(dest_zip, extract_dir)

            # Find actual plugin directory
            plugin_dir = extract_dir
            if len(list(extract_dir.iterdir())) == 1:
                single_item = next(extract_dir.iterdir())
                if single_item.is_dir() and single_item.name != "__pycache__":
                    plugin_dir = single_item

            # Validate
            is_valid, error_msg = self._validate_plugin(plugin_dir)
            if not is_valid:
                raise ValueError(error_msg or "Plugin validation failed")

            # Parse manifest
            manifest_path = self._find_manifest(plugin_dir)
            manifest = self._parse_manifest(manifest_path) if manifest_path else None

            # Create plugin info
            now = datetime.now()
            plugin_info = PluginInfo(
                id=plugin_id,
                name=manifest.name if manifest else plugin_name or "unknown",
                version=manifest.version if manifest else "0.0.0",
                description=manifest.description if manifest else None,
                author=manifest.author if manifest else None,
                source=PluginSource.ZIP_UPLOAD,
                source_url=str(dest_zip),
                manifest=manifest,
                created_at=now,
                updated_at=now,
                metadata={"extract_path": str(extract_dir)},
            )

            self._plugins[plugin_id] = plugin_info
            self._save_metadata()

            logger.info("Stored plugin from ZIP", plugin_id=plugin_id, name=plugin_info.name)
            return plugin_info

        except Exception as e:
            logger.error("Failed to store plugin from ZIP", error=str(e))
            # Cleanup on failure
            if upload_dir.exists():
                shutil.rmtree(upload_dir)
            raise

    def store_plugin_from_github(
        self, repo_url: str, branch: str = "main", subdirectory: str | None = None
    ) -> PluginInfo:
        """Store plugin from GitHub repository."""
        import re

        # Parse GitHub URL
        match = re.search(r"github\.com[:/]([^/]+)/([^/]+)", repo_url)
        if not match:
            raise ValueError("Invalid GitHub URL")

        owner, repo = match.groups()
        repo_name = repo.replace(".git", "")
        plugin_id = f"github_{owner}_{repo_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        download_dir = self.storage_path / "uploads" / plugin_id
        download_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Download ZIP from GitHub
            zip_url = f"https://github.com/{owner}/{repo_name}/archive/{branch}.zip"
            import httpx

            zip_path = download_dir / "plugin.zip"
            with httpx.Client() as client:
                response = client.get(zip_url, follow_redirects=True)
                response.raise_for_status()
                zip_path.write_bytes(response.content)

            # Extract
            extract_dir = download_dir / "extracted"
            extract_dir.mkdir(exist_ok=True)
            self._extract_zip(zip_path, extract_dir)

            # Handle subdirectory if specified
            plugin_dir = extract_dir
            if len(list(extract_dir.iterdir())) == 1:
                single_item = next(extract_dir.iterdir())
                if single_item.is_dir() and single_item.name != "__pycache__":
                    plugin_dir = single_item

            # Navigate to subdirectory if specified
            if subdirectory:
                plugin_dir = plugin_dir / subdirectory
                if not plugin_dir.exists():
                    raise ValueError(f"Subdirectory '{subdirectory}' not found in repository")

            # Validate
            is_valid, error_msg = self._validate_plugin(plugin_dir)
            if not is_valid:
                raise ValueError(error_msg or "Plugin validation failed")

            # Parse manifest
            manifest_path = self._find_manifest(plugin_dir)
            manifest = self._parse_manifest(manifest_path) if manifest_path else None

            # Create plugin info
            now = datetime.now()
            plugin_info = PluginInfo(
                id=plugin_id,
                name=manifest.name if manifest else repo_name,
                version=manifest.version if manifest else "0.0.0",
                description=manifest.description if manifest else None,
                author=manifest.author if manifest else None,
                source=PluginSource.GITHUB,
                source_url=repo_url,
                manifest=manifest,
                created_at=now,
                updated_at=now,
                metadata={
                    "extract_path": str(extract_dir),
                    "github_owner": owner,
                    "github_repo": repo_name,
                    "branch": branch,
                    "subdirectory": subdirectory,
                },
            )

            self._plugins[plugin_id] = plugin_info
            self._save_metadata()

            logger.info(
                "Stored plugin from GitHub",
                plugin_id=plugin_id,
                name=plugin_info.name,
                repo=f"{owner}/{repo_name}",
            )
            return plugin_info

        except Exception as e:
            logger.error("Failed to store plugin from GitHub", error=str(e))
            # Cleanup on failure
            if download_dir.exists():
                shutil.rmtree(download_dir)
            raise

    def get_plugin(self, plugin_id: str) -> PluginInfo | None:
        """Get plugin by ID."""
        return self._plugins.get(plugin_id)

    def list_plugins(self) -> list[PluginInfo]:
        """List all plugins available in catalog."""
        return list(self._plugins.values())

    def delete_plugin(self, plugin_id: str) -> bool:
        """Delete plugin and cleanup resources."""
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return False

        try:
            # Remove from memory
            del self._plugins[plugin_id]

            # Cleanup files if source is upload
            if plugin.source in (PluginSource.ZIP_UPLOAD, PluginSource.GITHUB):
                upload_dir = self.storage_path / "uploads" / plugin_id
                if upload_dir.exists():
                    shutil.rmtree(upload_dir)

            self._save_metadata()
            logger.info("Deleted plugin", plugin_id=plugin_id)
            return True

        except Exception as e:
            logger.error("Failed to delete plugin", plugin_id=plugin_id, error=str(e))
            return False

    def get_plugin_path(self, plugin_id: str) -> Path | None:
        """Get path to plugin files."""
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return None

        if plugin.metadata and "extract_path" in plugin.metadata:
            return Path(plugin.metadata["extract_path"])
        if plugin.metadata and "local_path" in plugin.metadata:
            return Path(plugin.metadata["local_path"])
        local_dir = self.storage_path / plugin_id
        if local_dir.exists() and local_dir.is_dir():
            return local_dir

        return None

    def get_health(self) -> dict[str, Any]:
        """Get storage health status."""
        return {
            "status": "healthy",
            "storage_path": str(self.storage_path),
            "storage_exists": self.storage_path.exists(),
            "plugins_count": len(self._plugins),
        }


# Singleton instance
plugin_storage = PluginStorageService()
