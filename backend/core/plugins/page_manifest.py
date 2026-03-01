from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, ValidationError

SUPPORTED_MANIFEST_MAJOR = 1
SUPPORTED_PLUGIN_API_MAJOR = 1
MANIFEST_CANDIDATES = (
    "page_manifest.yaml",
    "page_manifest.yml",
    "frontend_manifest.yaml",
    "frontend_manifest.yml",
)


class PluginDataSourceV1(BaseModel):
    type: Literal["http"] = "http"
    endpoint: str
    method: Literal["GET", "POST"] = "GET"
    capability: str | None = None
    response_path: str | None = None
    body: dict[str, Any] | None = None


class PluginDataTableColumnV1(BaseModel):
    key: str
    label: str


class PluginDataTableGroupByLevelV1(BaseModel):
    field: str
    label: str | None = None
    empty_label: str = Field(default="Unknown", alias="emptyLabel")

    model_config = {
        "populate_by_name": True,
    }


class PluginRowActionAddToDashboardV1(BaseModel):
    id: str
    type: Literal["add-to-dashboard"] = "add-to-dashboard"
    label: str = "Add to Dashboard"
    capability: str | None = None
    target_group_id: str = Field(default="autodiscover", alias="targetGroupId")
    target_group_title: str = Field(default="Autodiscover", alias="targetGroupTitle")
    target_page_id: str | None = Field(default=None, alias="targetPageId")
    subgroup_field: str = Field(default="host_ip", alias="subgroupField")
    url_field: str = Field(default="url", alias="urlField")
    title_field: str | None = Field(default=None, alias="titleField")
    title_template: str | None = Field(default=None, alias="titleTemplate")
    tags_from_fields: list[str] = Field(
        default_factory=lambda: ["host_ip", "service", "port"],
        alias="tagsFromFields",
    )
    open_mode: Literal["new_tab", "same_tab"] = Field(default="new_tab", alias="openMode")

    model_config = {
        "populate_by_name": True,
    }


class PluginPageComponentBaseV1(BaseModel):
    id: str
    type: str
    title: str | None = None


class PluginTextComponentV1(PluginPageComponentBaseV1):
    type: Literal["text"] = "text"
    text: str


class PluginDataTableComponentV1(PluginPageComponentBaseV1):
    type: Literal["data-table"] = "data-table"
    columns: list[PluginDataTableColumnV1] = Field(default_factory=list)
    group_by: list[PluginDataTableGroupByLevelV1] = Field(
        default_factory=list,
        alias="groupBy",
    )
    data_source: PluginDataSourceV1 = Field(alias="dataSource")
    row_actions: list[PluginRowActionAddToDashboardV1] = Field(default_factory=list, alias="rowActions")
    loading_text: str = Field(default="Loading...", alias="loadingText")
    empty_text: str = Field(default="No data", alias="emptyText")
    error_text: str = Field(default="Failed to load data", alias="errorText")

    model_config = {
        "populate_by_name": True,
    }


class PluginPageV1(BaseModel):
    enabled: bool = False
    layout: Literal["content-only", "with-sidebar", "dashboard", "split-view"] = "content-only"
    components: list[PluginTextComponentV1 | PluginDataTableComponentV1] = Field(default_factory=list)


class PluginCustomBundleV1(BaseModel):
    enabled: bool = False
    entry: str | None = None
    integrity: str | None = None
    sandbox: bool = True
    kill_switch_key: str = Field(default="oko:plugins:bundle:disabled", alias="killSwitchKey")

    model_config = {
        "populate_by_name": True,
    }


class PluginFrontendV1(BaseModel):
    renderer: Literal["universal", "custom"] = "universal"
    sandbox: bool = True
    custom_bundle: PluginCustomBundleV1 = Field(default_factory=PluginCustomBundleV1, alias="customBundle")

    model_config = {
        "populate_by_name": True,
    }


class PluginPageManifestV1(BaseModel):
    plugin_id: str
    version: str
    manifest_version: str = "1.0"
    plugin_api_version: str = "1.0"
    capabilities: list[str] = Field(default_factory=list)
    frontend: PluginFrontendV1 = Field(default_factory=PluginFrontendV1)
    page: PluginPageV1 = Field(default_factory=PluginPageV1)
    schema: dict[str, Any] = Field(default_factory=dict)


@dataclass(frozen=True)
class ManifestResolution:
    manifest: PluginPageManifestV1
    accepted: bool
    fallback_used: bool
    reason: str | None = None
    errors: tuple[str, ...] = ()


def _parse_major(version: str) -> int:
    token = str(version or "").strip()
    if not token:
        return 0
    chunk = token.split(".", 1)[0]
    try:
        return int(chunk)
    except ValueError:
        return 0


