from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from core.plugins.schemas import PluginInfo, PluginManifest, PluginState
from core.plugins.service import PluginService

pytestmark = pytest.mark.asyncio


def _plugin(
    plugin_id: str,
    *,
    state: PluginState = PluginState.DISCOVERED,
    path: Path | None = None,
    module: Any = None,
) -> PluginInfo:
    return PluginInfo(
        id=plugin_id,
        manifest=PluginManifest(name=plugin_id, version="1.0.0", description=f"Plugin {plugin_id}"),
        state=state,
        path=path,
        module=module,
    )


class FakeRegistry:
    def __init__(self, plugins: list[PluginInfo]) -> None:
        self.plugins: dict[str, PluginInfo] = {plugin.id: plugin for plugin in plugins}
        self.sync_result: dict[str, list[str]] = {"added": [], "removed": []}
        self.refresh_fail_ids: set[str] = set()
        self.initialize_called = False
        self.load_calls: list[str] = []
        self.unload_calls: list[str] = []
        self.reload_calls: list[str] = []
        self.enable_calls: list[str] = []
        self.disable_calls: list[str] = []

    def initialize(self) -> None:
        self.initialize_called = True

    def list_plugins(self) -> list[PluginInfo]:
        return list(self.plugins.values())

    def list_active(self) -> list[PluginInfo]:
        return [plugin for plugin in self.plugins.values() if plugin.state == PluginState.ACTIVE]

    def get_plugin(self, plugin_id: str) -> PluginInfo | None:
        return self.plugins.get(plugin_id)

    def load_plugin(self, plugin_id: str) -> PluginInfo:
        self.load_calls.append(plugin_id)
        plugin = self.plugins[plugin_id]
        plugin.state = PluginState.ACTIVE
        return plugin

    def unload_plugin(self, plugin_id: str) -> bool:
        self.unload_calls.append(plugin_id)
        plugin = self.plugins.get(plugin_id)
        if plugin is None:
            return False
        plugin.state = PluginState.DISCOVERED
        return True

    def reload_plugin(self, plugin_id: str) -> PluginInfo:
        self.reload_calls.append(plugin_id)
        plugin = self.plugins[plugin_id]
        plugin.state = PluginState.ACTIVE
        return plugin

    def enable_plugin(self, plugin_id: str) -> PluginInfo:
        self.enable_calls.append(plugin_id)
        plugin = self.plugins[plugin_id]
        plugin.state = PluginState.ACTIVE
        return plugin

    def disable_plugin(self, plugin_id: str) -> bool:
        self.disable_calls.append(plugin_id)
        plugin = self.plugins.get(plugin_id)
        if plugin is None:
            return False
        plugin.state = PluginState.DISABLED
        return True

    def sync(self) -> dict[str, list[str]]:
        return self.sync_result

    def refresh_plugin_metadata(self, plugin_id: str) -> PluginInfo | None:
        if plugin_id in self.refresh_fail_ids:
            raise RuntimeError(f"refresh failed for {plugin_id}")
        return self.plugins.get(plugin_id)

    def to_dict(self) -> dict[str, Any]:
        return {"plugins": sorted(self.plugins.keys())}


class FakeRouter:
    def __init__(self) -> None:
        self.mounted_plugins: list[str] = []
        self.unmounted_plugins: list[str] = []
        self.mount_all_active_called = False

    def mount_all_active(self) -> None:
        self.mount_all_active_called = True

    def _mount_plugin_routes(self, plugin: PluginInfo) -> None:
        self.mounted_plugins.append(plugin.id)

    def _unmount_plugin_routes(self, plugin_id: str) -> None:
        self.unmounted_plugins.append(plugin_id)


