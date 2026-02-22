from __future__ import annotations

import asyncio
import ipaddress
import json
from pathlib import Path

import pytest
import service.lan_scan.service as lan_scan_module
from db.models import LanScanSnapshot
from db.repositories import LanScanSnapshotRepository
from db.session import build_sqlite_engine
from faker import Faker
from scheme.dashboard import LanHttpService, LanScanResult
from service.config_service import DashboardConfigService
from service.lan_scan import LanScanService
from service.lan_scan.settings import LanScanSettings
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker
from support.factories import LAN_SCAN_PORT_FACTORY, build_dashboard_config, write_dashboard_yaml

pytestmark = pytest.mark.asyncio


def _lan_scan_settings(result_file: Path, *, enabled: bool = True, run_on_startup: bool = False) -> LanScanSettings:
    return LanScanSettings(
        enabled=enabled,
        run_on_startup=run_on_startup,
        interval_sec=30,
        connect_timeout_sec=0.1,
        http_verify_tls=True,
        max_parallel=16,
        max_hosts=32,
        ports=(80,),
        cidrs=("192.168.10.0/30",),
        result_file=result_file.resolve(),
    )


def _build_snapshot_repository(tmp_path: Path) -> tuple[LanScanSnapshotRepository, Engine]:
    engine = build_sqlite_engine((tmp_path / "dashboard.sqlite3").resolve())
    LanScanSnapshot.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return LanScanSnapshotRepository(session_factory), engine


async def test_lan_scan_service_start_stop_lifecycle(tmp_path: Path, fake: Faker) -> None:
    config_path = (tmp_path / "dashboard.yaml").resolve()
    write_dashboard_yaml(config_path, build_dashboard_config(fake))
    config_service = DashboardConfigService(config_path=config_path)

    service = LanScanService(
        config_service=config_service,
        settings=_lan_scan_settings((tmp_path / "lan_scan_result.json").resolve()),
    )

    await service.start()
    assert service._periodic_task is not None
    assert not service._periodic_task.done()

    await service.stop()
    assert service._periodic_task is None
    assert service.state().next_run_at is None


async def test_lan_scan_service_disabled_flags_skip_start_and_trigger(tmp_path: Path, fake: Faker) -> None:
    config_path = (tmp_path / "dashboard.yaml").resolve()
    write_dashboard_yaml(config_path, build_dashboard_config(fake))
    config_service = DashboardConfigService(config_path=config_path)
    service = LanScanService(
        config_service=config_service,
        settings=_lan_scan_settings((tmp_path / "lan_scan_result.json").resolve(), enabled=False),
    )
    await service.start()
    assert service._periodic_task is None
    assert await service.trigger_scan() is False


async def test_lan_scan_service_sets_queue_when_already_running(tmp_path: Path, fake: Faker) -> None:
    config_path = (tmp_path / "dashboard.yaml").resolve()
    write_dashboard_yaml(config_path, build_dashboard_config(fake))
    config_service = DashboardConfigService(config_path=config_path)
    service = LanScanService(
        config_service=config_service,
        settings=_lan_scan_settings((tmp_path / "lan_scan_result.json").resolve()),
    )
    service._run_task = asyncio.create_task(asyncio.sleep(0.1))
    accepted = await service.trigger_scan()
    assert accepted is False
    assert service._pending_trigger is True
    await service._run_task


