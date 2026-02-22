from __future__ import annotations

import html
import re

from scheme.dashboard import LanScanMappedService, LanScanPort

TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
DESCRIPTION_RE = re.compile(
    r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
    re.IGNORECASE | re.DOTALL,
)
DESCRIPTION_RE_ALT = re.compile(
    r'<meta[^>]+content=["\'](.*?)["\'][^>]+name=["\']description["\']',
    re.IGNORECASE | re.DOTALL,
)

MAC_OUI_VENDORS = {
    "000C29": "VMware",
    "000569": "VMware",
    "005056": "VMware",
    "0003FF": "Microsoft Hyper-V",
    "00155D": "Microsoft Hyper-V",
    "080027": "Oracle VirtualBox",
    "525400": "QEMU/KVM",
    "0242AC": "Docker",
    "B827EB": "Raspberry Pi Foundation",
    "DCA632": "Raspberry Pi Trading",
    "E45F01": "Raspberry Pi Trading",
    "F4F26D": "Ubiquiti",
    "24A43C": "Ubiquiti",
    "FCECDA": "Ubiquiti",
    "D850E6": "TP-Link",
    "AC84C6": "TP-Link",
    "E894F6": "TP-Link",
    "8C3B4A": "MikroTik",
    "4C5E0C": "MikroTik",
    "FC3497": "Asus",
    "F07959": "Asus",
    "F8FFCF": "Apple",
    "3C22FB": "Apple",
    "A4C361": "Apple",
    "D8BB2C": "Apple",
    "3CD92B": "Hewlett Packard",
    "0025B3": "Dell",
    "F8B156": "Dell",
    "F4CE46": "Intel",
    "A44CC8": "Intel",
    "001A8C": "Cisco",
    "58D56E": "Huawei",
    "94D9B3": "Xiaomi",
}


def extract_html_metadata(body: str) -> tuple[str | None, str | None]:
    if not body:
        return None, None

    title: str | None = None
    description: str | None = None

    title_match = TITLE_RE.search(body)
    if title_match:
        title = html.unescape(title_match.group(1))
        title = re.sub(r"\s+", " ", title).strip()[:240] or None

    description_match = DESCRIPTION_RE.search(body) or DESCRIPTION_RE_ALT.search(body)
    if description_match:
        description = html.unescape(description_match.group(1))
        description = re.sub(r"\s+", " ", description).strip()[:800] or None

    return title, description


def normalize_mac(raw_mac: str | None) -> str | None:
    if not raw_mac:
        return None
    clean = re.sub(r"[^0-9a-fA-F]", "", raw_mac)
    if len(clean) != 12:
        return None
    chunks = [clean[index : index + 2].upper() for index in range(0, 12, 2)]
    return ":".join(chunks)


def mac_vendor(mac_address: str | None) -> str | None:
    if not mac_address:
        return None
    prefix = mac_address.replace(":", "")[:6].upper()
    vendor = MAC_OUI_VENDORS.get(prefix)
    if vendor:
        return vendor

    first_octet = int(prefix[:2], 16)
    if first_octet & 0b10:
        return "Locally Administered"
    return None


def detect_device_type(
    *,
    hostname: str | None,
    vendor: str | None,
    open_ports: list[LanScanPort],
    dashboard_items: list[LanScanMappedService],
) -> str:
    ports = {entry.port for entry in open_ports}
    text = " ".join([hostname or "", *[item.title for item in dashboard_items]]).lower()
    vendor_text = (vendor or "").lower()

    if 8006 in ports or "proxmox" in text:
        return "Hypervisor"
    if 3389 in ports or 5985 in ports or 5986 in ports:
        return "Windows PC"
    if 8123 in ports or "home assistant" in text:
        return "IoT Hub"
    if 445 in ports and 139 in ports:
        return "NAS/File Server"
    if 25565 in ports:
        return "Game Server"
    if 5432 in ports or 3306 in ports or 9042 in ports:
        return "Database Server"
    if 9200 in ports or 9300 in ports:
        return "Search Cluster"
    if any(port in ports for port in (80, 443, 8080, 8443)) and len(ports) <= 3:
        return "Web Device"
    if 22 in ports:
        return "Linux/Unix Host"
    if any(key in vendor_text for key in ("mikrotik", "ubiquiti", "tp-link", "cisco", "huawei", "asus")):
        return "Network Device"
    if "raspberry" in vendor_text:
        return "SBC/IoT Device"
    if ports:
        return "Server/Host"
    return "Unknown"


__all__ = ["detect_device_type", "extract_html_metadata", "mac_vendor", "normalize_mac"]
