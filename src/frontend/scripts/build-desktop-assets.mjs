import { copyFileSync, cpSync, existsSync, mkdirSync, readdirSync, rmSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const frontendDir = path.resolve(__dirname, '..')
const srcDir = path.resolve(frontendDir, '..')
const sourceStaticDir = path.join(srcDir, 'static')
const distDir = path.join(frontendDir, 'dist')
const distStaticDir = path.join(distDir, 'static')

if (!existsSync(distDir)) {
  throw new Error(`Desktop dist directory not found: ${distDir}`)
}

if (!existsSync(sourceStaticDir)) {
  throw new Error(`Static source directory not found: ${sourceStaticDir}`)
}

if (existsSync(distStaticDir)) {
  rmSync(distStaticDir, { recursive: true, force: true })
}
mkdirSync(distStaticDir, { recursive: true })

for (const entry of readdirSync(sourceStaticDir, { withFileTypes: true })) {
  if (entry.name === 'assets') continue

  const sourcePath = path.join(sourceStaticDir, entry.name)
  const destinationPath = path.join(distStaticDir, entry.name)

  if (entry.isDirectory()) {
    cpSync(sourcePath, destinationPath, { recursive: true })
    continue
  }

  if (!entry.isFile()) continue
  copyFileSync(sourcePath, destinationPath)
}

console.log(`Synced desktop static files to: ${distStaticDir}`)
