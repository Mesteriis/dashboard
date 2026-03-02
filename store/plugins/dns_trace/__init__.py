from __future__ import annotations

import asyncio
from contextlib import suppress
import ipaddress
import re
import shutil
from datetime import UTC, datetime
from statistics import mean
from time import perf_counter
from typing import Any

import httpx

from .manifest import (
    PLUGIN_CAPABILITIES,
    PLUGIN_DESCRIPTION,
    PLUGIN_LICENSE,
    PLUGIN_NAME,
    PLUGIN_TAGS,
    PLUGIN_VERSION,
)

PLUGIN_MANIFEST = {
    "name": PLUGIN_NAME,
    "version": PLUGIN_VERSION,
    "description": PLUGIN_DESCRIPTION,
    "license": PLUGIN_LICENSE,
    "tags": PLUGIN_TAGS,
    "capabilities": PLUGIN_CAPABILITIES,
}

_TARGETS: tuple[tuple[str, str], ...] = (
    ("google", "google.com"),
    ("yandex", "yandex.ru"),
    ("cloudflare", "cloudflare.com"),
)

_RESOLVERS: tuple[dict[str, str | None], ...] = (
    {
        "id": "system",
        "label": "Системный DNS",
        "ip": None,
    },
    {
        "id": "google",
        "label": "Google DNS",
        "ip": "8.8.8.8",
    },
    {
        "id": "cloudflare",
        "label": "Cloudflare DNS",
        "ip": "1.1.1.1",
    },
    {
        "id": "yandex",
        "label": "Yandex DNS",
        "ip": "77.88.8.8",
    },
)

_IP_RE = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"
)


def setup(**_kwargs: Any) -> None:
    return None


def teardown() -> None:
    return None


def _safe_round(value: float | None, digits: int = 1) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


def _flag(country_code: str | None) -> str:
    token = str(country_code or "").strip().upper()
    if len(token) != 2 or not token.isalpha():
        return "🏳️"
    base = 127397
    return "".join(chr(base + ord(ch)) for ch in token)


def _is_private_ip(ip: str) -> bool:
    try:
        value = ipaddress.ip_address(ip)
    except Exception:
        return False
    return bool(
        value.is_private
        or value.is_loopback
        or value.is_link_local
        or value.is_reserved
        or value.is_multicast
    )


async def _run_command(
    *args: str,
    timeout_sec: float,
) -> tuple[int, str, str, str | None]:
    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        return 127, "", "", f"command not found: {args[0]}"
    except Exception as exc:
        return 1, "", "", str(exc)

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_sec)
    except asyncio.TimeoutError:
        with suppress(Exception):
            proc.kill()
        with suppress(Exception):
            await proc.wait()
        return 124, "", "", f"timeout after {timeout_sec:.1f}s"

    return (
        int(proc.returncode or 0),
        stdout.decode("utf-8", errors="ignore"),
        stderr.decode("utf-8", errors="ignore"),
        None,
    )


async def _resolve_dns_with_dig(target: str, resolver_ip: str | None) -> dict[str, Any]:
    args = ["dig", "+time=2", "+tries=1", "+short"]
    if resolver_ip:
        args.append(f"@{resolver_ip}")
    args.append(target)

    started_at = perf_counter()
    code, stdout, stderr, run_error = await _run_command(*args, timeout_sec=4.0)
    latency_ms = _safe_round((perf_counter() - started_at) * 1000, 1)

    if run_error:
        return {
            "ok": False,
            "latency_ms": latency_ms,
            "ip": None,
            "error": run_error,
        }

    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    candidates = [line for line in lines if _IP_RE.search(line)]
    if code != 0 and not candidates:
        message = stderr.strip() or f"dig exited with code {code}"
        return {
            "ok": False,
            "latency_ms": latency_ms,
            "ip": None,
            "error": message,
        }

    resolved_ip = _IP_RE.search("\n".join(candidates or lines or [""]))
    ip = resolved_ip.group(0) if resolved_ip else None
    if not ip:
        return {
            "ok": False,
            "latency_ms": latency_ms,
            "ip": None,
            "error": "no A record",
        }

    return {
        "ok": True,
        "latency_ms": latency_ms,
        "ip": ip,
        "error": None,
    }