async def test_create_autoloads_discovered_plugins(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    discovered_dir = tmp_path / "p-discovered"
    discovered_dir.mkdir()
    (discovered_dir / "__init__.py").write_text("", encoding="utf-8")

    active_dir = tmp_path / "p-active"
    active_dir.mkdir()
    (active_dir / "__init__.py").write_text("", encoding="utf-8")

    discovered = _plugin("p-discovered", state=PluginState.DISCOVERED, path=discovered_dir)
    active = _plugin("p-active", state=PluginState.ACTIVE, path=active_dir)

    captured: dict[str, Any] = {}

    class _Scanner:
        def __init__(self, plugin_dirs: tuple[Path, ...]) -> None:
            self.plugin_dirs = plugin_dirs

    class _Registry(FakeRegistry):
        def __init__(self, scanner: Any, setup_kwargs: dict[str, Any] | None = None) -> None:
            _ = (scanner, setup_kwargs)
            super().__init__([discovered, active])
            captured["registry"] = self

    class _Router(FakeRouter):
        def __init__(self, registry: Any, base_path: str, api_base_path: str) -> None:
            _ = (registry, base_path, api_base_path)
            super().__init__()
            captured["router"] = self

    monkeypatch.setattr("core.plugins.service.PluginScanner", _Scanner)
    monkeypatch.setattr("core.plugins.service.PluginRegistry", _Registry)
    monkeypatch.setattr("core.plugins.service.PluginRouter", _Router)

    service = PluginService.create(plugin_dirs=(tmp_path,), plugin_setup_kwargs={"actor": "tester"})
    registry: FakeRegistry = captured["registry"]
    router: FakeRouter = captured["router"]

    assert registry.initialize_called is True
    assert "p-discovered" in registry.load_calls
    assert router.mount_all_active_called is True
    assert set(service._fingerprints) == {"p-discovered", "p-active"}


async def test_basic_service_operations_schedule_hooks(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    plugin_path = tmp_path / "p1"
    plugin_path.mkdir()
    (plugin_path / "mod.py").write_text("print('x')", encoding="utf-8")

    plugin = _plugin("p1", state=PluginState.DISCOVERED, path=plugin_path)
    registry = FakeRegistry([plugin])
    router = FakeRouter()
    service = PluginService(registry=registry, router=router)

    startup_calls: list[str] = []
    shutdown_calls: list[str] = []

    monkeypatch.setattr(service, "_schedule_startup_hook", lambda plugin: startup_calls.append(plugin.id))
    monkeypatch.setattr(service, "_schedule_shutdown_hook", lambda plugin: shutdown_calls.append(plugin.id))

    service._runtime_started = True

    loaded = service.load_plugin("p1")
    assert loaded.state == PluginState.ACTIVE
    assert router.mounted_plugins[-1] == "p1"
    assert startup_calls == ["p1"]

    assert service.unload_plugin("p1") is True
    assert router.unmounted_plugins[-1] == "p1"
    assert shutdown_calls[-1] == "p1"

    service.enable_plugin("p1")
    assert router.mounted_plugins[-1] == "p1"

    assert service.disable_plugin("p1") is True
    assert router.unmounted_plugins[-1] == "p1"


async def test_invoke_plugin_hook_startup_and_shutdown_paths() -> None:
    marks: list[str] = []

    async def _async_startup() -> None:
        marks.append("startup")

    def _sync_shutdown() -> None:
        marks.append("shutdown")

    plugin = _plugin(
        "p-hook",
        state=PluginState.ACTIVE,
        module=SimpleNamespace(on_startup=_async_startup, on_shutdown=_sync_shutdown),
    )
    service = PluginService(registry=FakeRegistry([plugin]), router=FakeRouter())

    await service._invoke_plugin_hook(plugin, hook_name="on_startup", mark_started=True)
    assert "startup" in marks
    assert "p-hook" in service._started_plugins

    # Already started: hook should not run twice.
    before = len(marks)
    await service._invoke_plugin_hook(plugin, hook_name="on_startup", mark_started=True)
    assert len(marks) == before

    await service._invoke_plugin_hook(plugin, hook_name="on_shutdown", mark_started=False)
    assert "shutdown" in marks
    assert "p-hook" not in service._started_plugins

    plugin_no_hook = _plugin("p-no-hook", module=SimpleNamespace())
    await service._invoke_plugin_hook(plugin_no_hook, hook_name="on_startup", mark_started=True)
    assert "p-no-hook" in service._started_plugins

    await service._invoke_plugin_hook(plugin_no_hook, hook_name="on_shutdown", mark_started=False)
    assert "p-no-hook" not in service._started_plugins

    plugin_error = _plugin(
        "p-error",
        module=SimpleNamespace(on_startup=lambda: (_ for _ in ()).throw(RuntimeError("boom"))),
    )
    await service._invoke_plugin_hook(plugin_error, hook_name="on_startup", mark_started=True)
    assert "p-error" not in service._started_plugins


async def test_startup_and_shutdown_delegate_to_hooks() -> None:
    calls: list[str] = []

    async def _on_startup() -> None:
        calls.append("startup")

    async def _on_shutdown() -> None:
        calls.append("shutdown")

    plugin = _plugin(
        "p-active",
        state=PluginState.ACTIVE,
        module=SimpleNamespace(on_startup=_on_startup, on_shutdown=_on_shutdown),
    )
    registry = FakeRegistry([plugin])
    service = PluginService(registry=registry, router=FakeRouter())

    await service.startup()
    assert service._runtime_started is True
    assert "p-active" in service._started_plugins

    await service.shutdown()
    assert service._runtime_started is False
    assert "shutdown" in calls


async def test_plugin_fingerprint_refresh_runtime_and_watch_loop(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    old_path = tmp_path / "old"
    old_path.mkdir()
    (old_path / "a.py").write_text("x=1", encoding="utf-8")

    new_path = tmp_path / "new"
    new_path.mkdir()
    (new_path / "b.py").write_text("x=2", encoding="utf-8")

    changed_active_path = tmp_path / "changed-active"
    changed_active_path.mkdir()
    (changed_active_path / "c.py").write_text("x=3", encoding="utf-8")

    changed_discovered_path = tmp_path / "changed-discovered"
    changed_discovered_path.mkdir()
    (changed_discovered_path / "d.py").write_text("x=4", encoding="utf-8")

    disabled_path = tmp_path / "disabled"
    disabled_path.mkdir()
    (disabled_path / "e.py").write_text("x=5", encoding="utf-8")

    failed_path = tmp_path / "failed"
    failed_path.mkdir()
    (failed_path / "f.py").write_text("x=6", encoding="utf-8")

    plugins = [
        _plugin("new", state=PluginState.DISCOVERED, path=new_path),
        _plugin("changed-active", state=PluginState.ACTIVE, path=changed_active_path),
        _plugin("changed-discovered", state=PluginState.DISCOVERED, path=changed_discovered_path),
        _plugin("disabled", state=PluginState.DISABLED, path=disabled_path),
        _plugin("failed", state=PluginState.ACTIVE, path=failed_path),
    ]
    registry = FakeRegistry(plugins)
    registry.sync_result = {"added": ["new"], "removed": ["old"]}
    registry.refresh_fail_ids = {"failed"}
    router = FakeRouter()
    service = PluginService(registry=registry, router=router)
    service._runtime_started = True
    service._started_plugins = {"old"}
    service._fingerprints = {
        "old": service._plugin_fingerprint(old_path),
        "changed-active": (0, 0),
        "changed-discovered": (0, 0),
        "disabled": (0, 0),
        "failed": (0, 0),
    }

    startup_calls: list[str] = []
    monkeypatch.setattr(service, "_schedule_startup_hook", lambda plugin: startup_calls.append(plugin.id))

    summary = service.refresh_runtime()

    assert summary["added"] == ["new"]
    assert summary["removed"] == ["old"]
    assert "changed-active" in summary["reloaded"]
    assert "changed-discovered" in summary["reloaded"]
    assert "failed" in summary["failed"]
    assert "old" in router.unmounted_plugins
    assert "new" in startup_calls

    assert service._plugin_fingerprint(None) == (0, 0)

    pycache = tmp_path / "cache-test" / "__pycache__"
    pycache.mkdir(parents=True)
    (pycache / "x.pyc").write_text("cache", encoding="utf-8")
    regular = tmp_path / "cache-test" / "real.py"
    regular.write_text("print('ok')", encoding="utf-8")
    count, _mtime = service._plugin_fingerprint(regular.parent)
    assert count == 1

    async def _cancel_sleep(_seconds: float) -> None:
        raise asyncio.CancelledError()

    monkeypatch.setattr(asyncio, "sleep", _cancel_sleep)
    with pytest.raises(asyncio.CancelledError):
        await service.watch_loop(interval_sec=0.01)
