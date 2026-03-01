from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class PluginSource(str, Enum):
    """Plugin source type enumeration."""

    ZIP_UPLOAD = "zip_upload"
    GITHUB = "github"
    LOCAL = "local"


# Request Schemas
class PluginUploadZipRequest(BaseModel):
    """Request schema for ZIP upload."""

    pass


class PluginUploadGitHubRequest(BaseModel):
    """Request schema for GitHub repository upload."""

    repo_url: HttpUrl = Field(..., description="GitHub repository URL")
    branch: str = Field(default="main", description="Branch name")
    subdirectory: str | None = Field(default=None, description="Subdirectory within repo")


# Response Schemas
class PluginManifest(BaseModel):
    """Plugin manifest schema."""

    name: str = Field(..., description="Plugin name")
    version: str = Field(..., description="Plugin version")
    description: str | None = Field(default=None, description="Plugin description")
    author: str | None = Field(default=None, description="Plugin author")
    homepage: str | None = Field(default=None, description="Plugin homepage URL")
    license: str | None = Field(default=None, description="Plugin license")
    tags: tuple[str, ...] | None = Field(default=None, description="Plugin tags")
    capabilities: tuple[str, ...] | None = Field(
        default=None, description="Plugin capabilities"
    )


class PluginInfo(BaseModel):
    """Plugin information schema."""

    id: str = Field(..., description="Plugin ID")
    name: str = Field(..., description="Plugin name")
    version: str = Field(..., description="Plugin version")
    description: str | None = Field(default=None, description="Plugin description")
    author: str | None = Field(default=None, description="Plugin author")
    source: PluginSource = Field(..., description="Plugin source type")
    source_url: str | None = Field(default=None, description="Source URL or path")
    manifest: PluginManifest | None = Field(default=None, description="Plugin manifest")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class PluginListResponse(BaseModel):
    """Response schema for plugin list."""

    plugins: list[PluginInfo] = Field(..., description="List of plugins")
    total: int = Field(..., description="Total number of plugins")


class PluginUploadResponse(BaseModel):
    """Response schema for plugin upload."""

    success: bool = Field(..., description="Upload success status")
    plugin_id: str | None = Field(default=None, description="Plugin ID if successful")
    message: str = Field(..., description="Response message")
    plugin: PluginInfo | None = Field(default=None, description="Plugin info if successful")


class PluginActionResponse(BaseModel):
    """Response schema for catalog actions (e.g. delete)."""

    success: bool = Field(..., description="Action success status")
    message: str = Field(..., description="Response message")
    plugin: PluginInfo | None = Field(default=None, description="Plugin info after action")


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(..., description="Health status")
    version: str = Field(..., description="Application version")
    storage_path: str = Field(..., description="Storage path")
    plugins_count: int = Field(..., description="Number of plugins")


class ErrorResponse(BaseModel):
    """Error response schema."""

    success: bool = Field(default=False, description="Always False for errors")
    error: str = Field(..., description="Error message")
    detail: str | None = Field(default=None, description="Detailed error information")
