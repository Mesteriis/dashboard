import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const frontendDir = path.resolve(__dirname, "..");
const rootDir = path.resolve(frontendDir, "..");

const sourceConfig = path.join(rootDir, "dashboard.yaml");
const tauriResourcesDir = path.join(rootDir, "tauri", "resources");
const targetConfig = path.join(tauriResourcesDir, "dashboard.default.yaml");

if (!existsSync(sourceConfig)) {
  throw new Error(`Source config not found: ${sourceConfig}`);
}

mkdirSync(tauriResourcesDir, { recursive: true });
copyFileSync(sourceConfig, targetConfig);

console.log(`Synced desktop default config: ${targetConfig}`);
