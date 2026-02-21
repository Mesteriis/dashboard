from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path

ADMIN_TOKEN_HEADER = "X-Dashboard-Token"
PROXY_ACCESS_COOKIE = "dashboard_proxy_access"


@dataclass(frozen=True)
class AppSettings:
    base_dir: Path
    static_dir: Path
    index_file: Path
    config_file: Path
    healthcheck_timeout_sec: float
    healthcheck_max_parallel: int
    healthcheck_verify_tls: bool
    admin_token: str
    admin_token_header: str
    proxy_access_cookie: str
    proxy_token_secret: str
    proxy_token_ttl_sec: int


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, *, minimum: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be an integer") from exc
    return max(minimum, value)


def _env_float(name: str, default: float, *, minimum: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be a float") from exc
    return max(minimum, value)


def load_app_settings(base_dir: Path | None = None) -> AppSettings:
    resolved_base_dir = base_dir or Path(__file__).resolve().parents[1]
    admin_token = os.getenv("DASHBOARD_ADMIN_TOKEN", "").strip()
    proxy_secret = (
        os.getenv("DASHBOARD_PROXY_TOKEN_SECRET", "").strip()
        or admin_token
        or secrets.token_urlsafe(32)
    )

    return AppSettings(
        base_dir=resolved_base_dir,
        static_dir=resolved_base_dir / "static",
        index_file=resolved_base_dir / "templates" / "index.html",
        config_file=Path(
            os.getenv(
                "DASHBOARD_CONFIG_FILE",
                str(resolved_base_dir.parent / "dashboard.yaml"),
            )
        ),
        healthcheck_timeout_sec=_env_float("DASHBOARD_HEALTHCHECK_TIMEOUT_SEC", 4.0, minimum=0.2),
        healthcheck_max_parallel=_env_int("DASHBOARD_HEALTHCHECK_MAX_PARALLEL", 8, minimum=1),
        healthcheck_verify_tls=_env_bool("DASHBOARD_HEALTHCHECK_VERIFY_TLS", True),
        admin_token=admin_token,
        admin_token_header=ADMIN_TOKEN_HEADER,
        proxy_access_cookie=PROXY_ACCESS_COOKIE,
        proxy_token_secret=proxy_secret,
        proxy_token_ttl_sec=_env_int("DASHBOARD_PROXY_TOKEN_TTL_SEC", 3600, minimum=30),
    )
