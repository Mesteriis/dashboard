from __future__ import annotations

import asyncio
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from apps.health.model.contracts import HealthCheckRequestedV1
from apps.health.service import checkers
from apps.health.service.checkers import HealthChecker
from apps.health.service.config_sync import extract_service_specs_from_config
from apps.health.service.validators import (
    clamp_interval_sec,
    clamp_latency_threshold_ms,
    clamp_timeout_ms,
    parse_tcp_target,
    validate_target,
)
from core.contracts.errors import ApiError


def _request(*, check_type: str, target: str, timeout_ms: int = 200) -> HealthCheckRequestedV1:
    return HealthCheckRequestedV1(
        service_id=uuid4(),
        item_id="svc-1",
        check_type=check_type,  # type: ignore[arg-type]
        target=target,
        timeout_ms=timeout_ms,
        latency_threshold_ms=500,
        window_size=3,
    )


def test_validators_clamp_boundaries() -> None:
    assert clamp_interval_sec(-1) == 1
    assert clamp_interval_sec(99999) == 3600
    assert clamp_timeout_ms(1) == 100
    assert clamp_timeout_ms(999999) == 120_000
    assert clamp_latency_threshold_ms(0) == 1
    assert clamp_latency_threshold_ms(130_000) == 120_000


def test_parse_tcp_target_supports_ipv6_and_validates_port() -> None:
    assert parse_tcp_target("example.org:443") == ("example.org", 443)
    assert parse_tcp_target("[2001:db8::1]:8443") == ("2001:db8::1", 8443)

    with pytest.raises(ApiError):
        parse_tcp_target("example.org")
    with pytest.raises(ApiError):
        parse_tcp_target("example.org:not-int")
    with pytest.raises(ApiError):
        parse_tcp_target("example.org:70000")


def test_validate_target_rejects_invalid_values() -> None:
    assert validate_target(check_type="http", target="https://example.org") == "https://example.org"
    assert validate_target(check_type="tcp", target="host.local:8080") == "host.local:8080"
    assert validate_target(check_type="icmp", target="localhost") == "localhost"

    with pytest.raises(ApiError):
        validate_target(check_type="http", target="ftp://example.org")
    with pytest.raises(ApiError):
        validate_target(check_type="icmp", target="bad host")

    with pytest.raises(ApiError):
        validate_target(check_type="smtp", target="x")  # type: ignore[arg-type]


async def test_health_checker_http_success_and_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Client:
        def __init__(self, status_code: int) -> None:
            self._status_code = status_code

        async def __aenter__(self) -> _Client:
            return self

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            _ = (exc_type, exc, tb)
            return False

        async def get(self, url: str):
            _ = url
            return SimpleNamespace(status_code=self._status_code)

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: _Client(status_code=204))
    ok = await HealthChecker(icmp_enabled=False).run(
        _request(check_type="http", target="https://service.local")
    )
    assert ok.success is True
    assert ok.error_message is None

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: _Client(status_code=503))
    failed = await HealthChecker(icmp_enabled=False).run(
        _request(check_type="http", target="https://service.local")
    )
    assert failed.success is False
    assert failed.error_message == "http_status_503"


async def test_health_checker_http_timeout_and_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    class _TimeoutClient:
        async def __aenter__(self) -> _TimeoutClient:
            return self

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            _ = (exc_type, exc, tb)
            return False

        async def get(self, url: str):
            _ = url
            raise TimeoutError()

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: _TimeoutClient())
    timeout = await HealthChecker(icmp_enabled=False).run(
        _request(check_type="http", target="https://service.local")
    )
    assert timeout.success is False
    assert timeout.error_message == "timeout"

    class _ErrorClient(_TimeoutClient):
        async def get(self, url: str):
            _ = url
            raise RuntimeError("boom")

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: _ErrorClient())
    failed = await HealthChecker(icmp_enabled=False).run(
        _request(check_type="http", target="https://service.local")
    )
    assert failed.success is False
    assert failed.error_message == "boom"


