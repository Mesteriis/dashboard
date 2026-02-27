from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.skip(
    reason="features.autodiscover module not yet implemented",
)

try:
    from features.autodiscover import plugin as autodiscover
except ImportError:
    autodiscover = None  # type: ignore[assignment]


def test_parse_ports_and_cidrs_helpers() -> None:
    ports = autodiscover._parse_ports("22,80,80,100-102,bad")
    cidrs = autodiscover._parse_cidrs("192.168.1.10/24,10.0.0.1/24,not-cidr")
    default_ports = autodiscover._parse_ports(None)
    ranged_ports = autodiscover._parse_ports(None, default_start=7, default_end=9)

    assert ports == (22, 80, 100, 101, 102)
    assert cidrs == ("192.168.1.0/24", "10.0.0.0/24")
    assert default_ports[0] == 1
    assert default_ports[-1] == 20_000
    assert len(default_ports) == 20_000
    assert ranged_ports == (7, 8, 9)


def test_detect_default_cidrs_merges_sources_and_has_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        autodiscover,
        "_detect_cidrs_from_ip_addr",
        lambda: ("192.168.1.0/24", "10.0.0.0/24"),
    )
    monkeypatch.setattr(
        autodiscover,
        "_detect_cidrs_from_ifconfig",
        lambda: ("10.0.0.0/24", "172.16.0.0/24"),
    )
    monkeypatch.setattr(
        autodiscover,
        "_detect_cidrs_from_udp_probe",
        lambda: ("192.168.1.0/24",),
    )

    assert autodiscover.detect_default_cidrs() == (
        "192.168.1.0/24",
        "10.0.0.0/24",
        "172.16.0.0/24",
    )

    monkeypatch.setattr(autodiscover, "_detect_cidrs_from_ip_addr", lambda: ())
    monkeypatch.setattr(autodiscover, "_detect_cidrs_from_ifconfig", lambda: ())
    monkeypatch.setattr(autodiscover, "_detect_cidrs_from_udp_probe", lambda: ())

    assert autodiscover.detect_default_cidrs() == ("192.168.1.0/24",)


def test_dashboard_mapping_and_device_type_classification() -> None:
    config_snapshot = {
        "groups": [
            {
                "subgroups": [
                    {
                        "items": [
                            {
                                "id": "svc-a",
                                "title": "Proxmox UI",
                                "url": "https://192.168.10.2:8006/",
                            },
                            {
                                "id": "svc-b",
                                "title": "External",
                                "url": "https://8.8.8.8/",
                            },
                        ]
                    }
                ]
            }
        ]
    }

    mapping = autodiscover.dashboard_services_by_ip(config_snapshot)
    assert list(mapping) == ["192.168.10.2"]
    assert [entry["id"] for entry in mapping["192.168.10.2"]] == ["svc-a"]

    device_type = autodiscover.detect_device_type(
        hostname="node-1",
        vendor="VMware",
        open_ports=[{"port": 8006, "service": "proxmox"}],
        dashboard_items=mapping["192.168.10.2"],
    )
    assert device_type == "Hypervisor"


def test_hostname_and_mac_fallback_helpers() -> None:
    hostname = autodiscover.hostname_from_dashboard_items(
        "192.168.10.2",
        [
            {
                "id": "svc-a",
                "title": "OpenWrt Router",
                "url": "http://192.168.10.2/",
            }
        ],
    )
    assert hostname == "openwrt"
    assert autodiscover.normalize_mac("bc:24:11:4:2:ed") == "BC:24:11:04:02:ED"


