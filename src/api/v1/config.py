from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Request, Response

import depens.v1.health_runtime as health_runtime
from depens.v1.dashboard_deps import ConfigServiceDep, validation_exception
from scheme.dashboard import ConfigVersion, DashboardConfig, SaveConfigResponse, ValidateRequest, ValidateResponse
from service.config_service import DashboardConfigValidationError

config_router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@config_router.get(
    "/config",
    response_model=DashboardConfig,
    summary="Get dashboard configuration",
    description="Returns the current dashboard configuration with support for ETag-based caching.",
    responses={
        200: {"description": "Current dashboard configuration"},
        304: {"description": "Configuration unchanged (ETag match)"},
        422: {"description": "Configuration validation error"},
    },
)
async def get_dashboard_config(
    request: Request,
    response: Response,
    config_service: ConfigServiceDep,
) -> DashboardConfig | Response:
    try:
        version = config_service.get_version()
        etag = health_runtime._config_etag(version)

        if health_runtime._if_none_match_matches(request.headers.get("if-none-match"), etag):
            return Response(
                status_code=304,
                headers={
                    "etag": etag,
                    "cache-control": health_runtime.CONFIG_CACHE_CONTROL,
                },
            )

        config = config_service.load()
    except DashboardConfigValidationError as exc:
        raise validation_exception(exc) from exc

    response.headers["etag"] = etag
    response.headers["cache-control"] = health_runtime.CONFIG_CACHE_CONTROL
    return config


@config_router.get(
    "/version",
    response_model=ConfigVersion,
    summary="Get configuration version",
    description="Returns the current configuration version metadata (revision, SHA256).",
)
async def get_dashboard_config_version(config_service: ConfigServiceDep) -> ConfigVersion:
    try:
        return config_service.get_version()
    except DashboardConfigValidationError as exc:
        raise validation_exception(exc) from exc


@config_router.get(
    "/errors",
    summary="Get last configuration errors",
    description="Returns the last configuration validation errors.",
)
async def get_dashboard_last_errors(config_service: ConfigServiceDep) -> dict[str, list[dict[str, str]]]:
    return {"issues": [issue.model_dump() for issue in config_service.last_issues]}


@config_router.post(
    "/validate",
    response_model=ValidateResponse,
    summary="Validate dashboard YAML",
    description="Validates a YAML configuration string and returns validation issues.",
)
async def validate_dashboard_yaml(payload: ValidateRequest, config_service: ConfigServiceDep) -> ValidateResponse:
    config, issues = config_service.validate_yaml(payload.yaml)
    return ValidateResponse(valid=not issues, issues=issues, config=config)


@config_router.put(
    "/config",
    response_model=SaveConfigResponse,
    summary="Save dashboard configuration",
    description="Saves a new dashboard configuration and creates a revision.",
    responses={
        200: {"description": "Configuration saved successfully"},
        422: {"description": "Configuration validation error"},
    },
)
async def save_dashboard_config(
    payload: DashboardConfig,
    config_service: ConfigServiceDep,
) -> SaveConfigResponse:
    try:
        state = config_service.save(payload.model_dump(mode="json", exclude_none=True), source="api")
        return SaveConfigResponse(config=state.config, version=state.version)
    except DashboardConfigValidationError as exc:
        raise validation_exception(exc) from exc


@config_router.get(
    "/config/backup",
    summary="Download configuration backup",
    description="Exports the current configuration as a YAML file attachment.",
    responses={
        200: {"description": "YAML backup file", "content": {"application/x-yaml": {}}},
        422: {"description": "Configuration validation error"},
    },
)
async def download_dashboard_config_backup(config_service: ConfigServiceDep) -> Response:
    try:
        backup_yaml = config_service.export_yaml()
    except DashboardConfigValidationError as exc:
        raise validation_exception(exc) from exc

    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return Response(
        content=backup_yaml,
        media_type="application/x-yaml",
        headers={
            "content-disposition": f'attachment; filename="dashboard-backup-{timestamp}.yaml"',
            "cache-control": health_runtime.CONFIG_CACHE_CONTROL,
        },
    )


@config_router.post(
    "/config/restore",
    response_model=SaveConfigResponse,
    summary="Restore configuration from YAML",
    description="Imports and saves a YAML configuration string.",
    responses={
        200: {"description": "Configuration restored successfully"},
        422: {"description": "Configuration validation error"},
    },
)
async def restore_dashboard_config(
    payload: ValidateRequest,
    config_service: ConfigServiceDep,
) -> SaveConfigResponse:
    try:
        state = config_service.import_yaml(payload.yaml, source="restore")
        return SaveConfigResponse(config=state.config, version=state.version)
    except DashboardConfigValidationError as exc:
        raise validation_exception(exc) from exc


__all__ = ["config_router"]
