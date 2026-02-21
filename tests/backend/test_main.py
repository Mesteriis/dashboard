from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest
from support.factories import build_dashboard_config, write_dashboard_yaml

pytestmark = pytest.mark.asyncio


async def test_root_returns_503_when_index_is_missing(
    fake,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = (tmp_path / "dashboard.yaml").resolve()
    write_dashboard_yaml(config_path, build_dashboard_config(fake))
    monkeypatch.setenv("DASHBOARD_CONFIG_FILE", str(config_path))

    main_module = importlib.import_module("main")
    main_module = importlib.reload(main_module)
    missing_index = (tmp_path / "missing.html").resolve()
    monkeypatch.setattr(main_module, "container", SimpleNamespace(settings=SimpleNamespace(index_file=missing_index)))

    response = await main_module.root()
    assert response.status_code == 503


async def test_root_returns_file_response_when_index_exists(
    fake,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = (tmp_path / "dashboard.yaml").resolve()
    write_dashboard_yaml(config_path, build_dashboard_config(fake))
    monkeypatch.setenv("DASHBOARD_CONFIG_FILE", str(config_path))

    main_module = importlib.import_module("main")
    main_module = importlib.reload(main_module)
    index_file = (tmp_path / "index.html").resolve()
    index_file.write_text("<html></html>", encoding="utf-8")
    monkeypatch.setattr(main_module, "container", SimpleNamespace(settings=SimpleNamespace(index_file=index_file)))

    response = await main_module.root()
    assert response.status_code == 200
    assert "app" in main_module.__all__
