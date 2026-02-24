from __future__ import annotations

from pathlib import Path

from config.container import _default_plugin_storage_configs


def test_default_plugin_storage_configs_normalize_ddl_indexes_to_columns() -> None:
    project_root = Path(__file__).resolve().parents[3]
    backend_dir = project_root / "backend"

    configs = _default_plugin_storage_configs(backend_dir)
    assert configs

    autodiscover = configs.get("autodiscover")
    assert autodiscover is not None
    assert autodiscover.tables

    scan_runs = next(table for table in autodiscover.tables if table.name == "scan_runs")
    assert scan_runs.indexes == ["status", "dry_run"]
    assert all(isinstance(index_name, str) for index_name in scan_runs.indexes)