async def test_health_checker_tcp_success_timeout_and_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Writer:
        def __init__(self) -> None:
            self.closed = False

        def close(self) -> None:
            self.closed = True

        async def wait_closed(self) -> None:
            return None

    async def _ok_open_connection(*, host: str, port: int):
        _ = (host, port)
        return object(), _Writer()

    monkeypatch.setattr(asyncio, "open_connection", _ok_open_connection)
    success = await HealthChecker(icmp_enabled=False).run(
        _request(check_type="tcp", target="127.0.0.1:443")
    )
    assert success.success is True

    async def _slow_open_connection(*, host: str, port: int):
        _ = (host, port)
        await asyncio.sleep(0.3)
        return object(), _Writer()

    monkeypatch.setattr(asyncio, "open_connection", _slow_open_connection)
    timeout = await HealthChecker(icmp_enabled=False).run(
        _request(check_type="tcp", target="127.0.0.1:443", timeout_ms=100)
    )
    assert timeout.success is False
    assert timeout.error_message == "timeout"

    async def _error_open_connection(*, host: str, port: int):
        _ = (host, port)
        raise OSError("refused")

    monkeypatch.setattr(asyncio, "open_connection", _error_open_connection)
    failed = await HealthChecker(icmp_enabled=False).run(
        _request(check_type="tcp", target="127.0.0.1:443")
    )
    assert failed.success is False
    assert "refused" in (failed.error_message or "")


async def test_health_checker_icmp_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    checker_disabled = HealthChecker(icmp_enabled=False)
    disabled = await checker_disabled.run(_request(check_type="icmp", target="127.0.0.1"))
    assert disabled.error_message == "icmp_disabled"

    checker_no_binary = HealthChecker(icmp_enabled=True)
    checker_no_binary._ping_binary = None
    unavailable = await checker_no_binary.run(_request(check_type="icmp", target="127.0.0.1"))
    assert unavailable.error_message == "icmp_unavailable"

    class _Process:
        def __init__(self, *, output: bytes, error: bytes, returncode: int, delay: float = 0.0) -> None:
            self._output = output
            self._error = error
            self.returncode = returncode
            self._delay = delay
            self.killed = False

        async def communicate(self) -> tuple[bytes, bytes]:
            if self._delay:
                await asyncio.sleep(self._delay)
            return self._output, self._error

        def kill(self) -> None:
            self.killed = True

    checker = HealthChecker(icmp_enabled=True)
    checker._ping_binary = "ping"

    async def _proc_timeout(*args, **kwargs):
        _ = (args, kwargs)
        return _Process(output=b"", error=b"", returncode=0, delay=0.3)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _proc_timeout)
    timeout = await checker.run(_request(check_type="icmp", target="127.0.0.1", timeout_ms=100))
    assert timeout.success is False
    assert timeout.error_message == "timeout"

    async def _proc_ok(*args, **kwargs):
        _ = (args, kwargs)
        return _Process(output=b"64 bytes time=12.34 ms", error=b"", returncode=0)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _proc_ok)
    ok = await checker.run(_request(check_type="icmp", target="127.0.0.1"))
    assert ok.success is True
    assert ok.latency_ms == 12

    async def _proc_fail(*args, **kwargs):
        _ = (args, kwargs)
        return _Process(output=b"", error=b"destination unreachable", returncode=1)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _proc_fail)
    failed = await checker.run(_request(check_type="icmp", target="127.0.0.1"))
    assert failed.success is False
    assert "destination unreachable" in (failed.error_message or "")


def test_ping_latency_parser() -> None:
    assert checkers._parse_ping_latency_ms("time=7.99 ms") == 7
    assert checkers._parse_ping_latency_ms("no match") is None
    assert checkers._parse_ping_latency_ms("time=<oops ms") is None


def test_extract_service_specs_handles_dedup_and_flags() -> None:
    payload = {
        "groups": [
            {
                "id": "g1",
                "subgroups": [
                    {
                        "id": "sg1",
                        "items": [
                            {
                                "id": "svc-http",
                                "type": "link",
                                "title": "HTTP",
                                "url": "https://example.org",
                                "check_url": "https://example.org/health",
                                "monitor_health": "yes",
                                "healthcheck": {
                                    "type": "http",
                                    "timeout_ms": 750,
                                    "latency_threshold_ms": 420,
                                    "tls_verify": False,
                                },
                            },
                            {
                                "id": "svc-http",
                                "type": "link",
                                "url": "https://duplicate.example.org",
                                "monitor_health": True,
                            },
                            {
                                "id": "svc-private",
                                "type": "iframe",
                                "url": "https://192.168.1.15/",
                                "monitor_health": True,
                            },
                            {
                                "id": "svc-invalid",
                                "type": "link",
                                "url": "ftp://bad",
                                "monitor_health": True,
                            },
                        ],
                    }
                ],
            }
        ]
    }

    specs = extract_service_specs_from_config(
        config_payload=payload,
        default_interval_sec=30,
        default_timeout_ms=1000,
        default_latency_threshold_ms=500,
    )
    assert {spec.item_id for spec in specs} == {"svc-http", "svc-private"}

    by_id = {spec.item_id: spec for spec in specs}
    assert by_id["svc-http"].target == "https://example.org/health"
    assert by_id["svc-http"].enabled is True
    assert by_id["svc-http"].timeout_ms == 750
    assert by_id["svc-http"].latency_threshold_ms == 420
    assert by_id["svc-http"].tls_verify is False

    assert by_id["svc-private"].check_type == "http"
    assert by_id["svc-private"].tls_verify is False


