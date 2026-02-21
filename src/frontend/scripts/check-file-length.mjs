import { readFile, readdir, stat } from 'node:fs/promises'
import path from 'node:path'

const ROOT = process.cwd()
const THRESHOLD = 100
const SCAN_DIRS = ['src', 'tests']
const EXTENSIONS = new Set(['.js', '.mjs', '.vue', '.css', '.scss'])

// Temporary exception while store logic is being split into domain modules.
const ALLOWLIST = new Set(['src/stores/dashboardStore.js'])

async function walk(dir) {
  const entries = await readdir(dir, { withFileTypes: true })
  const files = []

  for (const entry of entries) {
    if (entry.name.startsWith('.')) continue
    const full = path.join(dir, entry.name)

    if (entry.isDirectory()) {
      files.push(...(await walk(full)))
      continue
    }

    if (!EXTENSIONS.has(path.extname(entry.name))) continue
    files.push(full)
  }

  return files
}

async function main() {
  const files = []
  for (const dir of SCAN_DIRS) {
    const fullDir = path.join(ROOT, dir)
    files.push(...(await walk(fullDir)))
  }

  const oversized = []
  for (const fullPath of files) {
    const relPath = path.relative(ROOT, fullPath).replaceAll(path.sep, '/')
    const content = await stat(fullPath)
    if (!content.isFile()) continue

    const text = await readFile(fullPath, 'utf8')
    let lines = text.split('\n').length
    if (text.endsWith('\n')) lines -= 1
    if (lines > THRESHOLD) {
      oversized.push({ relPath, lines, allowlisted: ALLOWLIST.has(relPath) })
    }
  }

  oversized.sort((a, b) => b.lines - a.lines)

  if (!oversized.length) {
    console.log(`OK: all files are <= ${THRESHOLD} lines`)
    return
  }

  console.log(`Files over ${THRESHOLD} lines:`)
  for (const row of oversized) {
    const marker = row.allowlisted ? ' [allowlisted]' : ''
    console.log(`- ${row.lines.toString().padStart(4, ' ')}  ${row.relPath}${marker}`)
  }

  const blocking = oversized.filter((row) => !row.allowlisted)
  if (blocking.length) {
    process.exitCode = 1
  }
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
