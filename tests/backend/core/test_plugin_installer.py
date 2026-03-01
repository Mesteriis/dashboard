from __future__ import annotations

from pathlib import Path

from core.plugins.store import PluginInstaller, StoreClient


def _touch(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_resolve_plugin_root_flat_layout(tmp_path: Path) -> None:
    source = tmp_path / "flat"
    source.mkdir(parents=True, exist_ok=True)
    _touch(source / "__init__.py")
    _touch(source / "manifest.py")

    installer = PluginInstaller(
        install_dir=tmp_path / "install",
        store_client=StoreClient.create("http://127.0.0.1:18001/api/v1"),
    )

    resolved = installer._resolve_plugin_root(source_path=source, expected_name="probe")
    assert resolved == source


def test_resolve_plugin_root_nested_layout(tmp_path: Path) -> None:
    source = tmp_path / "nested"
    package = source / "bundle" / "oko_e2e_probe"
    package.mkdir(parents=True, exist_ok=True)
    _touch(package / "__init__.py")
    _touch(package / "manifest.py")

    installer = PluginInstaller(
        install_dir=tmp_path / "install",
        store_client=StoreClient.create("http://127.0.0.1:18001/api/v1"),
    )

    resolved = installer._resolve_plugin_root(
        source_path=source,
        expected_name="oko_e2e_probe",
    )
    assert resolved == package