def test_load_last_result_backfills_services_and_tls_hostname(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result_file = (tmp_path / "autodiscover_result.json").resolve()
    result_file.write_text(
        json.dumps(
            {
                "generated_at": "2026-01-01T00:00:00Z",
                "duration_ms": 5,
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
                        "http_services": [
                            {
                                "port": 8006,
                                "scheme": "https",
                                "url": "https://192.168.1.2:8006/",
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        autodiscover,
        "hostname_from_tls_services",
        lambda ip, services: "pve.local" if ip == "192.168.1.2" else None,
    )

    loaded = autodiscover.load_last_result(result_file)
    assert loaded is not None
    host = loaded["hosts"][0]
    assert host["open_ports"][0]["service"] == "ollama"
    assert host["hostname"] == "pve.local"


@pytest.mark.asyncio
async def test_execute_scan_filters_dashboard_mapping_to_scan_targets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result_file = (tmp_path / "autodiscover_result.json").resolve()

    async def fake_scan_open_ports(host_ips, request, *, on_host_scanned=None, on_service_found=None):
        assert host_ips == ["192.168.10.2"]
        if on_host_scanned is not None:
            await on_host_scanned("192.168.10.2", [])
        return {}

    async def fake_probe_http_services(*_args, **_kwargs):
        return {}

    async def fake_resolve_hostnames(*_args, **_kwargs):
        return {}

    monkeypatch.setattr(autodiscover, "scan_open_ports", fake_scan_open_ports)
    monkeypatch.setattr(autodiscover, "probe_http_services", fake_probe_http_services)
    monkeypatch.setattr(autodiscover, "resolve_hostnames_with_services", fake_resolve_hostnames)
    monkeypatch.setattr(autodiscover, "resolve_mac_addresses", lambda *_args, **_kwargs: {})

    result = await autodiscover.execute_scan(
        payload={
            "hosts": ["192.168.10.2"],
            "ports": [22],
            "result_file": str(result_file),
            "config_snapshot": {
                "groups": [
                    {
                        "subgroups": [
                            {
                                "items": [
                                    {
                                        "id": "svc-target",
                                        "title": "OpenWrt Router",
                                        "url": "http://192.168.10.2/",
                                    },
                                    {
                                        "id": "svc-other",
                                        "title": "Other Host",
                                        "url": "http://192.168.10.99/",
                                    },
                                ]
                            }
                        ]
                    }
                ]
            },
        },
        dry_run=False,
    )

    hosts = result["hosts"]
    assert len(hosts) == 1
    assert hosts[0]["ip"] == "192.168.10.2"
    assert hosts[0]["hostname"] == "openwrt"


@pytest.mark.asyncio
async def test_execute_scan_full_pipeline_with_progress_events(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result_file = (tmp_path / "autodiscover_result.json").resolve()

    async def fake_scan_open_ports(host_ips, request, *, on_host_scanned=None, on_service_found=None):
        assert host_ips == ["192.168.10.1", "192.168.10.2"]
        open_ports = [{"port": 22, "service": "ssh"}, {"port": 8006, "service": "proxmox"}]
        if on_service_found is not None:
            await on_service_found("192.168.10.2", {"port": 22, "service": "ssh"})
            await on_service_found("192.168.10.2", {"port": 8006, "service": "proxmox"})
        if on_host_scanned is not None:
            await on_host_scanned("192.168.10.2", open_ports)
            await on_host_scanned("192.168.10.1", [])
        return {"192.168.10.2": open_ports}

    async def fake_probe_http_services(open_ports_map, request):
        assert "192.168.10.2" in open_ports_map
        return {
            "192.168.10.2": [
                {
                    "port": 8006,
                    "scheme": "https",
                    "url": "https://192.168.10.2:8006/",
                    "status_code": 200,
                    "title": "Proxmox",
                    "description": "hypervisor",
                    "server": "pveproxy",
                    "error": None,
                }
            ]
        }

    async def fake_resolve_hostnames(ips, http_services_map):
        assert ips == ["192.168.10.2"]
        return {"192.168.10.2": "pve.local"}

    monkeypatch.setattr(autodiscover, "scan_open_ports", fake_scan_open_ports)
    monkeypatch.setattr(autodiscover, "probe_http_services", fake_probe_http_services)
    monkeypatch.setattr(autodiscover, "resolve_hostnames_with_services", fake_resolve_hostnames)
    monkeypatch.setattr(
        autodiscover,
        "resolve_mac_addresses",
        lambda ips: {"192.168.10.2": "00:0C:29:AA:BB:CC"},
    )

    progress_events: list[tuple[str, dict[str, object]]] = []

    async def on_progress(event_type: str, payload: dict[str, object]) -> None:
        progress_events.append((event_type, payload))

    result = await autodiscover.execute_scan(
        payload={
            "hosts": ["192.168.10.1", "192.168.10.2"],
            "ports": [22, 8006],
            "max_hosts": 8,
            "result_file": str(result_file),
            "config_snapshot": {
                "groups": [
                    {
                        "subgroups": [
                            {
                                "items": [
                                    {
                                        "id": "svc-proxmox",
                                        "title": "Proxmox UI",
                                        "url": "https://192.168.10.2:8006/",
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
        },
        dry_run=False,
        progress_callback=on_progress,
    )

    assert result["plugin"] == "autodiscover"
    assert result["action"] == "autodiscover.scan"
    assert result["summary"]["targets_total"] == 2
    assert result["summary"]["targets_scanned"] == 2
    assert result["summary"]["discovered_hosts"] == 1

    host = result["hosts"][0]
    assert host["ip"] == "192.168.10.2"
    assert host["hostname"] == "pve.local"
    assert host["mac_vendor"] == "VMware"
    assert host["device_type"] == "Hypervisor"
    assert host["dashboard_items"][0]["id"] == "svc-proxmox"

    event_types = [event_type for event_type, _payload in progress_events]
    assert "host_found" in event_types
    assert "service_found" in event_types
    assert "scan_progress" in event_types

    saved = json.loads(result_file.read_text(encoding="utf-8"))
    assert saved["hosts"][0]["ip"] == "192.168.10.2"