async def _resolve_dns_with_socket(target: str) -> dict[str, Any]:
    started_at = perf_counter()

    def _resolve() -> list[str]:
        import socket

        infos = socket.getaddrinfo(target, None, family=socket.AF_INET)
        out: list[str] = []
        for info in infos:
            value = str(info[4][0])
            if _IP_RE.search(value):
                out.append(value)
        return out

    try:
        values = await asyncio.to_thread(_resolve)
    except Exception as exc:
        return {
            "ok": False,
            "latency_ms": _safe_round((perf_counter() - started_at) * 1000, 1),
            "ip": None,
            "error": str(exc),
        }

    ip = values[0] if values else None
    return {
        "ok": bool(ip),
        "latency_ms": _safe_round((perf_counter() - started_at) * 1000, 1),
        "ip": ip,
        "error": None if ip else "no A record",
    }


async def _resolve_dns(target: str, resolver_ip: str | None, dig_available: bool) -> dict[str, Any]:
    if dig_available:
        return await _resolve_dns_with_dig(target, resolver_ip)
    if resolver_ip:
        return {
            "ok": False,
            "latency_ms": None,
            "ip": None,
            "error": "dig unavailable for custom resolver",
        }
    return await _resolve_dns_with_socket(target)


def _parse_traceroute_output(target_id: str, target: str, output: str) -> list[dict[str, Any]]:
    hops: list[dict[str, Any]] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("traceroute"):
            continue
        parts = line.split()
        if not parts:
            continue
        if not parts[0].isdigit():
            continue

        hop_no = int(parts[0])
        if len(parts) == 1:
            hops.append(
                {
                    "target_id": target_id,
                    "target": target,
                    "hop": hop_no,
                    "ip": None,
                    "rtt_ms": None,
                    "timeout": True,
                }
            )
            continue

        ip = None if parts[1] == "*" else parts[1]
        rtt_ms: float | None = None
        for token in parts[2:]:
            try:
                rtt_ms = float(token)
                break
            except ValueError:
                continue

        hops.append(
            {
                "target_id": target_id,
                "target": target,
                "hop": hop_no,
                "ip": ip,
                "rtt_ms": _safe_round(rtt_ms, 1),
                "timeout": ip is None,
            }
        )
    return hops


async def _trace_target(target_id: str, target: str, *, traceroute_available: bool) -> dict[str, Any]:
    if not traceroute_available:
        return {
            "target_id": target_id,
            "target": target,
            "ok": False,
            "hops": [],
            "error": "traceroute command unavailable",
        }

    args = ["traceroute", "-n", "-m", "10", "-q", "1", "-w", "1", target]
    code, stdout, stderr, run_error = await _run_command(*args, timeout_sec=14.0)
    if run_error:
        return {
            "target_id": target_id,
            "target": target,
            "ok": False,
            "hops": [],
            "error": run_error,
        }

    hops = _parse_traceroute_output(target_id, target, stdout)
    if code != 0 and not hops:
        return {
            "target_id": target_id,
            "target": target,
            "ok": False,
            "hops": [],
            "error": stderr.strip() or f"traceroute exited with code {code}",
        }

    return {
        "target_id": target_id,
        "target": target,
        "ok": bool(hops),
        "hops": hops,
        "error": None,
    }


