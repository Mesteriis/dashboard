from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from config.settings import AppSettings, load_app_settings
from db.migrations import run_alembic_upgrade
from db.session import build_sqlite_engine, sqlite_url_from_path
from service.config_service import DashboardConfigService
from service.lan_scan import LanScanService, lan_scan_settings_from_env
from tools.auth import ProxyAccessSigner


@dataclass(frozen=True)
class AppContainer:
    settings: AppSettings
    db_engine: Engine
    db_session_factory: sessionmaker[Session]
    config_service: DashboardConfigService
    lan_scan_service: LanScanService
    proxy_signer: ProxyAccessSigner


def build_container(base_dir: Path | None = None) -> AppContainer:
    settings = load_app_settings(base_dir=base_dir)
    db_engine = build_sqlite_engine(settings.db_file)
    db_session_factory = sessionmaker(bind=db_engine, autoflush=False, autocommit=False, expire_on_commit=False)
    run_alembic_upgrade(
        ini_path=(settings.base_dir.parent / "alembic.ini"),
        db_url=sqlite_url_from_path(settings.db_file),
    )

    config_service = DashboardConfigService(
        config_path=settings.config_file,
        db_session_factory=db_session_factory,
    )
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
        db_engine=db_engine,
        db_session_factory=db_session_factory,
        config_service=config_service,
        lan_scan_service=lan_scan_service,
        proxy_signer=proxy_signer,
    )
