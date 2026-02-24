from __future__ import annotations

import json
from dataclasses import dataclass
from time import monotonic

from core.contracts.storage import StorageLimits
from core.storage.errors import StorageLimitExceeded, StorageQueryNotAllowed, StorageRateLimited


@dataclass
class _TokenBucket:
    tokens: float
    updated_at: float


class PluginQuotaGuard:
    def __init__(self) -> None:
        self._buckets: dict[tuple[str, str], _TokenBucket] = {}

    def enforce_qps(self, *, plugin_id: str, message_type: str, limits: StorageLimits) -> None:
        key = (plugin_id, message_type)
        now = monotonic()
        capacity = max(1.0, limits.max_qps)

        bucket = self._buckets.get(key)
        if bucket is None:
            self._buckets[key] = _TokenBucket(tokens=capacity - 1.0, updated_at=now)
            return

        elapsed = max(0.0, now - bucket.updated_at)
        bucket.tokens = min(capacity, bucket.tokens + elapsed * limits.max_qps)
        bucket.updated_at = now
        if bucket.tokens < 1.0:
            raise StorageRateLimited(
                f"Rate limit exceeded for plugin '{plugin_id}' message '{message_type}' (max_qps={limits.max_qps})"
            )
        bucket.tokens -= 1.0

    @staticmethod
    def enforce_kv_bytes(*, value: object, limits: StorageLimits) -> None:
        try:
            size = len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        except TypeError as exc:
            raise StorageLimitExceeded("KV value must be JSON serializable") from exc
        if size > limits.max_kv_bytes:
            raise StorageLimitExceeded(f"KV value exceeds max_kv_bytes ({size}>{limits.max_kv_bytes})")

    @staticmethod
    def enforce_row_bytes(*, row: dict[str, object], limits: StorageLimits) -> None:
        try:
            size = len(json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        except TypeError as exc:
            raise StorageLimitExceeded("Row payload must be JSON serializable") from exc
        if size > limits.max_row_bytes:
            raise StorageLimitExceeded(f"Row exceeds max_row_bytes ({size}>{limits.max_row_bytes})")

    @staticmethod
    def clamp_query_limit(*, requested: int | None, limits: StorageLimits) -> int:
        if requested is None:
            raise StorageQueryNotAllowed("table.query requires explicit limit")
        return max(1, min(requested, limits.max_query_limit))


__all__ = ["PluginQuotaGuard"]
