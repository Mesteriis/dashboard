import assert from 'node:assert/strict'
import test from 'node:test'
import {
  fetchDashboardConfig,
  fetchDashboardConfigBackup,
  restoreDashboardConfig,
  updateDashboardConfig,
  validateDashboardYaml,
} from '../../frontend/src/services/dashboardApi.ts'

const originalFetch = globalThis.fetch
const hadWindow = 'window' in globalThis
const originalWindow = globalThis.window

function jsonResponse(body = {}) {
  return {
    ok: true,
    status: 200,
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

test('fetchDashboardConfig calls new core endpoint', async () => {
  let path = ''
  globalThis.fetch = async (nextPath) => {
    path = nextPath
    return jsonResponse({ version: 1, app: { id: 'ok' } })
  }

  await fetchDashboardConfig()
  assert.equal(path, '/api/v1/config')
})

test('updateDashboardConfig uses config patch endpoint', async () => {
  let call = null
  globalThis.fetch = async (path, options) => {
    call = { path, options }
    return jsonResponse({ active_state: { active_revision: 2 } })
  }

  await updateDashboardConfig({ app: { id: 'ok' } })
  assert.equal(call.path, '/api/v1/config/patch')
  assert.equal(call.options.method, 'POST')
  assert.equal(call.options.headers['Content-Type'], 'application/json')
  assert.equal(call.options.body, JSON.stringify({ patch: { app: { id: 'ok' } }, source: 'patch' }))
})

test('updateDashboardConfig returns config from revision payload', async () => {
  globalThis.fetch = async () =>
    jsonResponse({
      active_state: { active_revision: 2 },
      revision: {
        payload: {
          version: 1,
          app: { id: 'demo' },
          layout: { pages: [{ id: 'home' }] },
        },
      },
    })

  const result = await updateDashboardConfig({ app: { id: 'ok' } })
  assert.deepEqual(result.config, {
    version: 1,
    app: { id: 'demo' },
    layout: { pages: [{ id: 'home' }] },
  })
})

test('validateDashboardYaml uses config validate endpoint', async () => {
  let call = null
  globalThis.fetch = async (path, options) => {
    call = { path, options }
    return jsonResponse({ valid: true, issues: [] })
  }

  const result = await validateDashboardYaml('version: 1\napp:\n  id: demo\n')
  assert.equal(call.path, '/api/v1/config/validate')
  assert.equal(call.options.method, 'POST')
  assert.equal(result.valid, true)
  assert.deepEqual(result.issues, [])
})

test('restoreDashboardConfig uses config import endpoint', async () => {
  let call = null
  globalThis.fetch = async (path, options) => {
    call = { path, options }
    return jsonResponse({ active_state: { active_revision: 3 } })
  }

  await restoreDashboardConfig('version: 1\n')
  assert.equal(call.path, '/api/v1/config/import')
  assert.equal(call.options.method, 'POST')
  assert.equal(call.options.headers['Content-Type'], 'application/json')
  assert.equal(
    call.options.body,
    JSON.stringify({ format: 'yaml', payload: 'version: 1\n', source: 'import' }),
  )
})

test('fetchDashboardConfigBackup is generated from config payload', async () => {
  globalThis.fetch = async () => jsonResponse({ version: 1, app: { id: 'demo' } })

  const payload = await fetchDashboardConfigBackup()
  assert.ok(payload.yaml.includes('"version": 1'))
  assert.ok(payload.filename.startsWith('dashboard-backup-'))
})
