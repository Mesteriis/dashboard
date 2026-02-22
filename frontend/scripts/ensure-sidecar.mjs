import { spawnSync } from "node:child_process";
import { existsSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const frontendDir = path.resolve(__dirname, "..");
const rootDir = path.resolve(frontendDir, "..");

const sidecarPath = path.join(
  rootDir,
  "tauri",
  "binaries",
  "oko-backend-aarch64-apple-darwin",
);
const buildScript = path.join(
  rootDir,
  "scripts",
  "build_sidecar_macos_arm64.sh",
);

function hasUsableSidecar(binaryPath) {
  if (!existsSync(binaryPath)) return false;
  try {
    const stat = statSync(binaryPath);
    return stat.isFile() && stat.size > 0;
  } catch {
    return false;
  }
}

if (hasUsableSidecar(sidecarPath)) {
  console.log(`Sidecar is ready: ${sidecarPath}`);
  process.exit(0);
}

console.log("Embedded backend sidecar is missing, building it now...");
const result = spawnSync(buildScript, {
  cwd: rootDir,
  stdio: "inherit",
  env: process.env,
});

if (result.status !== 0) {
  process.exit(result.status || 1);
}

if (!hasUsableSidecar(sidecarPath)) {
  throw new Error(
    `Sidecar build completed without output binary: ${sidecarPath}`,
  );
}

console.log(`Sidecar is ready: ${sidecarPath}`);