async def test_lan_scan_service_stop_skips_queued_rerun_on_shutdown(
    tmp_path: Path,
    fake: Faker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = (tmp_path / "dashboard.yaml").resolve()
    write_dashboard_yaml(config_path, build_dashboard_config(fake))
    config_service = DashboardConfigService(config_path=config_path)
    service = LanScanService(
        config_service=config_service,
        settings=_lan_scan_settings((tmp_path / "lan_scan_result.json").resolve()),
    )

    monkeypatch.setattr(
        lan_scan_module,
        "resolve_networks",
        lambda _: [ipaddress.ip_network("192.168.10.0/30")],
    )
    monkeypatch.setattr(
        lan_scan_module,
        "enumerate_hosts",
        lambda _networks, max_hosts: ["192.168.10.2", "192.168.10.3"],
    )
    monkeypatch.setattr(lan_scan_module, "dashboard_services_by_ip", lambda *_: {})
    monkeypatch.setattr(lan_scan_module, "resolve_mac_addresses", lambda *_: {})

    async def fake_scan_open_ports(*_: object, **__: object) -> dict[str, list]:
        await asyncio.sleep(60)
        return {}

    async def fake_probe_http_services(*_: object, **__: object) -> dict[str, list[LanHttpService]]:
        return {}

    async def fake_resolve_hostnames(*_: object, **__: object) -> dict[str, str]:
        return {}

    monkeypatch.setattr(lan_scan_module, "scan_open_ports", fake_scan_open_ports)
    monkeypatch.setattr(lan_scan_module, "probe_http_services", fake_probe_http_services)
    monkeypatch.setattr(lan_scan_module, "resolve_hostnames_with_services", fake_resolve_hostnames)

    accepted = await service.trigger_scan()
    assert accepted is True
    await asyncio.sleep(0)

    queued = await service.trigger_scan()
    assert queued is False
    assert service._pending_trigger is True

    await asyncio.wait_for(service.stop(), timeout=1.0)
    assert service._run_task is None
    assert service._pending_trigger is False
    assert service.state().running is False


async def test_lan_scan_service_stream_subscriber_receives_snapshot(tmp_path: Path, fake: Faker) -> None:
    config_path = (tmp_path / "dashboard.yaml").resolve()
    write_dashboard_yaml(config_path, build_dashboard_config(fake))
    config_service = DashboardConfigService(config_path=config_path)
    service = LanScanService(
        config_service=config_service,
        settings=_lan_scan_settings((tmp_path / "lan_scan_result.json").resolve()),
    )

    queue = service.subscribe_events()
    event = queue.get_nowait()
    assert event.type == "snapshot"
    assert event.state.running is False
    service.unsubscribe_events(queue)


async def test_lan_scan_service_trigger_scan_collects_and_persists_result(
    tmp_path: Path,
    fake: Faker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = (tmp_path / "dashboard.yaml").resolve()
    write_dashboard_yaml(config_path, build_dashboard_config(fake))
    config_service = DashboardConfigService(config_path=config_path)
    result_path = (tmp_path / "lan_scan_result.json").resolve()

    monkeypatch.setattr(
        lan_scan_module,
        "resolve_networks",
        lambda _: [ipaddress.ip_network("192.168.10.0/30")],
    )
    monkeypatch.setattr(lan_scan_module, "enumerate_hosts", lambda _, max_hosts: ["192.168.10.2"])
    monkeypatch.setattr(lan_scan_module, "dashboard_services_by_ip", lambda *_: {})
    monkeypatch.setattr(lan_scan_module, "resolve_mac_addresses", lambda *_: {"192.168.10.2": "AA:BB:CC:DD:EE:FF"})

    async def fake_scan_open_ports(*_: object, **__: object) -> dict[str, list]:
        return {"192.168.10.2": [LAN_SCAN_PORT_FACTORY.build(port=80, service="http")]}

    async def fake_probe_http_services(*_: object, **__: object) -> dict[str, list[LanHttpService]]:
        return {
            "192.168.10.2": [
                LanHttpService(
                    port=80,
                    scheme="http",
                    url="http://192.168.10.2/",
                    status_code=200,
                    title="Service",
                )
            ]
        }

    async def fake_resolve_hostnames(*_: object, **__: object) -> dict[str, str]:
        return {"192.168.10.2": "node-1"}

    monkeypatch.setattr(lan_scan_module, "scan_open_ports", fake_scan_open_ports)
    monkeypatch.setattr(lan_scan_module, "probe_http_services", fake_probe_http_services)
    monkeypatch.setattr(lan_scan_module, "resolve_hostnames_with_services", fake_resolve_hostnames)

    service = LanScanService(
        config_service=config_service,
        settings=_lan_scan_settings(result_path),
    )

    accepted = await service.trigger_scan()
    assert accepted is True
    assert service._run_task is not None

    await asyncio.wait_for(service._run_task, timeout=1.0)
    state = service.state()

    assert state.running is False
    assert state.last_error is None
    assert state.result is not None
    assert state.result.scanned_hosts == 1
    assert state.result.hosts[0].ip == "192.168.10.2"


async def test_lan_scan_service_emits_host_events_while_running(
    tmp_path: Path,
    fake: Faker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = (tmp_path / "dashboard.yaml").resolve()
    write_dashboard_yaml(config_path, build_dashboard_config(fake))
    config_service = DashboardConfigService(config_path=config_path)
    result_path = (tmp_path / "lan_scan_result.json").resolve()

    monkeypatch.setattr(
        lan_scan_module,
        "resolve_networks",
        lambda _: [ipaddress.ip_network("192.168.10.0/30")],
    )
    monkeypatch.setattr(
        lan_scan_module,
        "enumerate_hosts",
        lambda _networks, max_hosts: ["192.168.10.2", "192.168.10.3"],
    )
    monkeypatch.setattr(lan_scan_module, "dashboard_services_by_ip", lambda *_: {})
    monkeypatch.setattr(lan_scan_module, "resolve_mac_addresses", lambda *_: {})

    async def fake_resolve_hostnames(*_: object, **__: object) -> dict[str, str]:
        return {}

    monkeypatch.setattr(lan_scan_module, "resolve_hostnames_with_services", fake_resolve_hostnames)

    async def fake_scan_open_ports(
        host_ips: list[str],
        _settings: LanScanSettings,
        *,
        on_host_scanned=None,
    ) -> dict[str, list]:
        if on_host_scanned is not None:
            await on_host_scanned(host_ips[0], [LAN_SCAN_PORT_FACTORY.build(port=22, service="ssh")])
            await on_host_scanned(host_ips[1], [])
        return {host_ips[0]: [LAN_SCAN_PORT_FACTORY.build(port=22, service="ssh")]}

    async def fake_probe_http_services(*_: object, **__: object) -> dict[str, list[LanHttpService]]:
        return {}

    monkeypatch.setattr(lan_scan_module, "scan_open_ports", fake_scan_open_ports)
    monkeypatch.setattr(lan_scan_module, "probe_http_services", fake_probe_http_services)

    service = LanScanService(
        config_service=config_service,
        settings=_lan_scan_settings(result_path),
    )
    queue = service.subscribe_events()
    try:
        accepted = await service.trigger_scan()
        assert accepted is True
        assert service._run_task is not None
        await asyncio.wait_for(service._run_task, timeout=1.0)

        events = []
        while not queue.empty():
            events.append(queue.get_nowait())

        event_types = [event.type for event in events]
        assert "scan_started" in event_types
        assert "host_found" in event_types
        assert "scan_completed" in event_types
    finally:
        service.unsubscribe_events(queue)


async def test_lan_scan_service_persists_snapshot_in_repository(
    tmp_path: Path,
    fake: Faker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = (tmp_path / "dashboard.yaml").resolve()
    write_dashboard_yaml(config_path, build_dashboard_config(fake))
    config_service = DashboardConfigService(config_path=config_path)
    result_path = (tmp_path / "lan_scan_result.json").resolve()
    snapshot_repository, engine = _build_snapshot_repository(tmp_path)

    monkeypatch.setattr(
        lan_scan_module,
        "resolve_networks",
        lambda _: [ipaddress.ip_network("192.168.10.0/30")],
    )
    monkeypatch.setattr(lan_scan_module, "enumerate_hosts", lambda _, max_hosts: ["192.168.10.2"])
    monkeypatch.setattr(lan_scan_module, "dashboard_services_by_ip", lambda *_: {})
    monkeypatch.setattr(lan_scan_module, "resolve_mac_addresses", lambda *_: {"192.168.10.2": "AA:BB:CC:DD:EE:FF"})

    async def fake_scan_open_ports(*_: object, **__: object) -> dict[str, list]:
        return {"192.168.10.2": [LAN_SCAN_PORT_FACTORY.build(port=80, service="http")]}

    async def fake_probe_http_services(*_: object, **__: object) -> dict[str, list[LanHttpService]]:
        return {
            "192.168.10.2": [
                LanHttpService(
                    port=80,
                    scheme="http",
                    url="http://192.168.10.2/",
                    status_code=200,
                    title="Service",
                )
            ]
        }

    async def fake_resolve_hostnames(*_: object, **__: object) -> dict[str, str]:
        return {"192.168.10.2": "node-1"}

    monkeypatch.setattr(lan_scan_module, "scan_open_ports", fake_scan_open_ports)
    monkeypatch.setattr(lan_scan_module, "probe_http_services", fake_probe_http_services)
    monkeypatch.setattr(lan_scan_module, "resolve_hostnames_with_services", fake_resolve_hostnames)

    try:
        service = LanScanService(
            config_service=config_service,
            settings=_lan_scan_settings(result_path),
            snapshot_repository=snapshot_repository,
        )

        accepted = await service.trigger_scan()
        assert accepted is True
        assert service._run_task is not None

        await asyncio.wait_for(service._run_task, timeout=1.0)
        latest = snapshot_repository.fetch_latest()
        assert latest is not None
        assert "192.168.10.2" in latest.payload_json
    finally:
        engine.dispose()


async def test_lan_scan_service_loads_last_result_from_repository(tmp_path: Path, fake: Faker) -> None:
    config_path = (tmp_path / "dashboard.yaml").resolve()
    write_dashboard_yaml(config_path, build_dashboard_config(fake))
    config_service = DashboardConfigService(config_path=config_path)
    result_path = (tmp_path / "lan_scan_result.json").resolve()
    snapshot_repository, engine = _build_snapshot_repository(tmp_path)

    try:
        result = LanScanResult(
            generated_at=lan_scan_module._utc_now(),
            duration_ms=50,
            scanned_hosts=1,
            scanned_ports=1,
            scanned_cidrs=["192.168.10.0/30"],
            hosts=[],
            source_file=str(result_path),
        )
        snapshot_repository.save_snapshot(
            generated_at=result.generated_at,
            payload_json=json.dumps(result.model_dump(mode="json"), ensure_ascii=False),
        )

        service = LanScanService(
            config_service=config_service,
            settings=_lan_scan_settings(result_path),
            snapshot_repository=snapshot_repository,
        )

        state = service.state()
        assert state.result is not None
        assert state.result.scanned_hosts == 1
        assert state.result.duration_ms == 50
    finally:
        engine.dispose()


async def test_lan_scan_service_reports_failed_stage_in_last_error(
    tmp_path: Path,
    fake: Faker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = (tmp_path / "dashboard.yaml").resolve()
    write_dashboard_yaml(config_path, build_dashboard_config(fake))
    config_service = DashboardConfigService(config_path=config_path)
    result_path = (tmp_path / "lan_scan_result.json").resolve()

    monkeypatch.setattr(
        lan_scan_module,
        "resolve_networks",
        lambda _: [ipaddress.ip_network("192.168.10.0/30")],
    )
    monkeypatch.setattr(
        lan_scan_module,
        "enumerate_hosts",
        lambda *_args, **_kwargs: ["192.168.10.2"],
    )

    async def fail_scan_open_ports(*_: object, **__: object) -> dict[str, list]:
        raise RuntimeError("socket unavailable")

    monkeypatch.setattr(lan_scan_module, "scan_open_ports", fail_scan_open_ports)

    service = LanScanService(
        config_service=config_service,
        settings=_lan_scan_settings(result_path),
    )

    accepted = await service.trigger_scan()
    assert accepted is True
    assert service._run_task is not None

    await asyncio.wait_for(service._run_task, timeout=1.0)
    state = service.state()

    assert state.running is False
    assert state.last_error is not None
    assert state.last_error.startswith("scan_ports:")
