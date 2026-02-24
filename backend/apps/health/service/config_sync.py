from __future__ import annotations

import ipaddress
from typing import Any
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, UUID, uuid5

from apps.health.model.contracts import MonitoredServiceSpec
from apps.health.service.validators import (
    clamp_interval_sec,
    clamp_latency_threshold_ms,
    clamp_timeout_ms,
    validate_target,
)


def extract_service_specs_from_config(
    *,
    config_payload: dict[str, Any],
    default_interval_sec: int,
    default_timeout_ms: int,
    default_latency_threshold_ms: int,
) -> list[MonitoredServiceSpec]:
    groups = config_payload.get("groups")
    if not isinstance(groups, list):
        return []

    specs: list[MonitoredServiceSpec] = []
    seen: set[UUID] = set()

    for group in groups:
        if not isinstance(group, dict):
            continue
        group_id = str(group.get("id") or "")
        subgroups = group.get("subgroups")
        if not isinstance(subgroups, list):
            continue
        for subgroup in subgroups:
            if not isinstance(subgroup, dict):
                continue
            subgroup_id = str(subgroup.get("id") or "")
            items = subgroup.get("items")
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                spec = _item_to_spec(
                    item=item,
                    group_id=group_id,
                    subgroup_id=subgroup_id,
                    default_interval_sec=default_interval_sec,
                    default_timeout_ms=default_timeout_ms,
                    default_latency_threshold_ms=default_latency_threshold_ms,
                )
                if spec is None:
                    continue
                if spec.id in seen:
                    continue
                seen.add(spec.id)
                specs.append(spec)
    return specs


def _item_to_spec(
    *,
    item: dict[str, Any],
    group_id: str,
    subgroup_id: str,
    default_interval_sec: int,
    default_timeout_ms: int,
    default_latency_threshold_ms: int,
) -> MonitoredServiceSpec | None:
    item_id = str(item.get("id") or "").strip()
    if not item_id:
        return None
    item_type = str(item.get("type") or "link").strip().lower()
    if item_type not in {"link", "iframe"}:
        return None

    health_cfg_raw = item.get("healthcheck")
    health_cfg = health_cfg_raw if isinstance(health_cfg_raw, dict) else {}

    enabled: bool
    if "monitor_health" in item:
        enabled = _as_bool(item.get("monitor_health"), default=False)
    elif health_cfg_raw is None:
        enabled = False
    else:
        enabled = _as_bool(health_cfg.get("enabled"), default=True)

    check_type = str(health_cfg.get("type") or "http").strip().lower()
    if check_type not in {"http", "tcp", "icmp"}:
        check_type = "http"

    target = _resolve_target(item=item, health_cfg=health_cfg, check_type=check_type)
    if not target:
        return None
    try:
        validated_target = validate_target(check_type=check_type, target=target)
    except Exception:
        return None

    interval_sec = clamp_interval_sec(default_interval_sec)
    timeout_ms = clamp_timeout_ms(int(health_cfg.get("timeout_ms") or default_timeout_ms))
    latency_threshold_ms = clamp_latency_threshold_ms(
        int(health_cfg.get("latency_threshold_ms") or default_latency_threshold_ms)
    )
    tls_verify = _resolve_tls_verify(
        health_cfg=health_cfg,
        check_type=check_type,
        target=validated_target,
    )

    raw_name = str(item.get("title") or item_id).strip()
    service_name = raw_name[:128] if raw_name else item_id
    stable_key = f"{group_id}:{subgroup_id}:{item_id}"

    return MonitoredServiceSpec(
        id=uuid5(NAMESPACE_URL, stable_key),
        item_id=item_id,
        name=service_name,
        check_type=check_type,  # type: ignore[arg-type]
        target=validated_target,
        interval_sec=interval_sec,
        timeout_ms=timeout_ms,
        latency_threshold_ms=latency_threshold_ms,
        tls_verify=tls_verify,
        enabled=enabled,
    )


def _as_bool(value: Any, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off"}:
            return False
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    return default


def _resolve_target(*, item: dict[str, Any], health_cfg: dict[str, Any], check_type: str) -> str:
    if check_type == "http":
        check_url = str(item.get("check_url") or "").strip()
        if check_url:
            return check_url
        health_url = str(health_cfg.get("url") or "").strip()
        if health_url:
            return health_url
        return str(item.get("url") or "").strip()

    if check_type in {"tcp", "icmp"}:
        explicit_target = str(health_cfg.get("target") or "").strip()
        if explicit_target:
            return explicit_target

    return str(item.get("url") or "").strip()


def _resolve_tls_verify(*, health_cfg: dict[str, Any], check_type: str, target: str) -> bool:
    if "tls_verify" in health_cfg:
        return _as_bool(health_cfg.get("tls_verify"), default=True)
    if "verify_tls" in health_cfg:
        return _as_bool(health_cfg.get("verify_tls"), default=True)
    if "insecure_skip_verify" in health_cfg:
        return not _as_bool(health_cfg.get("insecure_skip_verify"), default=False)
    if check_type == "http" and _is_private_network_url(target):
        return False
    return True


def _is_private_network_url(url: str) -> bool:
    try:
        hostname = (urlsplit(url).hostname or "").strip().lower()
    except Exception:
        return False
    if not hostname:
        return False
    if hostname == "localhost":
        return True
    try:
        host_ip = ipaddress.ip_address(hostname)
    except ValueError:
        return False
    return bool(host_ip.is_private or host_ip.is_loopback or host_ip.is_link_local)


__all__ = ["extract_service_specs_from_config"]
