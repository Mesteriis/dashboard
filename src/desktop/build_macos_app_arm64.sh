#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/src/frontend"
TAURI_DIR="$FRONTEND_DIR/src-tauri"
ARTIFACTS_DIR="${OKO_DESKTOP_ARTIFACTS_DIR:-$ROOT_DIR/artifacts/macos-arm64}"
WORK_DIR="$ARTIFACTS_DIR/.work"
OUTPUT_DIR="$ARTIFACTS_DIR/output"
APP_NAME="Oko.app"
SIDE_BIN="$TAURI_DIR/binaries/oko-backend-aarch64-apple-darwin"
APP_BUNDLE_PATH="$WORK_DIR/target/aarch64-apple-darwin/release/bundle/macos/$APP_NAME"

cleanup() {
  rm -rf "$WORK_DIR"
  rm -f "$SIDE_BIN"
}

trap cleanup EXIT INT TERM

rm -rf "$OUTPUT_DIR" "$WORK_DIR"
mkdir -p "$OUTPUT_DIR" "$WORK_DIR"

if [[ -f "$HOME/.cargo/env" ]]; then
  # shellcheck disable=SC1090
  . "$HOME/.cargo/env"
fi

export CARGO_TARGET_DIR="$WORK_DIR/target"
export OKO_DESKTOP_ARTIFACTS_DIR="$ARTIFACTS_DIR"
export OKO_SIDECAR_WORK_ROOT="$WORK_DIR/sidecar"
export OKO_SIDECAR_DIST_DIR="$WORK_DIR/sidecar/dist"
export OKO_SIDECAR_BUILD_DIR="$WORK_DIR/sidecar/build"
export OKO_SIDECAR_SPEC_DIR="$WORK_DIR/sidecar/spec"
export OKO_SIDECAR_OUT_BIN="$SIDE_BIN"

"$ROOT_DIR/src/desktop/build_sidecar_macos_arm64.sh"

(
  cd "$FRONTEND_DIR"
  npm run tauri:build:arm64
)

if [[ ! -d "$APP_BUNDLE_PATH" ]]; then
  echo "Build failed: app bundle not found at $APP_BUNDLE_PATH" >&2
  exit 1
fi

ditto "$APP_BUNDLE_PATH" "$OUTPUT_DIR/$APP_NAME"
ditto -c -k --sequesterRsrc --keepParent "$OUTPUT_DIR/$APP_NAME" "$OUTPUT_DIR/$APP_NAME.zip"

echo "Desktop bundle ready:"
echo "  $OUTPUT_DIR/$APP_NAME"
echo "  $OUTPUT_DIR/$APP_NAME.zip"
