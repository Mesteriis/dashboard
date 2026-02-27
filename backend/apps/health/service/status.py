from __future__ import annotations

from statistics import mean

from apps.health.model.contracts import EvaluatedHealthState, HealthSample

_ICMP_UNAVAILABLE_ERRORS = {"icmp_disabled", "icmp_unavailable"}


def evaluate_health(
    *,
    samples: list[HealthSample],
    latency_threshold_ms: int,
    window_size: int,
) -> EvaluatedHealthState:
    if not samples:
        return EvaluatedHealthState(
            status="unknown",
            avg_latency_ms=None,
            success_rate=0.0,
            error_rate=1.0,
            consecutive_failures=0,
            sample_count=0,
        )

    window = samples[: max(1, window_size)]
    sample_count = len(window)

    # Check if all samples failed due to ICMP being unavailable
    if all(
        (not sample.success) and str(sample.error_message or "").strip() in _ICMP_UNAVAILABLE_ERRORS
        for sample in window
    ):
        return EvaluatedHealthState(
            status="unknown",
            avg_latency_ms=None,
            success_rate=0.0,
            error_rate=1.0,
            consecutive_failures=sample_count,
            sample_count=sample_count,
        )

    success_count = sum(1 for sample in window if sample.success)
    success_rate = success_count / sample_count
    error_rate = 1.0 - success_rate

    latencies = [sample.latency_ms for sample in window if sample.success and sample.latency_ms is not None]
    avg_latency = float(mean(latencies)) if latencies else None

    consecutive_failures = 0
    for sample in window:
        if sample.success:
            break
        consecutive_failures += 1

    is_down = sample_count >= window_size and success_count == 0
    if is_down:
        status = "down"
    elif success_rate < 0.90 or (avg_latency is not None and avg_latency > latency_threshold_ms):
        status = "degraded"
    else:
        status = "online"

    return EvaluatedHealthState(
        status=status,
        avg_latency_ms=avg_latency,
        success_rate=success_rate,
        error_rate=error_rate,
        consecutive_failures=consecutive_failures,
        sample_count=sample_count,
    )


__all__ = ["evaluate_health"]
