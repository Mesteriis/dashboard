# Build Contract

## Source Of Truth

- Backend runtime entrypoint: `backend/main.py`
- Frontend source: `frontend/src/`
- Shared runtime assets (served by backend):
`templates/index.html` and `static/assets/*`
- Desktop wrapper (Tauri): `tauri/`

## Build Targets

### Web (backend serves frontend assets)

```bash
cd frontend
npm ci
npm run build
```

`npm run build` does two things:

1. builds Vite output
2. syncs artifacts into backend runtime locations:
- `templates/index.html`
- `static/assets/*`

### Desktop (Tauri)

Development:

```bash
cd frontend
npm run tauri:dev
```

Production (ARM64):

```bash
cd frontend
npm run tauri:build:arm64
```

Both commands prepare sidecar/runtime assets before building desktop bundle.

## Runtime Profiles

- `web`: browser + external backend
- `remote`: desktop shell + external backend
- `embedded`: desktop shell + local sidecar backend

Profile sync happens via desktop bridge and updates `window.__OKO_API_BASE__` for frontend API calls.

## Output Artifacts

- Web runtime bundle for backend:
  - `templates/index.html`
  - `static/assets/*`
- Desktop artifacts:
  - `.data/artifacts/macos-arm64/output/` (from helper scripts)
  - `tauri/binaries/oko-backend-aarch64-apple-darwin` (embedded sidecar binary)

## Safety Rules

- Always run `npm ci` in `frontend/` before release builds.
- Treat `npm run build` as the only supported command for web release artifacts.
- Do not hand-edit files in `templates/index.html` or `static/assets/*`; they are generated.
