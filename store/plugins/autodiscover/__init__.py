from __future__ import annotations

import asyncio
import logging
import os
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

from core.contracts.models import ActionEnvelope

if TYPE_CHECKING:
    from core.config import ConfigService
    from core.events.protocols import EventPublisher
    from core.gateway import ActionGateway
    from core.storage import StorageRPC
else:
    ConfigService = Any
    EventPublisher = Any
    ActionGateway = Any
    StorageRPC = Any

from .constants import (
    DEFAULT_CONNECT_TIMEOUT_SEC,
    DEFAULT_PORTS_RANGE,
    DEFAULT_PORT_SCAN_MAX,
    DEFAULT_RESULT_FILE,
    SAFE_DEFAULT_SCAN_PORTS,
)
from .manifest import ACTION_SCAN, CAPABILITY_SCAN, PLUGIN_NAME
from .registry import register_autodiscover_actions
from .services import extract_services_from_scan_payload
from .storage import load_last_result

logger = logging.getLogger("core.plugins.autodiscover")

_action_gateway: ActionGateway | None = None
_event_bus: EventPublisher | None = None
_config_service: ConfigService | None = None
_storage_rpc: StorageRPC | None = None
_background_task: asyncio.Task[Any] | None = None
_last_sync_marker: str | None = None
_runtime_role: str | None = None
_last_services_cache: dict[str, Any] | None = None

_SCAN_SETTINGS_KEY = "scan_settings_v1"
_SCAN_BOOTSTRAP_STATE_KEY = "scan_bootstrap_state_v1"
_SCHEDULER_ACTOR_PREFIX = f"plugin.{PLUGIN_NAME}.scheduler"
_SCAN_PROFILES = ("fast", "balanced", "full")
_SCAN_PHASE_STARTUP_FAST = "startup_fast"
_SCAN_PHASE_STARTUP_FULL = "startup_full"
_SCAN_PHASE_SCHEDULED_PROFILE = "scheduled_profile"
_ADAPTIVE_TIMEOUT_MODES = ("off", "balanced", "aggressive")
_HOSTNAME_ENRICHMENT_MODES = ("off", "standard", "aggressive")

_BACKGROUND_INTERVAL_SEC = max(60, int(os.getenv("OKO_AUTODISCOVER_BACKGROUND_SCAN_INTERVAL_SEC", "900")))
_BACKGROUND_INITIAL_DELAY_SEC = max(1, int(os.getenv("OKO_AUTODISCOVER_BACKGROUND_SCAN_INITIAL_DELAY_SEC", "15")))
_BACKGROUND_MAX_HOSTS = max(16, int(os.getenv("OKO_AUTODISCOVER_BACKGROUND_SCAN_MAX_HOSTS", "255")))
_BACKGROUND_PORTS_FROM = max(1, int(os.getenv("OKO_AUTODISCOVER_BACKGROUND_SCAN_PORTS_FROM", "1")))
_BACKGROUND_PORTS_TO = max(
    _BACKGROUND_PORTS_FROM,
    min(65535, int(os.getenv("OKO_AUTODISCOVER_BACKGROUND_SCAN_PORTS_TO", "20000"))),
)
_BACKGROUND_RUNNING_ACTION_MAX_AGE_SEC = max(
    60,
    int(os.getenv("OKO_AUTODISCOVER_BACKGROUND_RUNNING_ACTION_MAX_AGE_SEC", "600")),
)
_BACKGROUND_ROLE = (os.getenv("OKO_AUTODISCOVER_BACKGROUND_SCAN_ROLE", "worker") or "worker").strip().lower()
_BACKGROUND_BOOTSTRAP_POLL_SEC = max(
    10,
    int(os.getenv("OKO_AUTODISCOVER_BACKGROUND_BOOTSTRAP_POLL_SEC", "30")),
)