async def _geo_lookup(client: httpx.AsyncClient, ip: str) -> dict[str, Any]:
    if _is_private_ip(ip):
        return {
            "ip": ip,
            "country": "LAN",
            "country_code": "LAN",
            "flag": "🏠",
            "city": "Local network",
            "asn": None,
        }

    try:
        response = await client.get(
            f"https://ipwho.is/{ip}",
            headers={"accept": "application/json", "user-agent": "oko-dns-trace-plugin/1.0"},
        )
        response.raise_for_status()
        payload = response.json() if response.headers.get("content-type", "").lower().find("json") >= 0 else {}
        success = bool(payload.get("success", False)) if isinstance(payload, dict) else False
        if not success:
            return {
                "ip": ip,
                "country": "Unknown",
                "country_code": "UN",
                "flag": "🏳️",
                "city": None,
                "asn": None,
            }
        country_code = str(payload.get("country_code") or "UN").upper()
        return {
            "ip": ip,
            "country": str(payload.get("country") or "Unknown"),
            "country_code": country_code,
            "flag": _flag(country_code),
            "city": str(payload.get("city") or "") or None,
            "asn": str((payload.get("connection") or {}).get("asn") or "") or None,
        }
    except Exception:
        return {
            "ip": ip,
            "country": "Unknown",
            "country_code": "UN",
            "flag": "🏳️",
            "city": None,
            "asn": None,
        }


