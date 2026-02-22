import {
  copyFileSync,
  cpSync,
  existsSync,
  mkdirSync,
  readdirSync,
  rmSync,
} from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const frontendDir = path.resolve(__dirname, "..");
const srcDir = path.resolve(frontendDir, "..");

const distDir = path.join(frontendDir, "dist");
const distIndex = path.join(distDir, "index.html");
const distAssetsDir = path.join(distDir, "assets");

const templatesDir = path.join(srcDir, "templates");
const templateIndex = path.join(templatesDir, "index.html");

const staticDir = path.join(srcDir, "static");
const staticAssetsDir = path.join(staticDir, "assets");

if (!existsSync(distIndex)) {
  throw new Error(`Build artifact not found: ${distIndex}`);
}

mkdirSync(templatesDir, { recursive: true });
mkdirSync(staticDir, { recursive: true });

copyFileSync(distIndex, templateIndex);

if (existsSync(staticAssetsDir)) {
  rmSync(staticAssetsDir, { recursive: true, force: true });
}
if (existsSync(distAssetsDir)) {
  cpSync(distAssetsDir, staticAssetsDir, { recursive: true });
}

for (const entry of readdirSync(distDir, { withFileTypes: true })) {
  if (entry.name === "index.html") continue;
  if (entry.name === "assets") continue;

  if (entry.isDirectory()) {
    const srcFolder = path.join(distDir, entry.name);
    const dstFolder = path.join(staticDir, entry.name);
    if (existsSync(dstFolder)) {
      rmSync(dstFolder, { recursive: true, force: true });
    }
    cpSync(srcFolder, dstFolder, { recursive: true });
    continue;
  }

  if (!entry.isFile()) continue;
  if (entry.name === "index.html") continue;
  const srcFile = path.join(distDir, entry.name);
  const dstFile = path.join(staticDir, entry.name);
  copyFileSync(srcFile, dstFile);
}

console.log(`Copied template: ${templateIndex}`);
console.log(`Synced static assets to: ${staticDir}`);
