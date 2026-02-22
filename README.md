# Dashboard

FastAPI + Vue dashboard for service links, health checks, iframe integrations, and optional LAN scan.

## Run locally

```bash
PYTHONPATH=backend uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

## Frontend

```bash
cd frontend
npm ci
npm run build
```

Для `npm run dev` запросы `/api` и `/static` всегда проксируются на `http://127.0.0.1:8000`.
Сборка фронтенда (`npm run build`) автоматически синхронизирует runtime-артефакты в backend:
- `templates/index.html`
- `static/assets/*`

Единые источники истины в `ROOT_DIR`:
- `static/` для статики (иконки/шрифты/manifest + `assets/` после сборки фронта)
- `templates/` для HTML-шаблонов (`templates/index.html` генерируется сборкой фронта)

## Desktop (Tauri, macOS Apple Silicon only)

Desktop shell is implemented with Tauri and is intentionally scoped to M-chip Macs (`aarch64-apple-darwin`).

### Runtime modes

- `embedded`: backend runs as a local sidecar process inside the desktop app.
- `remote`: desktop app uses an external backend URL (default `http://127.0.0.1:8000`).

По умолчанию desktop стартует в `remote` (тонкий клиент). Переключение в `embedded` (толстый клиент) делается из `Настройки панели`.

You can switch modes from `Настройки панели -> Desktop Runtime`.

### Prerequisites (for local desktop build)

- Full Xcode + Command Line Tools
- Rust toolchain (`rustup`, `cargo`, `rustc`)
- Node dependencies installed in `frontend` (`cd frontend && npm ci`)

### Commands

```bash
cd frontend
npm run tauri:dev
npm run tauri:build:arm64
```

`npm run tauri:dev` и `npm run tauri:build:arm64` автоматически соберут sidecar, если бинарник ещё не подготовлен.

### One-command clean desktop build (recommended)

```bash
./scripts/build_macos_app_arm64.sh
```

- Final artifacts are placed in one folder: `.data/artifacts/macos-arm64/output/`
- Intermediate build files are cleaned automatically after build.
- Desktop build uses Vite base `/` (separate from web `/static/`) to avoid blank screen in macOS WebView.

### Build embedded backend sidecar (ARM64)

```bash
./scripts/build_sidecar_macos_arm64.sh
```

This produces `tauri/binaries/oko-backend-aarch64-apple-darwin`, which is bundled into the app.

`uv` is used automatically (recommended) to build the sidecar with project dependencies.
Desktop default config source of truth: root `dashboard.yaml` (it is synced to `tauri/resources/dashboard.default.yaml` during desktop build commands).

### Desktop runtime files (`~/.oko`)

Embedded desktop backend stores runtime files in the user home directory:

- `~/.oko/data/dashboard.sqlite3`
- `~/.oko/dashboard.yaml` (bootstrap-only: created on first run if DB is absent, then imported and removed)
- `~/.oko/data/lan_scan_result.json`

This keeps desktop state/config outside the app bundle and survives app updates.

Optional override for local testing:

```bash
export OKO_DESKTOP_BACKEND_BIN=/absolute/path/to/oko-backend-aarch64-apple-darwin
```

## Security and startup flags

- `DASHBOARD_HEALTHCHECK_VERIFY_TLS` (`true`/`false`, default `true`): TLS verification for service health checks.
- `DASHBOARD_HEALTH_REFRESH_SEC` (`float`, default `5`): shared backend probe interval for centralized health snapshot refresh.
- `DASHBOARD_HEALTH_SSE_KEEPALIVE_SEC` (`float`, default `15`): keepalive interval for `/api/v1/dashboard/health/stream`.
- `DASHBOARD_ENABLE_LAN_SCAN` (`true`/`false`, default `false`): startup flag to enable LAN scan.
- `LAN_SCAN_ENABLED` (`true`/`false`, default `false`): explicit LAN scan switch (overrides startup flag).
- `LAN_SCAN_RUN_ON_STARTUP` (`true`/`false`, default `false`): trigger LAN scan immediately after app start.
- `LAN_SCAN_HTTP_VERIFY_TLS` (`true`/`false`, default `true`): TLS verification for LAN HTTP probing.
- `LAN_SCAN_CIDRS` / `LAN_SCAN_NETWORKS` (comma-separated CIDR list): explicit scan networks, e.g. `192.168.1.0/24,10.0.0.0/24`.
  If unset, scanner auto-detects available local IPv4 networks (with fallback to `192.168.1.0/24`).

## Tests

```bash
uv run --group dev pytest tests/backend
cd frontend && npm run test
```