def _fallback_manifest(
    plugin_id: str,
    plugin_version: str,
) -> PluginPageManifestV1:
    return PluginPageManifestV1(
        plugin_id=plugin_id,
        version=plugin_version or "0.0.0",
        manifest_version=f"{SUPPORTED_MANIFEST_MAJOR}.0",
        plugin_api_version=f"{SUPPORTED_PLUGIN_API_MAJOR}.0",
        capabilities=[],
        frontend=PluginFrontendV1(
            renderer="universal",
            sandbox=True,
            customBundle=PluginCustomBundleV1(enabled=False, sandbox=True).model_dump(by_alias=True),
        ),
        page=PluginPageV1(enabled=False, layout="content-only", components=[]),
        schema={},
    )


def _read_manifest_file(plugin_path: Path) -> tuple[Path | None, dict[str, Any] | None]:
    for filename in MANIFEST_CANDIDATES:
        candidate = plugin_path / filename
        if not candidate.exists():
            continue
        try:
            payload = yaml.safe_load(candidate.read_text(encoding="utf-8"))
        except Exception:
            return candidate, None
        if not isinstance(payload, dict):
            return candidate, None
        return candidate, payload
    return None, None


def resolve_page_manifest(
    *,
    plugin_id: str,
    plugin_version: str,
    plugin_path: Path | None,
) -> ManifestResolution:
    fallback = _fallback_manifest(plugin_id=plugin_id, plugin_version=plugin_version)
    if plugin_path is None:
        return ManifestResolution(
            manifest=fallback,
            accepted=False,
            fallback_used=True,
            reason="plugin_path_missing",
        )

    source_file, raw_payload = _read_manifest_file(plugin_path)
    if source_file is None:
        return ManifestResolution(
            manifest=fallback,
            accepted=False,
            fallback_used=True,
            reason="manifest_not_found",
        )

    if raw_payload is None:
        return ManifestResolution(
            manifest=fallback,
            accepted=False,
            fallback_used=True,
            reason="invalid_manifest_yaml",
        )

    raw_manifest_version = str(raw_payload.get("manifest_version", "")).strip() or "0"
    if _parse_major(raw_manifest_version) != SUPPORTED_MANIFEST_MAJOR:
        return ManifestResolution(
            manifest=fallback,
            accepted=False,
            fallback_used=True,
            reason="incompatible_manifest_version",
        )

    raw_plugin_api_version = str(raw_payload.get("plugin_api_version", "")).strip() or "0"
    if _parse_major(raw_plugin_api_version) > SUPPORTED_PLUGIN_API_MAJOR:
        return ManifestResolution(
            manifest=fallback,
            accepted=False,
            fallback_used=True,
            reason="incompatible_plugin_api_version",
        )

    try:
        parsed = PluginPageManifestV1.model_validate(raw_payload)
    except ValidationError as exc:
        return ManifestResolution(
            manifest=fallback,
            accepted=False,
            fallback_used=True,
            reason="manifest_schema_validation_failed",
            errors=tuple(str(item.get("msg", "invalid")) for item in exc.errors()),
        )

    if parsed.plugin_id != plugin_id:
        return ManifestResolution(
            manifest=fallback,
            accepted=False,
            fallback_used=True,
            reason="plugin_id_mismatch",
        )

    datasource_capability_errors: list[str] = []
    for component in parsed.page.components:
        if isinstance(component, PluginDataTableComponentV1):
            cap = (component.data_source.capability or "").strip()
            if cap and cap not in parsed.capabilities:
                datasource_capability_errors.append(
                    f"component '{component.id}' references undeclared capability '{cap}'"
                )
            for action in component.row_actions:
                action_capability = (action.capability or "").strip()
                if action_capability and action_capability not in parsed.capabilities:
                    datasource_capability_errors.append(
                        f"component '{component.id}' row action '{action.id}' "
                        f"references undeclared capability '{action_capability}'"
                    )
    if datasource_capability_errors:
        return ManifestResolution(
            manifest=fallback,
            accepted=False,
            fallback_used=True,
            reason="capability_declaration_mismatch",
            errors=tuple(datasource_capability_errors),
        )

    return ManifestResolution(
        manifest=parsed,
        accepted=True,
        fallback_used=False,
    )


def serialize_resolution(resolution: ManifestResolution) -> dict[str, Any]:
    return {
        "manifest": resolution.manifest.model_dump(mode="json", by_alias=True),
        "negotiation": {
            "accepted": resolution.accepted,
            "fallback_used": resolution.fallback_used,
            "reason": resolution.reason,
            "errors": list(resolution.errors),
            "supported_manifest_major": SUPPORTED_MANIFEST_MAJOR,
            "supported_plugin_api_major": SUPPORTED_PLUGIN_API_MAJOR,
        },
    }


__all__ = [
    "SUPPORTED_MANIFEST_MAJOR",
    "SUPPORTED_PLUGIN_API_MAJOR",
    "ManifestResolution",
    "PluginPageManifestV1",
    "resolve_page_manifest",
    "serialize_resolution",
]
