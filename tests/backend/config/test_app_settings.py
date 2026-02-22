from __future__ import annotations

from pathlib import Path

import pytest

import config.settings as settings_module
from config.settings import load_app_settings


def test_env_int_raises_for_invalid_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BAD_INT", "abc")
    with pytest.raises(ValueError):
        settings_module._env_int("BAD_INT", 1, minimum=1)


def test_env_float_raises_for_invalid_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BAD_FLOAT", "abc")
    with pytest.raises(ValueError):
        settings_module._env_float("BAD_FLOAT", 1.0, minimum=0.1)


def test_load_app_settings_uses_explicit_proxy_secret(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DASHBOARD_PROXY_TOKEN_SECRET", "proxy-secret")
    app_settings = load_app_settings(base_dir=tmp_path.resolve())
    assert app_settings.proxy_token_secret == "proxy-secret"


def test_load_app_settings_generates_proxy_secret_when_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DASHBOARD_PROXY_TOKEN_SECRET", raising=False)
    monkeypatch.setattr(settings_module.secrets, "token_urlsafe", lambda _: "generated-secret")
    app_settings = load_app_settings(base_dir=tmp_path.resolve())
    assert app_settings.proxy_token_secret == "generated-secret"


def test_load_app_settings_applies_env_and_minimums(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_file = (tmp_path / "custom.yaml").resolve()
    monkeypatch.setenv("DASHBOARD_CONFIG_FILE", str(config_file))
    monkeypatch.setenv("DASHBOARD_HEALTHCHECK_TIMEOUT_SEC", "0.01")
    monkeypatch.setenv("DASHBOARD_HEALTHCHECK_MAX_PARALLEL", "0")
    monkeypatch.setenv("DASHBOARD_HEALTH_HISTORY_SIZE", "0")
    monkeypatch.setenv("DASHBOARD_PROXY_TOKEN_TTL_SEC", "1")
    monkeypatch.setenv("DASHBOARD_HEALTHCHECK_VERIFY_TLS", "off")

    app_settings = load_app_settings(base_dir=tmp_path.resolve())
    assert app_settings.config_file == config_file
    assert app_settings.healthcheck_timeout_sec == 0.2
    assert app_settings.healthcheck_max_parallel == 1
    assert app_settings.health_history_size == 1
    assert app_settings.proxy_token_ttl_sec == 30
    assert app_settings.healthcheck_verify_tls is False