def test_extract_service_specs_handles_invalid_groups() -> None:
    assert extract_service_specs_from_config(
        config_payload={"groups": "bad"},
        default_interval_sec=30,
        default_timeout_ms=1000,
        default_latency_threshold_ms=500,
    ) == []


def test_extract_service_specs_covers_loop_guards_and_defaults() -> None:
    payload = {
        "groups": [
            "bad-group",
            {"id": "g1", "subgroups": "bad"},
            {
                "id": "g2",
                "subgroups": [
                    "bad-subgroup",
                    {"id": "sg1", "items": "bad"},
                    {
                        "id": "sg2",
                        "items": [
                            "bad-item",
                            {"id": "", "url": "https://x"},
                            {"id": "svc-no-monitor", "type": "link", "url": "https://ok.local"},
                            {
                                "id": "svc-health-disabled",
                                "type": "link",
                                "url": "https://ok2.local",
                                "healthcheck": {"enabled": "no"},
                            },
                            {
                                "id": "svc-weird-type",
                                "type": "link",
                                "url": "https://ok3.local",
                                "monitor_health": 1,
                                "healthcheck": {"type": "smtp"},
                            },
                            {
                                "id": "svc-bad-target",
                                "type": "link",
                                "url": "https://ok4.local",
                                "monitor_health": True,
                                "healthcheck": {"type": "tcp", "target": "broken-target"},
                            },
                            {
                                "id": "svc-tcp",
                                "type": "link",
                                "url": "https://fallback.local",
                                "monitor_health": "on",
                                "healthcheck": {
                                    "type": "tcp",
                                    "target": "127.0.0.1:8080",
                                    "verify_tls": "false",
                                },
                            },
                            {
                                "id": "svc-icmp",
                                "type": "iframe",
                                "url": "https://ignored.local",
                                "monitor_health": True,
                                "healthcheck": {
                                    "type": "icmp",
                                    "target": "localhost",
                                    "insecure_skip_verify": True,
                                },
                            },
                        ],
                    },
                ],
            },
        ]
    }

    specs = extract_service_specs_from_config(
        config_payload=payload,
        default_interval_sec=10_000,
        default_timeout_ms=200_000,
        default_latency_threshold_ms=250_000,
    )
    by_id = {spec.item_id: spec for spec in specs}

    assert by_id["svc-no-monitor"].enabled is False
    assert by_id["svc-health-disabled"].enabled is False
    assert by_id["svc-weird-type"].check_type == "http"
    assert by_id["svc-weird-type"].enabled is True
    assert by_id["svc-tcp"].check_type == "tcp"
    assert by_id["svc-tcp"].target == "127.0.0.1:8080"
    assert by_id["svc-icmp"].check_type == "icmp"
    assert by_id["svc-icmp"].target == "localhost"
    assert "svc-bad-target" not in by_id

    # Clamp branches.
    assert by_id["svc-no-monitor"].interval_sec == 3600
    assert by_id["svc-no-monitor"].timeout_ms == 120_000
    assert by_id["svc-no-monitor"].latency_threshold_ms == 120_000


def test_extract_service_specs_tls_resolution_variants() -> None:
    payload = {
        "groups": [
            {
                "id": "g1",
                "subgroups": [
                    {
                        "id": "sg1",
                        "items": [
                            {
                                "id": "svc-verify-tls",
                                "url": "https://public.example.org",
                                "monitor_health": True,
                                "healthcheck": {"verify_tls": True},
                            },
                            {
                                "id": "svc-insecure-flag",
                                "url": "https://public2.example.org",
                                "monitor_health": True,
                                "healthcheck": {"insecure_skip_verify": False},
                            },
                        ],
                    }
                ],
            }
        ]
    }
    specs = extract_service_specs_from_config(
        config_payload=payload,
        default_interval_sec=30,
        default_timeout_ms=1000,
        default_latency_threshold_ms=500,
    )
    by_id = {spec.item_id: spec for spec in specs}
    assert by_id["svc-verify-tls"].tls_verify is True
    assert by_id["svc-insecure-flag"].tls_verify is True
