from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_base_dir() -> Path:
    return Path(__file__).resolve().parents[1]


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=None,
        populate_by_name=True,
    )

    base_dir: Path = Field(default_factory=_default_base_dir)
    static_dir: Path = Field(default_factory=lambda: _default_base_dir().parent / "static")
    media_dir: Path = Field(
        default_factory=lambda: _default_base_dir().parent / "media",
        validation_alias="OKO_MEDIA_DIR",
    )
    index_file: Path = Field(default_factory=lambda: _default_base_dir().parent / "templates" / "index.html")
    config_file: Path = Field(
        default_factory=lambda: _default_base_dir().parent / "_dashboard.yaml",
        validation_alias="OKO_BOOTSTRAP_CONFIG_FILE",
    )
    database_url: str = Field(
        default="postgresql+asyncpg://oko:oko@localhost:5432/oko",
        validation_alias="DATABASE_URL",
    )
    broker_url: str = Field(
        default="amqp://oko:oko@localhost:5672/",
        validation_alias="BROKER_URL",
    )
    runtime_role: Literal["backend", "worker"] = Field(
        default="backend",
        validation_alias="OKO_RUNTIME_ROLE",
    )
    enable_local_consumers: bool = Field(
        default=False,
        validation_alias="OKO_ENABLE_LOCAL_CONSUMERS",
    )
    broker_prefetch_count: int = Field(
        default=32,
        ge=1,
        le=1024,
        validation_alias="OKO_BROKER_PREFETCH_COUNT",
    )
    event_stream_keepalive_sec: float = Field(default=15.0, validation_alias="OKO_EVENTS_KEEPALIVE_SEC")
    actions_execute_enabled: bool = Field(default=True, validation_alias="OKO_ACTIONS_EXECUTE_ENABLED")
    storage_rpc_timeout_sec: float = Field(default=2.0, validation_alias="OKO_STORAGE_RPC_TIMEOUT_SEC")
    action_rpc_timeout_sec: float = Field(default=5.0, validation_alias="OKO_ACTION_RPC_TIMEOUT_SEC")
    health_window_size: int = Field(default=10, ge=1, le=500, validation_alias="OKO_HEALTH_WINDOW_SIZE")
    health_retention_days: int = Field(default=7, ge=1, le=365, validation_alias="OKO_HEALTH_RETENTION_DAYS")
    health_icmp_enabled: bool = Field(default=False, validation_alias="OKO_HEALTH_ICMP_ENABLED")
    health_scheduler_tick_sec: float = Field(default=5.0, validation_alias="OKO_HEALTH_SCHEDULER_TICK_SEC")
    health_scheduler_heartbeat_sec: float = Field(
        default=30.0,
        validation_alias="OKO_HEALTH_SCHEDULER_HEARTBEAT_SEC",
    )
    health_default_interval_sec: int = Field(default=300, ge=1, le=3600, validation_alias="OKO_HEALTH_INTERVAL_SEC")
    health_default_timeout_ms: int = Field(default=1500, ge=100, le=120_000, validation_alias="OKO_HEALTH_TIMEOUT_MS")
    health_default_latency_threshold_ms: int = Field(
        default=800,
        ge=1,
        le=120_000,
        validation_alias="OKO_HEALTH_LATENCY_THRESHOLD_MS",
    )
    favicon_timeout_sec: float = Field(default=4.0, ge=0.5, le=30.0, validation_alias="OKO_FAVICON_TIMEOUT_SEC")
    favicon_max_bytes: int = Field(default=262_144, ge=1024, le=1_048_576, validation_alias="OKO_FAVICON_MAX_BYTES")
    favicon_tls_verify: bool = Field(default=True, validation_alias="OKO_FAVICON_TLS_VERIFY")
    favicon_tls_insecure_fallback: bool = Field(
        default=True,
        validation_alias="OKO_FAVICON_TLS_INSECURE_FALLBACK",
    )
    favicon_cache_ttl_days: int = Field(default=7, ge=1, le=365, validation_alias="OKO_FAVICON_CACHE_TTL_DAYS")

    @model_validator(mode="after")
    def _apply_minimums(self) -> AppSettings:
        object.__setattr__(self, "event_stream_keepalive_sec", max(2.0, self.event_stream_keepalive_sec))
        object.__setattr__(self, "storage_rpc_timeout_sec", max(0.05, self.storage_rpc_timeout_sec))
        object.__setattr__(self, "action_rpc_timeout_sec", max(0.05, self.action_rpc_timeout_sec))
        object.__setattr__(self, "health_scheduler_tick_sec", max(0.2, self.health_scheduler_tick_sec))
        object.__setattr__(
            self,
            "health_scheduler_heartbeat_sec",
            max(5.0, self.health_scheduler_heartbeat_sec),
        )
        object.__setattr__(self, "health_default_interval_sec", max(1, self.health_default_interval_sec))
        object.__setattr__(self, "health_default_timeout_ms", max(100, self.health_default_timeout_ms))
        object.__setattr__(
            self,
            "health_default_latency_threshold_ms",
            max(1, self.health_default_latency_threshold_ms),
        )
        object.__setattr__(self, "favicon_timeout_sec", max(0.5, self.favicon_timeout_sec))
        object.__setattr__(self, "favicon_max_bytes", max(1024, self.favicon_max_bytes))
        object.__setattr__(self, "favicon_cache_ttl_days", max(1, self.favicon_cache_ttl_days))
        return self

def load_app_settings(base_dir: Path | None = None) -> AppSettings:
    if base_dir is None:
        return AppSettings()
    return AppSettings(base_dir=base_dir.resolve())


__all__ = ["AppSettings", "load_app_settings"]
