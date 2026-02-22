from __future__ import annotations

import secrets
from pathlib import Path
from typing import Any

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROXY_ACCESS_COOKIE = "dashboard_proxy_access"


def _default_base_dir() -> Path:
    return Path(__file__).resolve().parents[1]


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=None,
        populate_by_name=True,
    )

    base_dir: Path = Field(default_factory=_default_base_dir)
    static_dir: Path = Field(default_factory=lambda: _default_base_dir() / "static")
    index_file: Path = Field(default_factory=lambda: _default_base_dir() / "templates" / "index.html")
    config_file: Path = Field(
        default_factory=lambda: _default_base_dir().parent / "dashboard.yaml",
        validation_alias="DASHBOARD_CONFIG_FILE",
    )
    db_file: Path = Field(
        default_factory=lambda: _default_base_dir().parent / "data" / "dashboard.sqlite3",
        validation_alias="DASHBOARD_DB_FILE",
    )
    healthcheck_timeout_sec: float = Field(default=4.0, validation_alias="DASHBOARD_HEALTHCHECK_TIMEOUT_SEC")
    healthcheck_max_parallel: int = Field(default=8, validation_alias="DASHBOARD_HEALTHCHECK_MAX_PARALLEL")
    healthcheck_verify_tls: bool = Field(default=True, validation_alias="DASHBOARD_HEALTHCHECK_VERIFY_TLS")
    health_refresh_sec: float = Field(default=5.0, validation_alias="DASHBOARD_HEALTH_REFRESH_SEC")
    health_sse_keepalive_sec: float = Field(default=15.0, validation_alias="DASHBOARD_HEALTH_SSE_KEEPALIVE_SEC")
    health_history_size: int = Field(default=20, validation_alias="DASHBOARD_HEALTH_HISTORY_SIZE")
    health_samples_retention_days: int = Field(default=30, validation_alias="DASHBOARD_HEALTH_SAMPLES_RETENTION_DAYS")
    proxy_access_cookie: str = Field(default=PROXY_ACCESS_COOKIE)
    proxy_token_secret: str = Field(default="", validation_alias="DASHBOARD_PROXY_TOKEN_SECRET")
    proxy_token_ttl_sec: int = Field(default=3600, validation_alias="DASHBOARD_PROXY_TOKEN_TTL_SEC")

    @model_validator(mode="before")
    @classmethod
    def _populate_paths_and_secret(_cls, data: Any) -> Any:
        values = dict(data) if isinstance(data, dict) else {}

        base_dir_raw = values.get("base_dir")
        base_dir = Path(base_dir_raw).resolve() if base_dir_raw is not None else _default_base_dir().resolve()
        values["base_dir"] = base_dir

        values.setdefault("static_dir", base_dir / "static")
        values.setdefault("index_file", base_dir / "templates" / "index.html")
        values.setdefault("config_file", base_dir.parent / "dashboard.yaml")
        values.setdefault("db_file", base_dir.parent / "data" / "dashboard.sqlite3")

        proxy_secret = str(values.get("proxy_token_secret") or "").strip()
        values["proxy_token_secret"] = proxy_secret or secrets.token_urlsafe(32)
        values.setdefault("proxy_access_cookie", PROXY_ACCESS_COOKIE)

        return values

    @model_validator(mode="after")
    def _apply_minimums(self) -> AppSettings:
        object.__setattr__(self, "healthcheck_timeout_sec", max(0.2, self.healthcheck_timeout_sec))
        object.__setattr__(self, "healthcheck_max_parallel", max(1, self.healthcheck_max_parallel))
        object.__setattr__(self, "health_refresh_sec", max(0.0, self.health_refresh_sec))
        object.__setattr__(self, "health_sse_keepalive_sec", max(2.0, self.health_sse_keepalive_sec))
        object.__setattr__(self, "health_history_size", max(1, self.health_history_size))
        object.__setattr__(self, "proxy_token_ttl_sec", max(30, self.proxy_token_ttl_sec))
        return self


def load_app_settings(base_dir: Path | None = None) -> AppSettings:
    if base_dir is None:
        return AppSettings()
    return AppSettings(base_dir=base_dir.resolve())
