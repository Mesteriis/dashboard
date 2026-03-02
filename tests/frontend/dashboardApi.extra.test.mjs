import assert from 'node:assert/strict'
import test from 'node:test'
import { isApiRequestError } from '../../frontend/src/features/services/apiErrors.ts'
import {
  executeActionEnvelope,
  fetchDashboardConfigBackup,
  restoreDashboardConfig,
  unsupportedFeature,
  updateDashboardConfig,
  validateActionEnvelope,
  validateDashboardYaml,
} from '../../frontend/src/features/services/dashboardApi.ts'

const originalFetch = globalThis.fetch
const hadWindow = 'window' in globalThis
const originalWindow = globalThis.window

function jsonResponse(body = {}, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers({ 'content-type': 'application/json' }),
    json: async () => body,
    text: async () => JSON.stringify(body),
  }
}

test.afterEach(() => {
  globalThis.fetch = originalFetch
  if (hadWindow) {
    globalThis.window = originalWindow
  } else {
    delete globalThis.window
  }
})

test('updateDashboardConfig uses direct config payload when provided', async () => {
  globalThis.fetch = async () =>
    jsonResponse({
      config: {
        version: 2,
        app: { id: 'direct' },
      },
    })

  const result = await updateDashboardConfig({ app: { id: 'client' } })
  assert.deepEqual(result.config, {
    version: 2,
    app: { id: 'direct' },
  })
})

test('updateDashboardConfig falls back to input object', async () => {
  globalThis.fetch = async () => jsonResponse({ ok: true })
  const nextConfig = { app: { id: 'fallback' } }
  const result = await updateDashboardConfig(nextConfig)
  assert.deepEqual(result.config, nextConfig)
})

test('updateDashboardConfig falls back to empty object for non-object input', async () => {
  globalThis.fetch = async () => jsonResponse({ ok: true })
  const result = await updateDashboardConfig('invalid-payload')
  assert.deepEqual(result.config, {})
})

test('validateDashboardYaml normalizes malformed backend payload', async () => {
  globalThis.fetch = async () => jsonResponse({ valid: 0, issues: 'not-array' })
  const result = await validateDashboardYaml('version: 1\n')
  assert.equal(result.valid, false)
  assert.deepEqual(result.issues, [])
})

test('restoreDashboardConfig returns backup payload', async () => {
  globalThis.fetch = async () => jsonResponse({ imported: true })
  const result = await restoreDashboardConfig('version: 1\n')
  assert.deepEqual(result, {
    yaml: 'version: 1\n',
    filename: 'dashboard-restored.yaml',
  })
})

test('fetchDashboardConfigBackup appends trailing newline in yaml-like payload', async () => {
  globalThis.fetch = async () => jsonResponse({ version: 1, app: { id: 'demo' } })
  const result = await fetchDashboardConfigBackup()
  assert.equal(result.yaml.endsWith('\n'), true)
  assert.match(result.filename, /^dashboard-backup-/)
})

test('validateActionEnvelope uses validate endpoint', async () => {
  let requestPath = ''
  let requestOptions = null
  globalThis.fetch = async (path, options) => {
    requestPath = path
    requestOptions = options
    return jsonResponse({ allowed: true })
  }

  const payload = { capability: 'exec.actions.validate' }
  const result = await validateActionEnvelope(payload)
  assert.deepEqual(result, { allowed: true })
  assert.equal(requestPath, '/api/v1/actions/validate')
  assert.equal(requestOptions.method, 'POST')
  assert.equal(requestOptions.body, JSON.stringify(payload))
})

test('executeActionEnvelope uses execute endpoint', async () => {
  let requestPath = ''
  let requestOptions = null
  globalThis.fetch = async (path, options) => {
    requestPath = path
    requestOptions = options
    return jsonResponse({ executed: true })
  }

  const payload = { capability: 'exec.actions.execute' }
  const result = await executeActionEnvelope(payload)
  assert.deepEqual(result, { executed: true })
  assert.equal(requestPath, '/api/v1/actions/execute')
  assert.equal(requestOptions.method, 'POST')
  assert.equal(requestOptions.body, JSON.stringify(payload))
})

test('unsupportedFeature throws structured api error', async () => {
  await assert.rejects(
    () => unsupportedFeature('disabled'),
    (error) => {
      assert.equal(isApiRequestError(error), true)
      assert.equal(error.status, 410)
      assert.equal(error.kind, 'http')
      assert.equal(error.method, 'GET')
      assert.equal(error.source, 'dashboardApi')
      assert.equal(error.url, '/api/v1')
      return true
    },
  )
})
