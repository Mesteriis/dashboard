#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
OUT_BIN="$ROOT_DIR/src/frontend/src-tauri/binaries/oko-backend-aarch64-apple-darwin"

cd "$ROOT_DIR"

if ! command -v pyinstaller >/dev/null 2>&1; then
  echo "pyinstaller is required. Install with: uv pip install pyinstaller"
  exit 1
fi

rm -rf "$ROOT_DIR/dist/desktop-sidecar" "$ROOT_DIR/build/desktop-sidecar"

pyinstaller \
  --onefile \
  --name oko-backend-aarch64-apple-darwin \
  --distpath "$ROOT_DIR/dist/desktop-sidecar" \
  --workpath "$ROOT_DIR/build/desktop-sidecar" \
  "$ROOT_DIR/src/desktop/backend_sidecar.py"

mkdir -p "$(dirname "$OUT_BIN")"
cp "$ROOT_DIR/dist/desktop-sidecar/oko-backend-aarch64-apple-darwin" "$OUT_BIN"
chmod +x "$OUT_BIN"

echo "Sidecar binary ready: $OUT_BIN"