def _resolve_result_file() -> Path:
    plugin_dir = Path(__file__).resolve().parent
    candidates = (
        Path.cwd() / DEFAULT_RESULT_FILE,
        plugin_dir / DEFAULT_RESULT_FILE,
        plugin_dir.parent / DEFAULT_RESULT_FILE,
        plugin_dir.parent.parent / DEFAULT_RESULT_FILE,
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _summary_from_payload(result_payload: dict[str, Any], services: list[dict[str, Any]]) -> dict[str, Any]:
    hosts = result_payload.get("hosts")
    host_count = len(hosts) if isinstance(hosts, list) else 0
    return {
        "discovered_hosts": host_count,
        "discovered_services": len(services),
        "generated_at": result_payload.get("generated_at"),
        "duration_ms": result_payload.get("duration_ms"),
    }


def _as_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    token = str(value).strip()
    return token or None


def _as_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed


def _parse_datetime(value: Any) -> datetime | None:
    parsed: datetime | None = None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        token = value.strip()
        if token:
            with suppress(Exception):
                parsed = datetime.fromisoformat(token.replace("Z", "+00:00"))
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _safe_bool(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    token = str(value).strip().lower()
    if token in {"1", "true", "yes", "on"}:
        return True
    if token in {"0", "false", "no", "off"}:
        return False
    return default


def _normalize_scan_profile(value: Any, *, default: str = "balanced") -> str:
    token = _as_optional_string(value)
    if not token:
        return default
    lowered = token.lower()
    if lowered in _SCAN_PROFILES:
        return lowered
    return default


def _normalize_one_of(value: Any, *, choices: tuple[str, ...], default: str) -> str:
    token = _as_optional_string(value)
    if not token:
        return default
    lowered = token.lower()
    if lowered in choices:
        return lowered
    return default


def _default_scan_settings() -> dict[str, Any]:
    return {
        "scan_profile": "balanced",
        "verify_previous_hosts": True,
        "adaptive_timeout_mode": "balanced",
        "hostname_enrichment_mode": "aggressive",
        "banner_grabbing_enabled": True,
        "diff_mode_enabled": True,
        "confidence_scoring_enabled": True,
    }


def _normalize_scan_settings(value: Any) -> dict[str, Any]:
    default = _default_scan_settings()
    settings = value if isinstance(value, dict) else {}
    return {
        "scan_profile": _normalize_scan_profile(settings.get("scan_profile"), default=default["scan_profile"]),
        "verify_previous_hosts": _safe_bool(
            settings.get("verify_previous_hosts"),
            default=default["verify_previous_hosts"],
        ),
        "adaptive_timeout_mode": _normalize_one_of(
            settings.get("adaptive_timeout_mode"),
            choices=_ADAPTIVE_TIMEOUT_MODES,
            default=default["adaptive_timeout_mode"],
        ),
        "hostname_enrichment_mode": _normalize_one_of(
            settings.get("hostname_enrichment_mode"),
            choices=_HOSTNAME_ENRICHMENT_MODES,
            default=default["hostname_enrichment_mode"],
        ),
        "banner_grabbing_enabled": _safe_bool(
            settings.get("banner_grabbing_enabled"),
            default=default["banner_grabbing_enabled"],
        ),
        "diff_mode_enabled": _safe_bool(
            settings.get("diff_mode_enabled"),
            default=default["diff_mode_enabled"],
        ),
        "confidence_scoring_enabled": _safe_bool(
            settings.get("confidence_scoring_enabled"),
            default=default["confidence_scoring_enabled"],
        ),
    }


def _default_bootstrap_state() -> dict[str, Any]:
    return {
        "startup_fast_completed": False,
        "startup_full_completed": False,
        "first_startup_sequence_completed": False,
        "updated_at": datetime.now(UTC).isoformat(),
    }


def _normalize_bootstrap_state(value: Any) -> dict[str, Any]:
    state = value if isinstance(value, dict) else {}
    default = _default_bootstrap_state()
    startup_fast_completed = _safe_bool(
        state.get("startup_fast_completed"),
        default=default["startup_fast_completed"],
    )
    startup_full_completed = _safe_bool(
        state.get("startup_full_completed"),
        default=default["startup_full_completed"],
    )
    first_sequence_completed = _safe_bool(
        state.get("first_startup_sequence_completed"),
        default=default["first_startup_sequence_completed"],
    )
    if startup_fast_completed and startup_full_completed:
        first_sequence_completed = True
    return {
        "startup_fast_completed": startup_fast_completed,
        "startup_full_completed": startup_full_completed,
        "first_startup_sequence_completed": first_sequence_completed,
        "updated_at": _as_optional_string(state.get("updated_at")) or default["updated_at"],
    }


def _normalized_services_from_projection(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    services: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        services.append(
            {
                "host_ip": row.get("host_ip"),
                "hostname": row.get("hostname"),
                "host_mac": row.get("host_mac") or row.get("mac_address"),
                "mac_vendor": row.get("mac_vendor") or row.get("vendor"),
                "device_type": row.get("device_type"),
                "port": row.get("port"),
                "service": row.get("service"),
                "title": row.get("title"),
                "description": None,
                "url": row.get("url"),
                "scheme": row.get("scheme"),
                "status": row.get("status"),
                "server": row.get("server"),
            }
        )
    services.sort(
        key=lambda item: (
            str(item.get("host_ip") or ""),
            int(item.get("port") or 0),
        )
    )
    return services


def _generated_at_from_scan_run(row: dict[str, Any] | None) -> str | None:
    if not isinstance(row, dict):
        return None
    summary = row.get("summary")
    if isinstance(summary, dict):
        summary_generated_at = _as_optional_string(summary.get("generated_at"))
        if summary_generated_at:
            return summary_generated_at
    requested_at = _as_optional_string(row.get("requested_at"))
    if requested_at:
        return requested_at
    return _as_optional_string(row.get("updated_at"))


async def _resolve_latest_scan_id_from_runs() -> str | None:
    if _storage_rpc is None:
        return None

    candidates: list[tuple[datetime, str]] = []
    for status in ("completed", "synced"):
        rows: list[dict[str, Any]] = []
        with suppress(Exception):
            rows = await _storage_rpc.table_query(
                plugin_id=PLUGIN_NAME,
                table="scan_runs",
                where={"status": status},
                limit=250,
            )
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            scan_id = _as_optional_string(row.get("scan_id"))
            if not scan_id:
                continue
            generated_at = _generated_at_from_scan_run(row)
            parsed_generated_at = _parse_datetime(generated_at)
            if parsed_generated_at is None:
                continue
            candidates.append((parsed_generated_at, scan_id))

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


async def _resolve_generated_at_for_scan(scan_id: str | None) -> str | None:
    if _storage_rpc is None or not scan_id:
        return None
    with suppress(Exception):
        scan_run = await _storage_rpc.table_get(
            plugin_id=PLUGIN_NAME,
            table="scan_runs",
            pk=scan_id,
        )
        return _generated_at_from_scan_run(scan_run if isinstance(scan_run, dict) else None)
    return None


async def _load_scan_settings() -> dict[str, Any]:
    if _storage_rpc is None:
        return _default_scan_settings()
    with suppress(Exception):
        raw = await _storage_rpc.kv_get(plugin_id=PLUGIN_NAME, key=_SCAN_SETTINGS_KEY)
        return _normalize_scan_settings(raw)
    return _default_scan_settings()


async def _save_scan_settings(settings: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_scan_settings(settings)
    if _storage_rpc is not None:
        with suppress(Exception):
            await _storage_rpc.kv_set(
                plugin_id=PLUGIN_NAME,
                key=_SCAN_SETTINGS_KEY,
                value=normalized,
            )
    return normalized


async def _load_bootstrap_state() -> dict[str, Any]:
    if _storage_rpc is None:
        return _default_bootstrap_state()
    with suppress(Exception):
        raw = await _storage_rpc.kv_get(plugin_id=PLUGIN_NAME, key=_SCAN_BOOTSTRAP_STATE_KEY)
        return _normalize_bootstrap_state(raw)
    return _default_bootstrap_state()


async def _save_bootstrap_state(state: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_bootstrap_state(
        {
            **state,
            "updated_at": datetime.now(UTC).isoformat(),
        }
    )
    if _storage_rpc is not None:
        with suppress(Exception):
            await _storage_rpc.kv_set(
                plugin_id=PLUGIN_NAME,
                key=_SCAN_BOOTSTRAP_STATE_KEY,
                value=normalized,
            )
    return normalized


def _scan_profile_payload(profile: str) -> dict[str, Any]:
    selected = _normalize_scan_profile(profile)
    if selected == "fast":
        ports = list(SAFE_DEFAULT_SCAN_PORTS)
        return {
            "scan_profile": "fast",
            "ports": ports,
            "ports_from": ports[0],
            "ports_to": ports[-1],
        }
    if selected == "full":
        return {
            "scan_profile": "full",
            "ports_from": 1,
            "ports_to": DEFAULT_PORT_SCAN_MAX,
        }
    balanced_to = max(DEFAULT_PORTS_RANGE[1], _BACKGROUND_PORTS_TO)
    return {
        "scan_profile": "balanced",
        "ports_from": _BACKGROUND_PORTS_FROM,
        "ports_to": balanced_to,
    }


def _phase_from_actor(actor: str) -> str:
    token = _as_optional_string(actor) or ""
    if not token.startswith(_SCHEDULER_ACTOR_PREFIX):
        return ""
    suffix = token[len(_SCHEDULER_ACTOR_PREFIX) :].strip(".")
    if suffix in {
        _SCAN_PHASE_STARTUP_FAST,
        _SCAN_PHASE_STARTUP_FULL,
        _SCAN_PHASE_SCHEDULED_PROFILE,
    }:
        return suffix
    return ""


def _is_pending_scheduler_status(status: str) -> bool:
    return status in {"queued", "validated", "running"}


async def _refresh_bootstrap_state_from_history(state: dict[str, Any]) -> dict[str, Any]:
    if _action_gateway is None:
        return state

    completed_phases: set[str] = set()

    with suppress(Exception):
        history = await _action_gateway.history(limit=100)
        if isinstance(history, list):
            for entry in history:
                if not isinstance(entry, dict):
                    continue
                if str(entry.get("type") or "") != ACTION_SCAN:
                    continue
                actor = str(entry.get("requested_by") or "")
                phase = _phase_from_actor(actor)
                if not phase:
                    continue
                status = str(entry.get("status") or "").lower()
                if status != "completed":
                    continue
                completed_phases.add(phase)

    if not completed_phases:
        return state

    changed = False
    if _SCAN_PHASE_STARTUP_FAST in completed_phases and not bool(state.get("startup_fast_completed")):
        state["startup_fast_completed"] = True
        changed = True
    if _SCAN_PHASE_STARTUP_FULL in completed_phases and not bool(state.get("startup_full_completed")):
        state["startup_full_completed"] = True
        changed = True

    if bool(state.get("startup_fast_completed")) and bool(state.get("startup_full_completed")):
        if not bool(state.get("first_startup_sequence_completed")):
            state["first_startup_sequence_completed"] = True
            changed = True

    if changed:
        return await _save_bootstrap_state(state)
    return state


def _next_scan_phase(state: dict[str, Any]) -> str:
    if not bool(state.get("first_startup_sequence_completed")):
        if not bool(state.get("startup_fast_completed")):
            return _SCAN_PHASE_STARTUP_FAST
        if not bool(state.get("startup_full_completed")):
            return _SCAN_PHASE_STARTUP_FULL
    return _SCAN_PHASE_SCHEDULED_PROFILE


def _is_bootstrap_pending(state: dict[str, Any]) -> bool:
    return not bool(state.get("first_startup_sequence_completed"))


async def _resolve_previous_hosts_and_ports_for_rescan(*, max_hosts: int) -> tuple[list[str], list[int]]:
    if _storage_rpc is None:
        return [], []
    latest_scan_id = await _resolve_latest_scan_id_from_runs()
    if not latest_scan_id:
        return [], []
    rows: list[dict[str, Any]] = []
    with suppress(Exception):
        rows = await _storage_rpc.table_query(
            plugin_id=PLUGIN_NAME,
            table="scan_services",
            where={"scan_id": latest_scan_id},
            limit=max(400, min(10000, max_hosts * 64)),
        )
    if not isinstance(rows, list):
        return [], []

    host_ips: set[str] = set()
    ports: set[int] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        host_ip = _as_optional_string(row.get("host_ip"))
        if host_ip:
            host_ips.add(host_ip)
        port = _as_optional_int(row.get("port"))
        if port is None:
            continue
        if 1 <= port <= DEFAULT_PORT_SCAN_MAX:
            ports.add(port)

    hosts_sorted = sorted(host_ips)[:max_hosts]
    ports_sorted = sorted(ports)
    return hosts_sorted, ports_sorted


async def _persist_services_projection(*, scan_id: str, services: list[dict[str, Any]]) -> None:
    if _storage_rpc is None:
        return
    now_iso = datetime.now(UTC).isoformat()
    dedupe: set[str] = set()
    projection_write_failed = False
    for row in services:
        if not isinstance(row, dict):
            continue
        port = _as_optional_int(row.get("port"))
        if port is None:
            continue
        host_ip = _as_optional_string(row.get("host_ip"))
        service = _as_optional_string(row.get("service"))
        url = _as_optional_string(row.get("url"))
        dedupe_token = f"{host_ip or ''}:{port}:{service or ''}:{url or ''}"
        if dedupe_token in dedupe:
            continue
        dedupe.add(dedupe_token)
        if projection_write_failed:
            continue
        try:
            await _storage_rpc.table_upsert(
                plugin_id=PLUGIN_NAME,
                table="scan_services",
                row={
                    "service_key": f"{scan_id}:{dedupe_token}",
                    "scan_id": scan_id,
                    "host_ip": host_ip,
                    "hostname": _as_optional_string(row.get("hostname")),
                    "host_mac": _as_optional_string(row.get("host_mac") or row.get("mac_address")),
                    "mac_vendor": _as_optional_string(row.get("mac_vendor") or row.get("vendor")),
                    "device_type": _as_optional_string(row.get("device_type")),
                    "port": port,
                    "service": service,
                    "title": _as_optional_string(row.get("title")),
                    "url": url,
                    "scheme": _as_optional_string(row.get("scheme")),
                    "status": _as_optional_string(row.get("status")),
                    "server": _as_optional_string(row.get("server")),
                    "updated_at": now_iso,
                },
            )
        except Exception as exc:
            projection_write_failed = True
            logger.warning(
                "Autodiscover could not write scan_services projection scan_id=%s: %s",
                scan_id,
                exc,
            )


async def _sync_result_to_storage() -> None:
    global _last_sync_marker

    if _storage_rpc is None:
        return

    payload = load_last_result(_resolve_result_file())
    if not isinstance(payload, dict):
        return

    generated_at_value = payload.get("generated_at")
    if isinstance(generated_at_value, str) and generated_at_value.strip():
        marker = generated_at_value.strip()
    else:
        marker = f"sync:{datetime.now(UTC).isoformat()}"

    if marker == _last_sync_marker:
        return

    scan_id = f"sync:{marker}"
    services = extract_services_from_scan_payload(payload)
    summary = _summary_from_payload(payload, services)
    now_iso = datetime.now(UTC).isoformat()
    requested_at = marker if marker.startswith("20") else now_iso

    await _persist_services_projection(scan_id=scan_id, services=services)
    await _storage_rpc.table_upsert(
        plugin_id=PLUGIN_NAME,
        table="scan_runs",
        row={
            "scan_id": scan_id,
            "status": "synced",
            "dry_run": False,
            "requested_at": requested_at,
            "updated_at": now_iso,
            "summary": summary,
        },
    )
    with suppress(Exception):
        await _storage_rpc.kv_set(plugin_id=PLUGIN_NAME, key="last_scan_summary", value=summary)
    with suppress(Exception):
        await _storage_rpc.kv_set(plugin_id=PLUGIN_NAME, key="last_scan_id", value=scan_id)
    with suppress(Exception):
        await _storage_rpc.kv_set(
            plugin_id=PLUGIN_NAME,
            key="services_latest",
            value={
                "services": services,
                "total": len(services),
                "generated_at": marker,
            },
        )
    with suppress(Exception):
        await _storage_rpc.kv_set(plugin_id=PLUGIN_NAME, key="last_scan_result", value=payload)
    _last_sync_marker = marker
    logger.info(
        "Autodiscover sync stored scan_id=%s services=%s generated_at=%s",
        scan_id,
        len(services),
        marker,
    )


async def _cleanup_legacy_kv_storage() -> None:
    # Keep legacy read-model keys for backward compatibility.
    return


async def _run_scheduled_scan_once() -> bool:
    if _action_gateway is None:
        logger.info("Autodiscover background scan skipped: action gateway is not available")
        return False

    settings = await _load_scan_settings()
    state = await _load_bootstrap_state()
    state = await _refresh_bootstrap_state_from_history(state)
    phase = _next_scan_phase(state)

    now_utc = datetime.now(UTC)
    with suppress(Exception):
        history = await _action_gateway.history(limit=50)
        if isinstance(history, list):
            for entry in history:
                if not isinstance(entry, dict):
                    continue
                if str(entry.get("type") or "") != ACTION_SCAN:
                    continue
                status = str(entry.get("status") or "").lower()
                requested_by = str(entry.get("requested_by") or "")
                if requested_by.startswith(_SCHEDULER_ACTOR_PREFIX) and _is_pending_scheduler_status(status):
                    age_sec = 0
                    requested_at_raw = entry.get("requested_at")
                    requested_at_dt: datetime | None = None
                    if isinstance(requested_at_raw, datetime):
                        requested_at_dt = requested_at_raw
                    elif isinstance(requested_at_raw, str):
                        with suppress(Exception):
                            requested_at_dt = datetime.fromisoformat(
                                requested_at_raw.replace("Z", "+00:00"),
                            )
                    if requested_at_dt is not None:
                        if requested_at_dt.tzinfo is None:
                            requested_at_dt = requested_at_dt.replace(tzinfo=UTC)
                        age_sec = max(0, int((now_utc - requested_at_dt).total_seconds()))
                    if age_sec > _BACKGROUND_RUNNING_ACTION_MAX_AGE_SEC:
                        logger.warning(
                            "Autodiscover found stale scheduler action id=%s status=%s age_sec=%s, starting new scan",
                            entry.get("id"),
                            status,
                            age_sec,
                        )
                        continue
                    logger.info(
                        "Autodiscover background scan skipped: scheduler action id=%s status=%s age_sec=%s",
                        entry.get("id"),
                        status,
                        age_sec,
                    )
                    return False

    if phase == _SCAN_PHASE_STARTUP_FAST:
        profile = "fast"
    elif phase == _SCAN_PHASE_STARTUP_FULL:
        profile = "full"
    else:
        profile = _normalize_scan_profile(settings.get("scan_profile"), default="balanced")

    actor = f"{_SCHEDULER_ACTOR_PREFIX}.{phase}"
    adaptive_timeout_mode = _normalize_one_of(
        settings.get("adaptive_timeout_mode"),
        choices=_ADAPTIVE_TIMEOUT_MODES,
        default="balanced",
    )
    hostname_enrichment_mode = _normalize_one_of(
        settings.get("hostname_enrichment_mode"),
        choices=_HOSTNAME_ENRICHMENT_MODES,
        default="aggressive",
    )
    banner_grabbing_enabled = bool(settings.get("banner_grabbing_enabled", True))
    if adaptive_timeout_mode == "off":
        connect_timeout_sec = max(0.2, min(10.0, DEFAULT_CONNECT_TIMEOUT_SEC * 0.8))
    elif adaptive_timeout_mode == "aggressive":
        connect_timeout_sec = max(0.2, min(10.0, DEFAULT_CONNECT_TIMEOUT_SEC * 1.8))
    else:
        connect_timeout_sec = DEFAULT_CONNECT_TIMEOUT_SEC
    payload: dict[str, Any] = {
        "max_hosts": _BACKGROUND_MAX_HOSTS,
        "include_http_services": banner_grabbing_enabled,
        "include_dashboard_items": True,
        "connect_timeout_sec": connect_timeout_sec,
        "resolve_hostnames": hostname_enrichment_mode != "off",
        "scheduler_phase": phase,
        "scheduler_profile": profile,
        "adaptive_timeout_mode": adaptive_timeout_mode,
        "hostname_enrichment_mode": hostname_enrichment_mode,
        "banner_grabbing_enabled": banner_grabbing_enabled,
        "diff_mode_enabled": bool(settings.get("diff_mode_enabled", True)),
        "confidence_scoring_enabled": bool(settings.get("confidence_scoring_enabled", True)),
        **_scan_profile_payload(profile),
    }
    if bool(settings.get("verify_previous_hosts", True)):
        previous_hosts, previous_ports = await _resolve_previous_hosts_and_ports_for_rescan(
            max_hosts=_BACKGROUND_MAX_HOSTS,
        )
        if previous_hosts:
            payload["hosts"] = previous_hosts
        if profile != "full" and previous_ports:
            base_ports: set[int] = set()
            raw_ports = payload.get("ports")
            if isinstance(raw_ports, list):
                for entry in raw_ports:
                    parsed = _as_optional_int(entry)
                    if parsed is None:
                        continue
                    if 1 <= parsed <= DEFAULT_PORT_SCAN_MAX:
                        base_ports.add(parsed)
            else:
                start_port = _as_optional_int(payload.get("ports_from")) or 1
                end_port = _as_optional_int(payload.get("ports_to")) or max(start_port, DEFAULT_PORTS_RANGE[1])
                if start_port > end_port:
                    start_port, end_port = end_port, start_port
                start_port = max(1, start_port)
                end_port = min(DEFAULT_PORT_SCAN_MAX, end_port)
                base_ports.update(range(start_port, end_port + 1))
            merged_ports = sorted(base_ports | set(previous_ports))
            if merged_ports:
                payload["ports"] = merged_ports
                payload["ports_from"] = merged_ports[0]
                payload["ports_to"] = merged_ports[-1]

    action = ActionEnvelope(
        type=ACTION_SCAN,
        requested_by=actor,
        capability=CAPABILITY_SCAN,
        payload=payload,
        dry_run=False,
    )
    logger.info(
        "Autodiscover background scan enqueue actor=%s phase=%s profile=%s max_hosts=%s ports=%s-%s hosts_override=%s",
        actor,
        phase,
        profile,
        _BACKGROUND_MAX_HOSTS,
        payload.get("ports_from"),
        payload.get("ports_to"),
        len(payload.get("hosts", [])) if isinstance(payload.get("hosts"), list) else 0,
    )
    await _action_gateway.execute_action(action=action, actor=actor)
    logger.info(
        "Autodiscover background scan action dispatched action_id=%s action_type=%s actor=%s",
        action.id,
        ACTION_SCAN,
        actor,
    )
    return True


async def _background_worker() -> None:
    first_run_at = datetime.now(UTC) + timedelta(seconds=_BACKGROUND_INITIAL_DELAY_SEC)
    logger.info(
        "Autodiscover background worker started interval_sec=%s bootstrap_poll_sec=%s initial_delay_sec=%s max_hosts=%s first_run_at=%s",
        _BACKGROUND_INTERVAL_SEC,
        _BACKGROUND_BOOTSTRAP_POLL_SEC,
        _BACKGROUND_INITIAL_DELAY_SEC,
        _BACKGROUND_MAX_HOSTS,
        first_run_at.isoformat(),
    )
    await asyncio.sleep(_BACKGROUND_INITIAL_DELAY_SEC)
    cycle = 0
    while True:
        cycle += 1
        cycle_started_at = datetime.now(UTC)
        try:
            logger.info(
                "Autodiscover background cycle started cycle=%s started_at=%s",
                cycle,
                cycle_started_at.isoformat(),
            )
            await _sync_result_to_storage()
            dispatched = await _run_scheduled_scan_once()
            state = await _load_bootstrap_state()
            sleep_sec = _BACKGROUND_BOOTSTRAP_POLL_SEC if _is_bootstrap_pending(state) else _BACKGROUND_INTERVAL_SEC
            next_run_at = datetime.now(UTC) + timedelta(seconds=sleep_sec)
            logger.info(
                "Autodiscover background cycle completed cycle=%s scan_dispatched=%s next_run_at=%s due_in_sec=%s",
                cycle,
                dispatched,
                next_run_at.isoformat(),
                sleep_sec,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Autodiscover background worker cycle failed")
            sleep_sec = _BACKGROUND_BOOTSTRAP_POLL_SEC
        await asyncio.sleep(sleep_sec)


def setup(
    action_gateway: ActionGateway | None = None,
    event_bus: EventPublisher | None = None,
    config_service: ConfigService | None = None,
    storage_rpc: StorageRPC | None = None,
    runtime_role: str | None = None,
) -> None:
    global _action_gateway, _event_bus, _config_service, _storage_rpc, _runtime_role

    _action_gateway = action_gateway
    _event_bus = event_bus
    _config_service = config_service
    _storage_rpc = storage_rpc
    _runtime_role = runtime_role

    if _action_gateway is not None and _event_bus is not None:
        register_autodiscover_actions(
            _action_gateway,
            event_bus=_event_bus,
            config_service=_config_service,
            storage_rpc=_storage_rpc,
        )


def teardown() -> None:
    global _action_gateway, _event_bus, _config_service, _storage_rpc, _background_task, _last_services_cache

    if _background_task is not None and not _background_task.done():
        _background_task.cancel()

    _background_task = None
    _action_gateway = None
    _event_bus = None
    _config_service = None
    _storage_rpc = None
    _last_services_cache = None


async def on_startup() -> None:
    global _background_task

    await _cleanup_legacy_kv_storage()
    await _save_scan_settings(await _load_scan_settings())
    await _save_bootstrap_state(await _load_bootstrap_state())

    role = (_runtime_role or "unknown").strip().lower()
    if _BACKGROUND_ROLE != "any" and role != _BACKGROUND_ROLE:
        logger.info(
            "Autodiscover background worker skipped runtime_role=%s expected_role=%s",
            role,
            _BACKGROUND_ROLE,
        )
        return

    await _sync_result_to_storage()

    if _background_task is not None and not _background_task.done():
        return
    _background_task = asyncio.create_task(
        _background_worker(),
        name="autodiscover-background-worker",
    )
    logger.info("Autodiscover background worker task created runtime_role=%s", role)


async def on_shutdown() -> None:
    global _background_task

    if _background_task is None:
        return
    _background_task.cancel()
    with suppress(asyncio.CancelledError, TimeoutError):
        await asyncio.wait_for(_background_task, timeout=2.0)
    _background_task = None


async def get_services() -> dict[str, Any]:
    global _last_services_cache

    if _storage_rpc is None:
        if isinstance(_last_services_cache, dict):
            return dict(_last_services_cache)
        return {
            "services": [],
            "total": 0,
            "generated_at": datetime.now(UTC).isoformat(),
        }

    services: list[dict[str, Any]] = []
    generated_at: str | None = None
    storage_read_failed = False
    selected_scan_id: str | None = None
    fallback_response = {
        "services": [],
        "total": 0,
        "generated_at": datetime.now(UTC).isoformat(),
    }

    async def _safe_table_query(
        *,
        table: str,
        where: dict[str, Any],
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        nonlocal storage_read_failed
        try:
            rows = await _storage_rpc.table_query(
                plugin_id=PLUGIN_NAME,
                table=table,
                where=where,
                limit=limit,
            )
            if not isinstance(rows, list):
                return []
            return [row for row in rows if isinstance(row, dict)]
        except Exception as exc:
            storage_read_failed = True
            logger.warning("Autodiscover storage read timeout/failure op=table.query table=%s: %s", table, exc)
            return []

    async def _safe_table_get_scan_run(scan_id: str) -> dict[str, Any] | None:
        nonlocal storage_read_failed
        try:
            row = await _storage_rpc.table_get(
                plugin_id=PLUGIN_NAME,
                table="scan_runs",
                pk=scan_id,
            )
        except Exception as exc:
            storage_read_failed = True
            logger.warning("Autodiscover storage read timeout/failure op=table.get table=scan_runs: %s", exc)
            return None
        if isinstance(row, dict):
            return row
        return None

    async def _safe_kv_get_scan_id() -> str | None:
        nonlocal storage_read_failed
        try:
            raw = await _storage_rpc.kv_get(plugin_id=PLUGIN_NAME, key="last_scan_id")
        except Exception as exc:
            storage_read_failed = True
            logger.warning("Autodiscover storage read timeout/failure op=kv.get key=last_scan_id: %s", exc)
            return None
        return _as_optional_string(raw)

    async def _safe_kv_get(key: str) -> Any | None:
        nonlocal storage_read_failed
        try:
            return await _storage_rpc.kv_get(plugin_id=PLUGIN_NAME, key=key)
        except Exception as exc:
            storage_read_failed = True
            logger.warning("Autodiscover storage read timeout/failure op=kv.get key=%s: %s", key, exc)
            return None

    def _services_from_legacy_cache(value: Any) -> tuple[list[dict[str, Any]], str | None]:
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)], None
        if not isinstance(value, dict):
            return [], None
        raw_services = value.get("services")
        if isinstance(raw_services, list):
            services_rows = [row for row in raw_services if isinstance(row, dict)]
        else:
            services_rows = []
        return services_rows, _as_optional_string(value.get("generated_at"))

    async def _safe_kv_self_heal(scan_id: str, scan_run: dict[str, Any] | None) -> None:
        with suppress(Exception):
            await _storage_rpc.kv_set(plugin_id=PLUGIN_NAME, key="last_scan_id", value=scan_id)
        summary = scan_run.get("summary") if isinstance(scan_run, dict) else None
        if isinstance(summary, dict):
            with suppress(Exception):
                await _storage_rpc.kv_set(
                    plugin_id=PLUGIN_NAME,
                    key="last_scan_summary",
                    value=summary,
                )

    def _scan_status_ok(scan_run: dict[str, Any] | None) -> bool:
        if not isinstance(scan_run, dict):
            return False
        status = _as_optional_string(scan_run.get("status")) or ""
        return status.lower() in {"completed", "synced"}

    async def _read_projection_for_scan(
        scan_id: str | None,
    ) -> tuple[list[dict[str, Any]], str | None, dict[str, Any] | None]:
        if not scan_id:
            return [], None, None
        scan_run = await _safe_table_get_scan_run(scan_id)
        if isinstance(scan_run, dict) and not _scan_status_ok(scan_run):
            return [], None, scan_run

        rows = await _safe_table_query(
            table="scan_services",
            where={"scan_id": scan_id},
        )
        projection_services = _normalized_services_from_projection(rows)
        projection_generated_at = _generated_at_from_scan_run(scan_run)
        if projection_generated_at is None:
            projection_generated_at = await _resolve_generated_at_for_scan(scan_id)

        if projection_services:
            return projection_services, projection_generated_at, scan_run
        if _scan_status_ok(scan_run):
            cached_services, cached_generated_at = _services_from_legacy_cache(
                await _safe_kv_get("services_latest"),
            )
            if cached_services:
                if (
                    projection_generated_at
                    and cached_generated_at
                    and projection_generated_at != cached_generated_at
                ):
                    logger.warning(
                        "Autodiscover services fallback rejected due to generated_at mismatch scan_id=%s projection=%s cache=%s",
                        scan_id,
                        projection_generated_at,
                        cached_generated_at,
                    )
                else:
                    return cached_services, cached_generated_at or projection_generated_at, scan_run

            cached_result = await _safe_kv_get("last_scan_result")
            if isinstance(cached_result, dict):
                result_services = extract_services_from_scan_payload(cached_result)
                result_generated_at = _as_optional_string(cached_result.get("generated_at"))
                if result_services:
                    if (
                        projection_generated_at
                        and result_generated_at
                        and projection_generated_at != result_generated_at
                    ):
                        logger.warning(
                            "Autodiscover result fallback rejected due to generated_at mismatch scan_id=%s projection=%s result=%s",
                            scan_id,
                            projection_generated_at,
                            result_generated_at,
                        )
                    else:
                        return result_services, result_generated_at or projection_generated_at, scan_run
            return [], projection_generated_at, scan_run
        return [], None, scan_run

    legacy_scan_id = await _safe_kv_get_scan_id()
    latest_scan_id = await _resolve_latest_scan_id_from_runs()

    scan_candidates: list[str] = []
    if legacy_scan_id:
        scan_candidates.append(legacy_scan_id)
    if latest_scan_id and latest_scan_id not in scan_candidates:
        scan_candidates.append(latest_scan_id)

    selected_scan_run: dict[str, Any] | None = None
    for scan_id in scan_candidates:
        candidate_services, candidate_generated_at, scan_run = await _read_projection_for_scan(scan_id)
        if candidate_services or candidate_generated_at:
            services = candidate_services
            generated_at = candidate_generated_at
            selected_scan_id = scan_id
            selected_scan_run = scan_run
            break

    if selected_scan_id and selected_scan_id != legacy_scan_id:
        await _safe_kv_self_heal(selected_scan_id, selected_scan_run)

    response = {
        "services": services,
        "total": len(services),
        "generated_at": generated_at or datetime.now(UTC).isoformat(),
    }
    if services or (selected_scan_id and generated_at):
        _last_services_cache = dict(response)
        return response
    if storage_read_failed and isinstance(_last_services_cache, dict):
        return dict(_last_services_cache)
    return fallback_response


async def get_settings() -> dict[str, Any]:
    settings = await _load_scan_settings()
    state = await _load_bootstrap_state()
    return {
        "settings": settings,
        "bootstrap_state": state,
        "profiles": {
            "available": list(_SCAN_PROFILES),
            "default": _default_scan_settings()["scan_profile"],
            "effective": _scan_profile_payload(settings.get("scan_profile")),
        },
        "modes": {
            "adaptive_timeout_mode": list(_ADAPTIVE_TIMEOUT_MODES),
            "hostname_enrichment_mode": list(_HOSTNAME_ENRICHMENT_MODES),
        },
    }


async def update_settings(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    current = await _load_scan_settings()
    raw = payload if isinstance(payload, dict) else {}
    merged = {
        **current,
        **raw,
    }
    settings = await _save_scan_settings(merged)
    return {
        "settings": settings,
        "profiles": {
            "available": list(_SCAN_PROFILES),
            "default": _default_scan_settings()["scan_profile"],
            "effective": _scan_profile_payload(settings.get("scan_profile")),
        },
        "modes": {
            "adaptive_timeout_mode": list(_ADAPTIVE_TIMEOUT_MODES),
            "hostname_enrichment_mode": list(_HOSTNAME_ENRICHMENT_MODES),
        },
    }


__all__ = [
    "get_settings",
    "get_services",
    "on_shutdown",
    "on_startup",
    "register_autodiscover_actions",
    "setup",
    "teardown",
    "update_settings",
]
