from __future__ import annotations

import asyncio
import ipaddress
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
import service.lan_scan.clients as clients_module
from scheme.dashboard import LanHttpService, LanScanResult, LinkItemConfig
from service.config_service import DashboardConfigValidationError
from service.lan_scan.settings import LanScanSettings
from support.factories import LAN_SCAN_PORT_FACTORY, VALIDATION_ISSUE_FACTORY


def _settings(tmp_path: Path) -> LanScanSettings:
    return LanScanSettings(
        enabled=True,
        run_on_startup=False,
        interval_sec=60,
        connect_timeout_sec=0.2,
        http_verify_tls=True,
        max_parallel=16,
        max_hosts=128,
        ports=(22, 80, 443),
        cidrs=("192.168.1.0/30",),
        result_file=(tmp_path / "lan_scan_result.json").resolve(),
    )


@pytest.mark.asyncio
async def test_scan_open_ports_detects_open_ports(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class DummyWriter:
        async def wait_closed(self) -> None:
            return None

        def close(self) -> None:
            return None

    async def fake_open_connection(ip: str, port: int) -> tuple[object, DummyWriter]:
        if port == 80:
            return object(), DummyWriter()
        raise OSError("closed")

    monkeypatch.setattr(clients_module.asyncio, "open_connection", fake_open_connection)

    result = await clients_module.scan_open_ports(["192.168.1.10"], _settings(tmp_path))
    assert list(result) == ["192.168.1.10"]
    assert [entry.port for entry in result["192.168.1.10"]] == [80]


@pytest.mark.asyncio
async def test_scan_open_ports_invokes_progress_callback(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class DummyWriter:
        async def wait_closed(self) -> None:
            return None

        def close(self) -> None:
            return None

    async def fake_open_connection(ip: str, port: int) -> tuple[object, DummyWriter]:
        if ip.endswith(".10") and port == 80:
            return object(), DummyWriter()
        raise OSError("closed")

    scanned: list[tuple[str, list[int]]] = []

    async def on_host_scanned(ip: str, ports: list) -> None:
        scanned.append((ip, [entry.port for entry in ports]))

    monkeypatch.setattr(clients_module.asyncio, "open_connection", fake_open_connection)

    await clients_module.scan_open_ports(
        ["192.168.1.10", "192.168.1.11"],
        _settings(tmp_path),
        on_host_scanned=on_host_scanned,
    )
    assert dict(scanned) == {
        "192.168.1.10": [80],
        "192.168.1.11": [],
    }


@pytest.mark.asyncio
async def test_scan_open_ports_reports_hosts_as_completed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class DummyWriter:
        async def wait_closed(self) -> None:
            return None

        def close(self) -> None:
            return None

    async def fake_open_connection(ip: str, port: int) -> tuple[object, DummyWriter]:
        if ip.endswith(".10"):
            await asyncio.sleep(0.03)
        if port == 80:
            return object(), DummyWriter()
        raise OSError("closed")

    progress_order: list[str] = []

    async def on_host_scanned(ip: str, _ports: list) -> None:
        progress_order.append(ip)

    monkeypatch.setattr(clients_module.asyncio, "open_connection", fake_open_connection)

    await clients_module.scan_open_ports(
        ["192.168.1.10", "192.168.1.11"],
        _settings(tmp_path),
        on_host_scanned=on_host_scanned,
    )

    assert progress_order == ["192.168.1.11", "192.168.1.10"]


@pytest.mark.asyncio
async def test_probe_http_port_success_and_fallbacks() -> None:
    request = httpx.Request("GET", "http://192.168.1.10:80/")
    response = httpx.Response(
        status_code=200,
        request=request,
        headers={"content-type": "text/html", "server": "nginx"},
        text="<title>Demo</title><meta name='description' content='ok'>",
    )

    class SuccessClient:
        async def get(self, url: str) -> httpx.Response:
            return response

    success = await clients_module._probe_http_port(SuccessClient(), ip="192.168.1.10", port=80)
    assert success is not None
    assert success.title == "Demo"

    class ErrorClient:
        async def get(self, url: str) -> httpx.Response:
            raise httpx.ConnectError("boom")

    expected_error = await clients_module._probe_http_port(ErrorClient(), ip="192.168.1.10", port=80)
    assert expected_error is not None
    assert expected_error.error is not None

    unexpected = await clients_module._probe_http_port(ErrorClient(), ip="192.168.1.10", port=5432)
    assert unexpected is None


@pytest.mark.asyncio
async def test_probe_http_services_groups_and_sorts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class FakeAsyncClient:
        def __init__(self, **_: object) -> None:
            pass

        async def __aenter__(self) -> FakeAsyncClient:
            return self

        async def __aexit__(self, _exc_type: object, exc: object, _tb: object) -> None:
            return None

    async def fake_probe(client: object, *, ip: str, port: int) -> LanHttpService | None:
        if port == 8080:
            return None
        return LanHttpService(port=port, scheme="http", url=f"http://{ip}:{port}/", status_code=200)

    monkeypatch.setattr(clients_module.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(clients_module, "_probe_http_port", fake_probe)

    open_ports = {
        "192.168.1.2": [
            LAN_SCAN_PORT_FACTORY.build(port=443, service="https"),
            LAN_SCAN_PORT_FACTORY.build(port=8080),
        ],
        "192.168.1.3": [LAN_SCAN_PORT_FACTORY.build(port=22, service="ssh")],
    }
    grouped = await clients_module.probe_http_services(open_ports, _settings(tmp_path))
    assert list(grouped) == ["192.168.1.2"]
    assert [service.port for service in grouped["192.168.1.2"]] == [443]


@pytest.mark.asyncio
async def test_resolve_hostnames_uses_safe_reverse_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(clients_module, "safe_reverse_dns", lambda ip: "host-1" if ip.endswith(".1") else None)
    resolved = await clients_module.resolve_hostnames(["192.168.1.1", "192.168.1.2"])
    assert resolved == {"192.168.1.1": "host-1"}


@pytest.mark.asyncio
async def test_resolve_hostnames_falls_back_to_tls_certificate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(clients_module, "safe_reverse_dns", lambda ip: None)
    monkeypatch.setattr(
        clients_module,
        "hostname_from_tls_services",
        lambda ip, services: "pve.local" if ip == "192.168.1.2" and services else None,
    )

    resolved = await clients_module.resolve_hostnames_with_services(
        ["192.168.1.2", "192.168.1.3"],
        {
            "192.168.1.2": [LanHttpService(port=8006, scheme="https", url="https://192.168.1.2:8006/")],
            "192.168.1.3": [LanHttpService(port=19999, scheme="http", url="http://192.168.1.3:19999/")],
        },
    )
    assert resolved == {"192.168.1.2": "pve.local"}


def test_safe_reverse_dns_returns_none_on_oserror(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(clients_module.socket, "gethostbyaddr", lambda ip: (_ for _ in ()).throw(OSError("x")))
    assert clients_module.safe_reverse_dns("192.168.1.1") is None


def test_hostname_from_tls_services_uses_https_ports_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        clients_module,
        "hostname_from_tls_certificate",
        lambda ip, port: "secure-host" if port == 8443 else None,
    )
    hostname = clients_module.hostname_from_tls_services(
        "192.168.1.10",
        [
            LanHttpService(port=8080, scheme="http", url="http://192.168.1.10:8080/"),
            LanHttpService(port=8443, scheme="https", url="https://192.168.1.10:8443/"),
        ],
    )
    assert hostname == "secure-host"


def test_detect_default_cidrs_success_and_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(clients_module, "_detect_cidrs_from_ip_addr", lambda: ())
    monkeypatch.setattr(clients_module, "_detect_cidrs_from_ifconfig", lambda: ())

    class SocketOK:
        def __enter__(self) -> SocketOK:
            return self

        def __exit__(self, _exc_type: object, exc: object, _tb: object) -> None:
            return None

        def connect(self, _target: tuple[str, int]) -> None:
            return None

        def getsockname(self) -> tuple[str, int]:
            return ("192.168.5.7", 1000)

    monkeypatch.setattr(clients_module.socket, "socket", lambda *_args, **_kwargs: SocketOK())
    assert clients_module.detect_default_cidrs() == ("192.168.5.0/24",)

    class SocketFail:
        def __enter__(self) -> SocketFail:
            raise OSError("fail")

        def __exit__(self, _exc_type: object, exc: object, _tb: object) -> None:
            return None

    monkeypatch.setattr(clients_module.socket, "socket", lambda *_args, **_kwargs: SocketFail())
    assert clients_module.detect_default_cidrs() == ("192.168.1.0/24",)


def test_detect_default_cidrs_merges_multiple_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(clients_module, "_detect_cidrs_from_ip_addr", lambda: ("192.168.1.0/24", "10.0.0.0/24"))
    monkeypatch.setattr(
        clients_module,
        "_detect_cidrs_from_ifconfig",
        lambda: ("10.0.0.0/24", "172.16.0.0/24"),
    )
    monkeypatch.setattr(clients_module, "_detect_cidrs_from_udp_probe", lambda: ("192.168.1.0/24",))

    assert clients_module.detect_default_cidrs() == (
        "192.168.1.0/24",
        "10.0.0.0/24",
        "172.16.0.0/24",
    )


def test_resolve_networks_and_enumerate_hosts() -> None:
    networks = clients_module.resolve_networks(("192.168.1.0/30", "invalid"))
    assert networks == [ipaddress.ip_network("192.168.1.0/30")]
    assert clients_module.resolve_networks(("bad",)) == [ipaddress.IPv4Network("192.168.1.0/24")]
    hosts = clients_module.enumerate_hosts(networks, max_hosts=1)
    assert hosts == ["192.168.1.1"]


def test_enumerate_hosts_balances_across_multiple_networks() -> None:
    networks = [
        ipaddress.ip_network("192.168.1.0/30"),
        ipaddress.ip_network("10.0.0.0/30"),
    ]
    hosts = clients_module.enumerate_hosts(networks, max_hosts=3)
    assert hosts == ["192.168.1.1", "10.0.0.1", "192.168.1.2"]


def test_read_arp_table_parses_ip_neigh_and_arp(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command: tuple[str, ...], **_: object) -> SimpleNamespace:
        if command[0] == "ip":
            return SimpleNamespace(stdout="192.168.1.10 dev en0 lladdr aa:bb:cc:dd:ee:ff REACHABLE\n")
        return SimpleNamespace(stdout="? (192.168.1.11) at 11:22:33:44:55:66 on en0 ifscope [ethernet]\n")

    monkeypatch.setattr(clients_module.subprocess, "run", fake_run)
    table = clients_module.read_arp_table()
    assert table["192.168.1.10"] == "AA:BB:CC:DD:EE:FF"
    assert table["192.168.1.11"] == "11:22:33:44:55:66"


def test_read_arp_table_ignores_command_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        clients_module.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(FileNotFoundError("missing")),
    )
    assert clients_module.read_arp_table() == {}


def test_resolve_mac_addresses_filters_only_requested_ips(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(clients_module, "read_arp_table", lambda: {"192.168.1.10": "AA:AA:AA:AA:AA:AA"})
    assert clients_module.resolve_mac_addresses([]) == {}
    assert clients_module.resolve_mac_addresses(["192.168.1.10", "192.168.1.11"]) == {
        "192.168.1.10": "AA:AA:AA:AA:AA:AA"
    }


def test_item_ip_handles_private_public_and_hostname_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    cache: dict[str, str | None] = {}
    private_item = LinkItemConfig(id="a", type="link", title="A", url="http://192.168.1.20/")
    public_item = LinkItemConfig(id="b", type="link", title="B", url="http://8.8.8.8/")
    dns_item = LinkItemConfig(id="c", type="link", title="C", url="http://host.local/")

    monkeypatch.setattr(clients_module.socket, "gethostbyname", lambda host: "192.168.1.30")
    assert clients_module.item_ip(private_item, cache) == "192.168.1.20"
    assert clients_module.item_ip(public_item, cache) is None
    assert clients_module.item_ip(dns_item, cache) == "192.168.1.30"
    assert clients_module.item_ip(dns_item, cache) == "192.168.1.30"


def test_dashboard_services_by_ip_handles_validation_error_and_groups_by_ip() -> None:
    class BrokenConfigService:
        def list_items(self) -> list[object]:
            raise DashboardConfigValidationError([VALIDATION_ISSUE_FACTORY.build(code="err")])

    assert clients_module.dashboard_services_by_ip(BrokenConfigService()) == {}

    item1 = LinkItemConfig(id="svc-a", type="link", title="B title", url="http://192.168.1.2/")
    item2 = LinkItemConfig(id="svc-b", type="link", title="A title", url="http://192.168.1.2/")
    item3 = LinkItemConfig(id="svc-c", type="link", title="External", url="http://8.8.8.8/")

    class GoodConfigService:
        def list_items(self) -> list[LinkItemConfig]:
            return [item1, item2, item3]

    mapping = clients_module.dashboard_services_by_ip(GoodConfigService())
    assert list(mapping) == ["192.168.1.2"]
    assert [entry.title for entry in mapping["192.168.1.2"]] == ["A title", "B title"]


def test_load_last_result_and_save_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result_file = (tmp_path / "result.json").resolve()
    assert clients_module.load_last_result(result_file) is None

    monkeypatch.setattr(
        clients_module,
        "hostname_from_tls_services",
        lambda ip, services: "pve.local" if ip == "192.168.1.2" else None,
    )

    result = LanScanResult.model_validate(
        {
            "generated_at": "2026-01-01T00:00:00Z",
            "duration_ms": 10,
            "scanned_hosts": 1,
            "scanned_ports": 2,
            "scanned_cidrs": ["192.168.1.0/24"],
            "hosts": [
                {
                    "ip": "192.168.1.2",
                    "hostname": None,
                    "open_ports": [
                        {"port": 11434, "service": None},
                        {"port": 22, "service": "ssh"},
                    ],
                    "http_services": [{"port": 8006, "scheme": "https", "url": "https://192.168.1.2:8006/"}],
                }
            ],
        }
    )
    clients_module.save_result(result_file, result)
    loaded = clients_module.load_last_result(result_file)
    assert loaded is not None
    assert loaded.scanned_hosts == 1
    assert loaded.hosts[0].open_ports[0].service == "ollama"
    assert loaded.hosts[0].hostname == "pve.local"

    result_file.write_text("{bad json", encoding="utf-8")
    assert clients_module.load_last_result(result_file) is None
