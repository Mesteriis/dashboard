# Dashboard

FastAPI + Vue dashboard for service links, health checks, iframe integrations, and optional LAN scan.

## Run locally

```bash
PYTHONPATH=src uv run uvicorn main:app --host 0.0.0.0 --port 8090
```

## Frontend

```bash
cd src/frontend
npm ci
npm run build
```

## Security and startup flags

- `DASHBOARD_ADMIN_TOKEN`: required for protected actions (`PUT /api/v1/dashboard/config`, `POST /api/v1/dashboard/lan/run`, `GET /api/v1/dashboard/iframe/{item_id}/source`).
- `DASHBOARD_HEALTHCHECK_VERIFY_TLS` (`true`/`false`, default `true`): TLS verification for service health checks.
- `DASHBOARD_ENABLE_LAN_SCAN` (`true`/`false`, default `false`): startup flag to enable LAN scan.
- `LAN_SCAN_ENABLED` (`true`/`false`, default `false`): explicit LAN scan switch (overrides startup flag).
- `LAN_SCAN_RUN_ON_STARTUP` (`true`/`false`, default `false`): trigger LAN scan immediately after app start.
- `LAN_SCAN_HTTP_VERIFY_TLS` (`true`/`false`, default `true`): TLS verification for LAN HTTP probing.

Frontend sends admin token from:

- `localStorage['dashboard_admin_token']`
- `window.__DASHBOARD_ADMIN_TOKEN__`

## Tests

```bash
uv run --group dev pytest tests/backend
cd src/frontend && npm test
```
