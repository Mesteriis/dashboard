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
    db_path = (tmp_path / "dashboard.sqlite3").resolve()
    write_dashboard_yaml(config_path, build_dashboard_config(fake))
    monkeypatch.setenv("DASHBOARD_CONFIG_FILE", str(config_path))
    monkeypatch.setenv("DASHBOARD_DB_FILE", str(db_path))

    main_module = importlib.import_module("main")
    main_module = importlib.reload(main_module)
    original_container = main_module.container
    missing_index = (tmp_path / "missing.html").resolve()
    try:
        monkeypatch.setattr(
            main_module,
            "container",
            SimpleNamespace(settings=SimpleNamespace(index_file=missing_index)),
        )

        response = await main_module.root()
        assert response.status_code == 503
    finally:
        db_engine = getattr(original_container, "db_engine", None)
        if db_engine is not None:
            db_engine.dispose()


async def test_root_returns_file_response_when_index_exists(
    fake,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = (tmp_path / "dashboard.yaml").resolve()
    db_path = (tmp_path / "dashboard.sqlite3").resolve()
    write_dashboard_yaml(config_path, build_dashboard_config(fake))
    monkeypatch.setenv("DASHBOARD_CONFIG_FILE", str(config_path))
    monkeypatch.setenv("DASHBOARD_DB_FILE", str(db_path))

    main_module = importlib.import_module("main")
    main_module = importlib.reload(main_module)
    original_container = main_module.container
    index_file = (tmp_path / "index.html").resolve()
    index_file.write_text("<html></html>", encoding="utf-8")
    try:
        monkeypatch.setattr(main_module, "container", SimpleNamespace(settings=SimpleNamespace(index_file=index_file)))

        response = await main_module.root()
        assert response.status_code == 200
        assert "app" in main_module.__all__
    finally:
        db_engine = getattr(original_container, "db_engine", None)
        if db_engine is not None:
            db_engine.dispose()
