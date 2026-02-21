from __future__ import annotations

from pathlib import Path

import pytest

import service.lan_scan.settings as lan_settings
from service.lan_scan import lan_scan_settings_from_env


def test_lan_scan_disabled_by_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("LAN_SCAN_ENABLED", raising=False)
    monkeypatch.delenv("DASHBOARD_ENABLE_LAN_SCAN", raising=False)

    base_dir = (tmp_path / "app" / "src").resolve()
    settings = lan_scan_settings_from_env(base_dir)

    assert not settings.enabled
    assert not settings.run_on_startup
    assert settings.http_verify_tls


def test_startup_flag_enables_lan_scan(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DASHBOARD_ENABLE_LAN_SCAN", "true")
    monkeypatch.delenv("LAN_SCAN_ENABLED", raising=False)
    settings = lan_scan_settings_from_env((tmp_path / "project" / "src").resolve())
    assert settings.enabled


def test_explicit_lan_scan_enabled_overrides_startup_flag(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("DASHBOARD_ENABLE_LAN_SCAN", "false")
    monkeypatch.setenv("LAN_SCAN_ENABLED", "true")
    settings = lan_scan_settings_from_env((tmp_path / "project" / "src").resolve())
    assert settings.enabled


def test_parse_ports_and_cidrs_helpers() -> None:
    ports = lan_settings._parse_ports("22,80,80,100-102,bad")
    cidrs = lan_settings._parse_cidrs("192.168.1.10/24,10.0.0.1/24,not-cidr")
    assert ports == (22, 80, 100, 101, 102)
    assert cidrs == ("192.168.1.0/24", "10.0.0.0/24")


def test_parse_ports_falls_back_to_safe_defaults() -> None:
    assert lan_settings._parse_ports(None) == lan_settings.SAFE_DEFAULT_SCAN_PORTS
    assert lan_settings._parse_ports("bad") == lan_settings.SAFE_DEFAULT_SCAN_PORTS


def test_known_homelab_ports_have_service_aliases() -> None:
    assert lan_settings.PORT_SERVICE_NAMES[11434] == "ollama"
    assert lan_settings.PORT_SERVICE_NAMES[19999] == "netdata"
    assert lan_settings.PORT_SERVICE_NAMES[6333] == "qdrant"
    assert lan_settings.PORT_SERVICE_NAMES[7575] == "homarr"


def test_minimums_are_enforced(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LAN_SCAN_INTERVAL_SEC", "1")
    monkeypatch.setenv("LAN_SCAN_CONNECT_TIMEOUT_SEC", "0.01")
    monkeypatch.setenv("LAN_SCAN_MAX_PARALLEL", "1")
    monkeypatch.setenv("LAN_SCAN_MAX_HOSTS", "1")
    monkeypatch.setenv("LAN_SCAN_RESULT_FILE", str((tmp_path / "res.json").resolve()))
    settings = lan_scan_settings_from_env((tmp_path / "src").resolve())
    assert settings.interval_sec == 30
    assert settings.connect_timeout_sec == 0.1
    assert settings.max_parallel == 16
    assert settings.max_hosts == 32
