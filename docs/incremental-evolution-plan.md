# Oko Incremental Evolution Plan (No Architectural Rewrite)

This document describes additive, low-risk improvements for the existing `Vue 3 + FastAPI` dashboard.

## Constraints Kept
- No architecture rewrite.
- No layout rebuild.
- No graph visualizations.
- No heavy worker/orchestration layer.
- Minimal and backward-compatible schema changes.

## 1) Smart Health Logic

### What to add
- Multi-level health state: `online`, `degraded`, `down`, `unknown`, plus `indirect_failure` (from dependencies).
- Threshold-based degradation by latency.
- Better error classification (`timeout`, `dns_error`, `ssl_error`, `connection_error`, `http_error`).
- Partial availability rule:
  - `2xx-3xx` -> `online`
  - `4xx` -> configurable: default `degraded` (service is reachable but functionally failing)
  - `5xx` -> `down`

### Minimal schema changes
Add optional fields in `HealthcheckConfig` and response model only.

```python
class HealthcheckThresholds(BaseModel):
    degraded_latency_ms: int = Field(default=700, ge=1, le=120000)
    down_latency_ms: int = Field(default=3000, ge=1, le=120000)
    degrade_on_http_4xx: bool = True

class HealthcheckConfig(BaseModel):
    type: Literal["http"] = "http"
    url: AnyHttpUrl
    interval_sec: int = Field(default=30, ge=1, le=3600)
    timeout_ms: int = Field(default=1500, ge=100, le=120000)
    thresholds: HealthcheckThresholds | None = None
```

```python
class ItemHealthStatus(BaseModel):
    item_id: str
    ok: bool
    checked_url: str
    status_code: int | None = None
    latency_ms: int | None = None
    error: str | None = None
    level: Literal["online", "degraded", "down", "unknown", "indirect_failure"] = "unknown"
    reason: str | None = None
    error_kind: Literal["timeout", "dns_error", "ssl_error", "connection_error", "http_error", "unknown"] | None = None
```

### Calculation logic
1. Probe as today.
2. Classify transport/result into `error_kind`.
3. Compute base `level`:
   - transport exception -> `down`
   - HTTP 5xx -> `down`
   - HTTP 4xx -> `degraded` (if `degrade_on_http_4xx`) else `down`
   - HTTP 2xx/3xx + latency >= `down_latency_ms` -> `down`
   - HTTP 2xx/3xx + latency >= `degraded_latency_ms` -> `degraded`
   - else `online`
4. Keep `ok = (level == "online")` for backward compatibility.

## 2) Dependency Awareness

### What to add
- Optional service dependencies (`depends_on: [item_id]`).
- Indirect failure propagation:
  - if dependency is `down` or `indirect_failure`, child becomes `indirect_failure`
  - own raw probe result is still preserved in debug fields

### Minimal schema changes
Add optional field in item model (shared base):

```python
class BaseItemConfig(BaseModel):
    ...
    depends_on: list[str] = Field(default_factory=list)
```

### Logic
- Build `item_id -> status` map after probing all items.
- Single-pass/iterative resolve (no graph UI required):
  - detect missing dependency IDs -> child `degraded` with reason `missing_dependency`
  - for valid links, if any parent not healthy -> child `indirect_failure`
- Protect from cycles with visited-set; on cycle mark involved nodes as `degraded` reason `dependency_cycle`.

## 3) Group / Node Aggregation

### What to add
- Group-level computed counters + aggregate state.

### Response extension (optional endpoint or enrich existing config response)

```python
class AggregateStatus(BaseModel):
    total: int
    online: int
    degraded: int
    down: int
    unknown: int
    indirect_failure: int
    level: Literal["online", "degraded", "down", "unknown"]
```

### Aggregation rule
- `down` if any `down` > 0
- else `degraded` if any `degraded` or `indirect_failure` > 0
- else `online` if `online == total`
- else `unknown`

Scope:
- subgroup aggregate
- group aggregate
- optional site aggregate

## 4) Lightweight Status History

### What to add
- In-memory ring buffer for each item, last `N` samples (`N=10..30`, configurable).
- Store only compact tuples: timestamp + level + latency + status_code.

### Minimal backend shape

```python
class HealthHistoryPoint(BaseModel):
    ts: datetime
    level: Literal["online", "degraded", "down", "unknown", "indirect_failure"]
    latency_ms: int | None = None
    status_code: int | None = None

class ItemHealthStatus(BaseModel):
    ...
    history: list[HealthHistoryPoint] = Field(default_factory=list)
```

### Storage approach
- Keep in process memory (dict of deques) inside API service layer.
- No database required.
- On app restart history resets (acceptable for lightweight mode).

## 5) Quick Search / Command Palette

### What to add
- Frontend local fuzzy search over already loaded config + latest health snapshot.
- Shortcut `Ctrl/Cmd + K` for command palette.
- Search fields: title, URL host, tags, detected IP, site.

### Backend impact
- None required for first iteration.
- Optional tiny endpoint later `/dashboard/search-index` if needed for large configs.

### UI behavior
- No layout changes.
- Overlay component with existing style tokens.
- Actions per result: open, copy URL/IP, recheck.

## 6) Multi-Site Awareness

### What to add
- Optional `site` attribute for item/group.
- Filter by site in existing controls (as another lightweight filter option).

### Minimal schema

```python
class BaseItemConfig(BaseModel):
    ...
    site: str | None = None
```

Optionally also at group level:

```python
class GroupConfig(BaseModel):
    ...
    site: str | None = None
```

### Logic
- Effective site resolution priority: `item.site` -> `group.site` -> `"default"`.
- Frontend filter is client-side; backend unaffected except optional validation for known site codes list.

## 7) Manual Utility Actions

### What to add
Per item quick actions (mostly frontend-only):
- Recheck now (single item)
- Copy IP
- Open in new tab
- SSH shortcut text copy (`ssh user@ip`)

### Minimal backend addition
- New endpoint for ad-hoc check:

```python
GET /api/v1/dashboard/health/item/{item_id}
```

Returns same `ItemHealthStatus`, updates history ring buffer, and can be reused by UI action `Recheck`.

### IP source
- Reuse LAN discovery map when available.
- If unavailable, best-effort host resolve from item URL.

## Suggested Implementation Stages (each stage is a separate commit)
1. Stage A: Smart health classification + response fields (`level`, `reason`, `error_kind`).
2. Stage B: Dependency awareness (`depends_on`, indirect failure resolution, cycle/missing handling).
3. Stage C: Group/subgroup aggregate counters and state.
4. Stage D: In-memory status history ring buffer + return in health payload.
5. Stage E: Quick search / command palette (frontend-local index).
6. Stage F: Multi-site metadata + filtering.
7. Stage G: Manual utility actions + single-item recheck endpoint.

## Backward Compatibility Notes
- Keep existing `ok`, `status_code`, `latency_ms`, `error` fields intact.
- New fields are additive/optional.
- Existing UI can ignore new fields and continue to work.
- No migration is required for existing YAML if defaults are used.
