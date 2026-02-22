#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ARTIFACTS_DIR="${OKO_DESKTOP_ARTIFACTS_DIR:-$ROOT_DIR/.data/artifacts/macos-arm64}"
SIDE_WORK_ROOT="${OKO_SIDECAR_WORK_ROOT:-$ARTIFACTS_DIR/.work/sidecar}"
SIDE_DIST_DIR="${OKO_SIDECAR_DIST_DIR:-$SIDE_WORK_ROOT/dist}"
SIDE_BUILD_DIR="${OKO_SIDECAR_BUILD_DIR:-$SIDE_WORK_ROOT/build}"
SIDE_SPEC_DIR="${OKO_SIDECAR_SPEC_DIR:-$SIDE_WORK_ROOT/spec}"
OUT_BIN="${OKO_SIDECAR_OUT_BIN:-$ROOT_DIR/tauri/binaries/oko-backend-aarch64-apple-darwin}"
PYINSTALLER_CMD=(pyinstaller)

cd "$ROOT_DIR"

if command -v uv >/dev/null 2>&1; then
  PYINSTALLER_CMD=(uv run --with pyinstaller pyinstaller)
elif ! command -v pyinstaller >/dev/null 2>&1; then
  echo "pyinstaller is required. Install with: uv tool install pyinstaller (recommended)"
  exit 1
fi

rm -rf "$SIDE_DIST_DIR" "$SIDE_BUILD_DIR" "$SIDE_SPEC_DIR"
mkdir -p "$SIDE_DIST_DIR" "$SIDE_BUILD_DIR" "$SIDE_SPEC_DIR"

"${PYINSTALLER_CMD[@]}" \
  --onefile \
  --name oko-backend-aarch64-apple-darwin \
  --paths "$ROOT_DIR/backend" \
  --hidden-import main \
  --distpath "$SIDE_DIST_DIR" \
  --workpath "$SIDE_BUILD_DIR" \
  --specpath "$SIDE_SPEC_DIR" \
  "$ROOT_DIR/scripts/backend_sidecar.py"

mkdir -p "$(dirname "$OUT_BIN")"
cp "$SIDE_DIST_DIR/oko-backend-aarch64-apple-darwin" "$OUT_BIN"
chmod +x "$OUT_BIN"

echo "Sidecar binary ready: $OUT_BIN"
