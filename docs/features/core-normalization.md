# Core Normalization (SQLite-first)

This backend now runs with a normalized core model:

- SQLite is the only runtime source of truth.
- YAML/JSON/TOML are bootstrap/import sources only.
- All infra actions go through Action Gateway.
- Events are immutable and streamed via SSE.
- Public API is versioned under `/api/v1`.
- Security policy is default-deny by capability.

## Core tables

- `config_revisions` (append-only)
- `app_state` (active revision pointer)
- `actions` (gateway execution history)
- `audit_log` (allow/deny/execution audit trail)

## Required headers

- `X-Oko-Actor`: actor identity
- `X-Oko-Capabilities`: comma-separated capabilities

## Core endpoints

- `GET /api/v1/state`
- `GET /api/v1/config`
- `POST /api/v1/config/import`
- `POST /api/v1/config/patch`
- `POST /api/v1/config/rollback`
- `GET /api/v1/config/revisions`
- `GET /api/v1/events/stream`
- `GET /api/v1/widgets/registry`
- `GET /api/v1/actions/registry`
- `POST /api/v1/actions/validate`
- `POST /api/v1/actions/execute`
- `GET /api/v1/actions/history`

## Runtime settings

- `OKO_DB_FILE`
- `OKO_BOOTSTRAP_CONFIG_FILE`
- `OKO_EVENTS_KEEPALIVE_SEC`
- `OKO_ACTIONS_EXECUTE_ENABLED`

## Registered actions (default)

- `system.echo` (`exec.system.echo`)
- `system.ping` (`exec.system.ping`)
