from __future__ import annotations

import pytest
from support.factories import LAN_SCAN_MAPPED_SERVICE_FACTORY, LAN_SCAN_PORT_FACTORY

from service.lan_scan.parsers import detect_device_type, extract_html_metadata, mac_vendor, normalize_mac


def test_extract_html_metadata() -> None:
    title, description = extract_html_metadata(
        "<html><head><title> Demo App </title><meta name='description' content='hello world'></head></html>"
    )
    assert title == "Demo App"
    assert description == "hello world"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("aa-bb-cc-dd-ee-ff", "AA:BB:CC:DD:EE:FF"),
        ("aa:bb:cc:dd:ee:ff", "AA:BB:CC:DD:EE:FF"),
        ("invalid", None),
        (None, None),
    ],
)
def test_normalize_mac(raw: str | None, expected: str | None) -> None:
    assert normalize_mac(raw) == expected


def test_mac_vendor_resolves_known_and_locally_administered() -> None:
    assert mac_vendor("00:0C:29:AA:BB:CC") == "VMware"
    assert mac_vendor("02:AA:BB:CC:DD:EE") == "Locally Administered"
    assert mac_vendor("00:11:22:33:44:55") is None


@pytest.mark.parametrize(
    ("ports", "hostname", "vendor", "expected"),
    [
        ([8006], "node", "", "Hypervisor"),
        ([3389], "host", "", "Windows PC"),
        ([8123], "home assistant", "", "IoT Hub"),
        ([139, 445], "nas", "", "NAS/File Server"),
        ([25565], "minecraft", "", "Game Server"),
        ([5432], "db", "", "Database Server"),
        ([9200], "elastic", "", "Search Cluster"),
        ([80], "web", "", "Web Device"),
        ([22], "linux", "", "Linux/Unix Host"),
        ([], "router", "MikroTik", "Network Device"),
        ([], "pi", "Raspberry Pi Trading", "SBC/IoT Device"),
        ([50000], "custom", "", "Server/Host"),
        ([], "unknown", "", "Unknown"),
    ],
)
def test_detect_device_type_branches(
    ports: list[int],
    hostname: str,
    vendor: str,
    expected: str,
) -> None:
    device_type = detect_device_type(
        hostname=hostname,
        vendor=vendor,
        open_ports=[LAN_SCAN_PORT_FACTORY.build(port=port, service="x") for port in ports],
        dashboard_items=[LAN_SCAN_MAPPED_SERVICE_FACTORY.build(id="svc", title=hostname, url="http://192.168.1.2:8006/")],
    )
    assert device_type == expected
