"""Dependencies for dashboard API routers."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException

from config.container import AppContainer
from config.settings import AppSettings
from db.repositories import HealthSampleRepository
from depens.v1.deps import get_container
from service.config_service import DashboardConfigService, DashboardConfigValidationError
from service.lan_scan import LanScanService
from tools.auth import ProxyAccessSigner


def validation_exception(exc: DashboardConfigValidationError) -> HTTPException:
    return HTTPException(status_code=422, detail=[issue.model_dump() for issue in exc.issues])


def get_settings(container: Annotated[AppContainer, Depends(get_container)]) -> AppSettings:
    return container.settings


def get_config_service(container: Annotated[AppContainer, Depends(get_container)]) -> DashboardConfigService:
    return container.config_service


def get_lan_scan_service(container: Annotated[AppContainer, Depends(get_container)]) -> LanScanService:
    return container.lan_scan_service


def get_proxy_signer(container: Annotated[AppContainer, Depends(get_container)]) -> ProxyAccessSigner:
    return container.proxy_signer


def get_health_sample_repository(
    container: Annotated[AppContainer, Depends(get_container)],
) -> HealthSampleRepository:
    return container.health_sample_repository


SettingsDep = Annotated[AppSettings, Depends(get_settings)]
ConfigServiceDep = Annotated[DashboardConfigService, Depends(get_config_service)]
LanScanServiceDep = Annotated[LanScanService, Depends(get_lan_scan_service)]
ProxySignerDep = Annotated[ProxyAccessSigner, Depends(get_proxy_signer)]
HealthSampleRepositoryDep = Annotated[HealthSampleRepository, Depends(get_health_sample_repository)]


__all__ = [
    "ConfigServiceDep",
    "HealthSampleRepositoryDep",
    "LanScanServiceDep",
    "ProxySignerDep",
    "SettingsDep",
    "get_config_service",
    "get_health_sample_repository",
    "get_lan_scan_service",
    "get_proxy_signer",
    "get_settings",
    "validation_exception",
]
