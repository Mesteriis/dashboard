from __future__ import annotations

import asyncio
import re
import shutil
from time import perf_counter

import httpx
from apps.health.model.contracts import HealthCheckRequestedV1, HealthCheckResultV1
from apps.health.service.validators import parse_tcp_target, validate_target

_PING_LATENCY_RE = re.compile(r"time[=<]([0-9.]+)\s*ms", re.IGNORECASE)


class HealthChecker:
    def __init__(self, *, icmp_enabled: bool) -> None:
        self._icmp_enabled = icmp_enabled
        self._ping_binary = shutil.which("ping")

    async def run(self, request: HealthCheckRequestedV1) -> HealthCheckResultV1:
        target = validate_target(check_type=request.check_type, target=request.target)
        if request.check_type == "http":
            return await self._run_http(request=request, target=target)
        if request.check_type == "tcp":
            return await self._run_tcp(request=request, target=target)
        if request.check_type == "icmp":
            return await self._run_icmp(request=request, target=target)

        return HealthCheckResultV1(
            service_id=request.service_id,
            item_id=request.item_id,
            check_type=request.check_type,
            target=target,
            success=False,
            latency_ms=None,
            error_message=f"unsupported_check_type:{request.check_type}",
        )

    async def _run_http(self, *, request: HealthCheckRequestedV1, target: str) -> HealthCheckResultV1:
        timeout_sec = request.timeout_ms / 1000.0
        started = perf_counter()
        try:
            async with httpx.AsyncClient(
                timeout=timeout_sec,
                follow_redirects=False,
                verify=request.tls_verify,
            ) as client:
                response = await client.get(target)
            latency_ms = max(0, int((perf_counter() - started) * 1000))
            is_success = 200 <= int(response.status_code) < 300
            return HealthCheckResultV1(
                service_id=request.service_id,
                item_id=request.item_id,
                check_type=request.check_type,
                target=target,
                success=is_success,
                latency_ms=latency_ms,
                error_message=None if is_success else f"http_status_{response.status_code}",
            )
        except TimeoutError:
            return HealthCheckResultV1(
                service_id=request.service_id,
                item_id=request.item_id,
                check_type=request.check_type,
                target=target,
                success=False,
                latency_ms=None,
                error_message="timeout",
            )
        except Exception as exc:
            return HealthCheckResultV1(
                service_id=request.service_id,
                item_id=request.item_id,
                check_type=request.check_type,
                target=target,
                success=False,
                latency_ms=None,
                error_message=str(exc)[:500],
            )

    async def _run_tcp(self, *, request: HealthCheckRequestedV1, target: str) -> HealthCheckResultV1:
        host, port = parse_tcp_target(target)
        timeout_sec = request.timeout_ms / 1000.0
        started = perf_counter()
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host=host, port=port),
                timeout=timeout_sec,
            )
            _ = reader
            writer.close()
            await writer.wait_closed()
            latency_ms = max(0, int((perf_counter() - started) * 1000))
            return HealthCheckResultV1(
                service_id=request.service_id,
                item_id=request.item_id,
                check_type=request.check_type,
                target=target,
                success=True,
                latency_ms=latency_ms,
                error_message=None,
            )
        except TimeoutError:
            return HealthCheckResultV1(
                service_id=request.service_id,
                item_id=request.item_id,
                check_type=request.check_type,
                target=target,
                success=False,
                latency_ms=None,
                error_message="timeout",
            )
        except Exception as exc:
            return HealthCheckResultV1(
                service_id=request.service_id,
                item_id=request.item_id,
                check_type=request.check_type,
                target=target,
                success=False,
                latency_ms=None,
                error_message=str(exc)[:500],
            )

    async def _run_icmp(self, *, request: HealthCheckRequestedV1, target: str) -> HealthCheckResultV1:
        if not self._icmp_enabled:
            return HealthCheckResultV1(
                service_id=request.service_id,
                item_id=request.item_id,
                check_type=request.check_type,
                target=target,
                success=False,
                latency_ms=None,
                error_message="icmp_disabled",
            )
        if not self._ping_binary:
            return HealthCheckResultV1(
                service_id=request.service_id,
                item_id=request.item_id,
                check_type=request.check_type,
                target=target,
                success=False,
                latency_ms=None,
                error_message="icmp_unavailable",
            )

        timeout_sec = max(0.1, request.timeout_ms / 1000.0)
        process = await asyncio.create_subprocess_exec(
            self._ping_binary,
            "-c",
            "1",
            target,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout_sec)
        except TimeoutError:
            process.kill()
            await process.communicate()
            return HealthCheckResultV1(
                service_id=request.service_id,
                item_id=request.item_id,
                check_type=request.check_type,
                target=target,
                success=False,
                latency_ms=None,
                error_message="timeout",
            )

        output = (stdout or b"").decode("utf-8", errors="ignore")
        err_output = (stderr or b"").decode("utf-8", errors="ignore")
        success = process.returncode == 0
        latency = _parse_ping_latency_ms(output) if success else None

        return HealthCheckResultV1(
            service_id=request.service_id,
            item_id=request.item_id,
            check_type=request.check_type,
            target=target,
            success=success,
            latency_ms=latency,
            error_message=None if success else (err_output.strip() or output.strip() or "icmp_failed")[:500],
        )


def _parse_ping_latency_ms(output: str) -> int | None:
    match = _PING_LATENCY_RE.search(output or "")
    if not match:
        return None
    try:
        latency = float(match.group(1))
    except ValueError:
        return None
    return max(0, int(latency))


__all__ = ["HealthChecker"]