async def get_services() -> dict[str, Any]:
    dig_available = shutil.which("dig") is not None
    traceroute_available = shutil.which("traceroute") is not None

    resolver_results: list[dict[str, Any]] = []
    for resolver in _RESOLVERS:
        resolver_id = str(resolver.get("id") or "")
        resolver_label = str(resolver.get("label") or resolver_id)
        resolver_ip = str(resolver.get("ip") or "").strip() or None

        target_results: list[dict[str, Any]] = []
        for target_id, target in _TARGETS:
            resolved = await _resolve_dns(target, resolver_ip, dig_available)
            target_results.append(
                {
                    "target_id": target_id,
                    "target": target,
                    "ok": bool(resolved.get("ok")),
                    "latency_ms": resolved.get("latency_ms"),
                    "ip": resolved.get("ip"),
                    "error": resolved.get("error"),
                }
            )

        latencies = [
            float(entry["latency_ms"])
            for entry in target_results
            if isinstance(entry.get("latency_ms"), (int, float)) and entry.get("ok")
        ]
        resolver_results.append(
            {
                "resolver_id": resolver_id,
                "resolver_label": resolver_label,
                "resolver_ip": resolver_ip,
                "targets": target_results,
                "ok": any(entry.get("ok") for entry in target_results),
                "ok_count": sum(1 for entry in target_results if entry.get("ok")),
                "avg_latency_ms": _safe_round(mean(latencies), 1) if latencies else None,
            }
        )

    trace_results = await asyncio.gather(
        *[_trace_target(target_id, target, traceroute_available=traceroute_available) for target_id, target in _TARGETS]
    )

    ips_to_geo: set[str] = set()
    for resolver in resolver_results:
        if resolver.get("resolver_ip"):
            ips_to_geo.add(str(resolver["resolver_ip"]))
        for row in resolver.get("targets", []):
            ip = row.get("ip")
            if ip:
                ips_to_geo.add(str(ip))

    for trace in trace_results:
        for hop in trace.get("hops", []):
            ip = hop.get("ip")
            if ip:
                ips_to_geo.add(str(ip))

    geo_cache: dict[str, dict[str, Any]] = {}
    geo_timeout = httpx.Timeout(4.5, connect=2.0)
    async with httpx.AsyncClient(timeout=geo_timeout, follow_redirects=True) as geo_client:
        geo_entries = await asyncio.gather(*[_geo_lookup(geo_client, ip) for ip in sorted(ips_to_geo)])
    for entry in geo_entries:
        token = str(entry.get("ip") or "").strip()
        if token:
            geo_cache[token] = entry

    for resolver in resolver_results:
        resolver_ip = resolver.get("resolver_ip")
        resolver_geo = geo_cache.get(str(resolver_ip), {}) if resolver_ip else {}
        resolver["resolver_country"] = resolver_geo.get("country") if resolver_geo else "System"
        resolver["resolver_country_code"] = resolver_geo.get("country_code") if resolver_geo else "SYS"
        resolver["resolver_flag"] = resolver_geo.get("flag") if resolver_geo else "🧭"

        for row in resolver.get("targets", []):
            ip = str(row.get("ip") or "").strip()
            geo = geo_cache.get(ip, {}) if ip else {}
            row["country"] = geo.get("country") if geo else None
            row["country_code"] = geo.get("country_code") if geo else None
            row["flag"] = geo.get("flag") if geo else "🏳️"

    trace_targets: list[dict[str, Any]] = []
    trace_nodes: list[dict[str, Any]] = []

    for trace in trace_results:
        hops = trace.get("hops", [])
        enriched_hops: list[dict[str, Any]] = []
        countries: list[str] = []
        rtts: list[float] = []

        for hop in hops:
            ip = str(hop.get("ip") or "").strip()
            geo = geo_cache.get(ip, {}) if ip else {}
            country_code = str(geo.get("country_code") or "").strip().upper()
            if country_code and country_code not in countries:
                countries.append(country_code)
            rtt = hop.get("rtt_ms")
            if isinstance(rtt, (int, float)):
                rtts.append(float(rtt))
            enriched = {
                **hop,
                "country": geo.get("country") if geo else ("timeout" if hop.get("timeout") else "Unknown"),
                "country_code": country_code or ("LAN" if _is_private_ip(ip) else "UN"),
                "flag": geo.get("flag") if geo else ("⏱" if hop.get("timeout") else "🏳️"),
                "city": geo.get("city") if geo else None,
                "asn": geo.get("asn") if geo else None,
            }
            enriched_hops.append(enriched)

            title = f"{trace.get('target')} · #{hop.get('hop')}"
            if ip:
                title = f"{title} · {ip}"
            value = "⏱ timeout"
            if ip:
                label_country = str(enriched.get("country") or "Unknown")
                rtt_label = f" · {enriched.get('rtt_ms')} ms" if enriched.get("rtt_ms") is not None else ""
                value = f"{enriched.get('flag', '🏳️')} {label_country}{rtt_label}"
            trace_nodes.append(
                {
                    "name": title,
                    "value": value,
                }
            )

        final_hop = next((hop for hop in reversed(enriched_hops) if hop.get("ip")), None)
        final_flag = str(final_hop.get("flag") or "🏳️") if final_hop else "🏳️"
        final_country = str(final_hop.get("country") or "Unknown") if final_hop else "Unknown"
        path_flags = [
            _flag(code)
            for code in countries
            if code and code not in {"LAN", "UN", "SYS"}
        ]
        path_compact = "→".join(path_flags[:5]) if path_flags else "n/a"
        avg_rtt = _safe_round(mean(rtts), 1) if rtts else None

        trace_targets.append(
            {
                "target_id": trace.get("target_id"),
                "target": trace.get("target"),
                "ok": trace.get("ok"),
                "hop_count": len(enriched_hops),
                "avg_rtt_ms": avg_rtt,
                "countries": countries,
                "path_compact": path_compact,
                "final_ip": final_hop.get("ip") if final_hop else None,
                "final_country": final_country,
                "final_flag": final_flag,
                "hops": enriched_hops,
                "error": trace.get("error"),
            }
        )

    summary_entries: list[dict[str, str]] = []
    all_country_codes: list[str] = []

    resolver_by_target: dict[str, dict[str, Any]] = {}
    for target_id, target in _TARGETS:
        best: dict[str, Any] | None = None
        for resolver in resolver_results:
            for entry in resolver.get("targets", []):
                if entry.get("target_id") != target_id:
                    continue
                if not entry.get("ok"):
                    continue
                if best is None:
                    best = {
                        "resolver": resolver,
                        "entry": entry,
                    }
                    continue
                current_latency = entry.get("latency_ms")
                best_latency = best["entry"].get("latency_ms")
                if isinstance(current_latency, (int, float)) and isinstance(best_latency, (int, float)):
                    if float(current_latency) < float(best_latency):
                        best = {
                            "resolver": resolver,
                            "entry": entry,
                        }
        if best is None:
            resolver_by_target[target_id] = {
                "resolver_label": "n/a",
                "latency_ms": None,
                "ip": None,
                "flag": "🏳️",
            }
        else:
            resolver_by_target[target_id] = {
                "resolver_label": best["resolver"].get("resolver_label"),
                "latency_ms": best["entry"].get("latency_ms"),
                "ip": best["entry"].get("ip"),
                "flag": best["entry"].get("flag") or "🏳️",
            }

    trace_by_target = {str(item.get("target_id") or ""): item for item in trace_targets}
    for target_id, target in _TARGETS:
        dns_part = resolver_by_target.get(target_id, {})
        trace_part = trace_by_target.get(target_id, {})
        final_flag = str(trace_part.get("final_flag") or "🏳️")
        dns_latency = dns_part.get("latency_ms")
        hops = trace_part.get("hop_count")
        avg_rtt = trace_part.get("avg_rtt_ms")
        path_compact = str(trace_part.get("path_compact") or "n/a")
        if isinstance(trace_part.get("countries"), list):
            for code in trace_part.get("countries", []):
                token = str(code or "").upper()
                if token and token not in all_country_codes:
                    all_country_codes.append(token)

        dns_label = f"DNS {dns_latency} ms" if isinstance(dns_latency, (int, float)) else "DNS n/a"
        hop_label = f"hops {hops}" if isinstance(hops, int) else "hops n/a"
        rtt_label = f"RTT {avg_rtt} ms" if isinstance(avg_rtt, (int, float)) else "RTT n/a"

        summary_entries.append(
            {
                "name": f"{final_flag} {target}",
                "value": f"{dns_label} · {hop_label} · {rtt_label} · {path_compact}",
            }
        )

    resolver_entries: list[dict[str, str]] = []
    for resolver in resolver_results:
        resolver_entries.append(
            {
                "name": f"{resolver.get('resolver_flag', '🧭')} {resolver.get('resolver_label')}",
                "value": (
                    f"ok {resolver.get('ok_count')}/{len(_TARGETS)}"
                    + (
                        f" · {resolver.get('avg_latency_ms')} ms"
                        if isinstance(resolver.get("avg_latency_ms"), (int, float))
                        else " · n/a"
                    )
                ),
            }
        )

    total_targets = len(_TARGETS)
    trace_ok = sum(1 for item in trace_targets if item.get("ok"))
    dns_ok = sum(
        1
        for target_id, _target in _TARGETS
        if resolver_by_target.get(target_id, {}).get("ip")
    )
    warning = ""
    if dns_ok < total_targets or trace_ok < total_targets:
        warning = "⚠ Частично недоступны DNS/trace цели"

    countries_public = [code for code in all_country_codes if code not in {"LAN", "UN", "SYS"}]
    country_flags = [_flag(code) for code in countries_public]
    countries_label = "Маршрут: " + (" ".join(country_flags[:10]) if country_flags else "n/a")

    return {
        "updated_at": datetime.now(UTC).isoformat(),
        "targets": [
            {
                "id": target_id,
                "host": target,
            }
            for target_id, target in _TARGETS
        ],
        "resolvers": resolver_results,
        "traces": trace_targets,
        "summary_entries": summary_entries,
        "resolver_entries": resolver_entries,
        "trace_nodes": trace_nodes,
        "summary": {
            "primary_status": f"DNS {dns_ok}/{total_targets} · Trace {trace_ok}/{total_targets}",
            "countries_label": countries_label,
            "warning": warning,
            "nodes_value": f"Узлов: {len(trace_nodes)}",
            "nodes_subtitle": f"Цели: {total_targets}",
            "nodes_trend": "",
            "dig_available": dig_available,
            "traceroute_available": traceroute_available,
        },
    }
