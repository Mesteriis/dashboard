from __future__ import annotations

from plugins.autodiscover.services import extract_services_from_scan_payload


def test_extract_services_returns_empty_for_invalid_payload_shapes() -> None:
    assert extract_services_from_scan_payload(None) == []
    assert extract_services_from_scan_payload({"result": {"hosts": "not-a-list"}}) == []
    assert extract_services_from_scan_payload({"result": "not-a-dict", "hosts": "not-a-list"}) == []


def test_extract_services_parses_and_sorts_with_http_enrichment() -> None:
    payload = {
        "result": {
            "hosts": [
                "skip-non-dict-host",
                {
                    "ip": " 10.0.0.5 ",
                    "hostname": " gateway ",
                    "mac_address": " aa:bb:cc ",
                    "vendor": " ACME ",
                    "device_type": " appliance ",
                    "http_services": [
                        "skip-non-dict-http",
                        {"port": 80, "title": "Admin", "url": "http://10.0.0.5:80", "server": "nginx"},
                        {"port": "443", "title": "skip-non-int-port"},
                    ],
                    "open_ports": [
                        "skip-non-dict-port",
                        {"port": "22", "service": "skip-non-int-port"},
                        {"port": 80, "service": "http"},
                        {"port": 22, "service": "ssh"},
                    ],
                },
                {
                    "ip": "10.0.0.4",
                    "open_ports": "skip-non-list-open-ports",
                },
                {
                    "ip": "10.0.0.3",
                    "host_mac": "11:22:33:44:55:66",
                    "mac_vendor": "VendorX",
                    "open_ports": [{"port": 53, "service": "dns"}],
                },
            ]
        }
    }

    rows = extract_services_from_scan_payload(payload)
    assert [(row["host_ip"], row["port"]) for row in rows] == [
        ("10.0.0.3", 53),
        ("10.0.0.5", 22),
        ("10.0.0.5", 80),
    ]

    ssh_row = rows[1]
    assert ssh_row["hostname"] == "gateway"
    assert ssh_row["host_mac"] == "aa:bb:cc"
    assert ssh_row["mac_vendor"] == "ACME"
    assert ssh_row["device_type"] == "appliance"
    assert ssh_row["title"] is None
    assert ssh_row["url"] is None

    http_row = rows[2]
    assert http_row["title"] == "Admin"
    assert http_row["url"] == "http://10.0.0.5:80"
    assert http_row["server"] == "nginx"


def test_extract_services_uses_root_payload_when_result_is_not_dict() -> None:
    payload = {
        "result": "ignored",
        "hosts": [{"ip": "1.1.1.1", "open_ports": [{"port": 443, "service": "https"}]}],
    }
    rows = extract_services_from_scan_payload(payload)
    assert len(rows) == 1
    assert rows[0]["host_ip"] == "1.1.1.1"
    assert rows[0]["port"] == 443
