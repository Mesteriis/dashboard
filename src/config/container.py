from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from config.settings import AppSettings, load_app_settings
from service.config_service import DashboardConfigService
from service.lan_scan import LanScanService, lan_scan_settings_from_env
from tools.auth import ProxyAccessSigner


@dataclass(frozen=True)
class AppContainer:
    settings: AppSettings
    config_service: DashboardConfigService
    lan_scan_service: LanScanService
    proxy_signer: ProxyAccessSigner


def build_container(base_dir: Path | None = None) -> AppContainer:
    settings = load_app_settings(base_dir=base_dir)
    config_service = DashboardConfigService(config_path=settings.config_file)
    lan_scan_service = LanScanService(
        config_service=config_service,
        settings=lan_scan_settings_from_env(settings.base_dir),
    )
    proxy_signer = ProxyAccessSigner(
        secret=settings.proxy_token_secret,
        ttl_sec=settings.proxy_token_ttl_sec,
    )
    return AppContainer(
        settings=settings,
        config_service=config_service,
        lan_scan_service=lan_scan_service,
        proxy_signer=proxy_signer,
    )
