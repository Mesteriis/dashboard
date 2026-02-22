import assert from 'node:assert/strict'
import test from 'node:test'
import {
  fetchDashboardConfig,
  fetchDashboardConfigBackup,
  fetchDashboardHealth,
  fetchIframeSource,
  fetchLanScanState,
  restoreDashboardConfig,
  triggerLanScan,
  updateDashboardConfig,
} from '../../src/frontend/src/services/dashboardApi.js'

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

function textResponse(body = '', headers = {}) {
  return {
    ok: true,
    status: 200,
    headers: new Headers(headers),
    json: async () => ({ value: body }),
    text: async () => body,
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

test('fetchDashboardConfig and fetchLanScanState call expected endpoints', async () => {
  const paths = []
  globalThis.fetch = async (path) => {
    paths.push(path)
    return jsonResponse({ ok: true })
  }

  await fetchDashboardConfig()
  await fetchLanScanState()
  assert.deepEqual(paths, ['/api/v1/dashboard/config', '/api/v1/dashboard/lan/state'])
})

test('fetchDashboardHealth encodes repeated item_id query params', async () => {
  let path = ''
  globalThis.fetch = async (nextPath) => {
    path = nextPath
    return jsonResponse({ items: [] })
  }

  await fetchDashboardHealth(['a', 'b c'])
  assert.equal(path, '/api/v1/dashboard/health?item_id=a&item_id=b+c')
})

test('updateDashboardConfig uses PUT and JSON body', async () => {
  let options = null
  globalThis.fetch = async (_path, nextOptions) => {
    options = nextOptions
    return jsonResponse({ config: { app: { id: 'ok' } } })
  }

  await updateDashboardConfig({ app: { id: 'ok' } })
  assert.equal(options.method, 'PUT')
  assert.equal(options.headers['Content-Type'], 'application/json')
  assert.equal(options.body, JSON.stringify({ app: { id: 'ok' } }))
})

test('fetchIframeSource resolves runtime URL and triggerLanScan uses POST', async () => {
  globalThis.window = {
    __OKO_API_BASE__: 'http://127.0.0.1:9000',
  }
  const calls = []
  globalThis.fetch = async (path, options) => {
    calls.push({ path, options })
    if (calls.length === 1) {
      return jsonResponse({ src: '/api/v1/dashboard/iframe/item%2Fid/proxy', proxied: true })
    }
    return jsonResponse({ ok: true })
  }

  const iframeSource = await fetchIframeSource('item/id')
  await triggerLanScan()
  assert.equal(calls[0].path, 'http://127.0.0.1:9000/api/v1/dashboard/iframe/item%2Fid/source')
  assert.equal(iframeSource.src, 'http://127.0.0.1:9000/api/v1/dashboard/iframe/item%2Fid/proxy')
  assert.equal(calls[1].path, 'http://127.0.0.1:9000/api/v1/dashboard/lan/run')
  assert.equal(calls[1].options.method, 'POST')
})

test('fetchDashboardConfigBackup returns yaml payload with filename from content-disposition', async () => {
  globalThis.fetch = async (path) => {
    assert.equal(path, '/api/v1/dashboard/config/backup')
    return textResponse('version: 1\n', {
      'content-disposition': 'attachment; filename="dashboard-backup.yaml"',
      'content-type': 'application/x-yaml',
    })
  }

  const payload = await fetchDashboardConfigBackup()
  assert.equal(payload.yaml, 'version: 1\n')
  assert.equal(payload.filename, 'dashboard-backup.yaml')
})

test('restoreDashboardConfig posts yaml payload', async () => {
  let call = null
  globalThis.fetch = async (path, options) => {
    call = { path, options }
    return jsonResponse({ ok: true })
  }

  await restoreDashboardConfig('version: 1\n')
  assert.equal(call.path, '/api/v1/dashboard/config/restore')
  assert.equal(call.options.method, 'POST')
  assert.equal(call.options.headers['Content-Type'], 'application/json')
  assert.equal(call.options.body, JSON.stringify({ yaml: 'version: 1\n' }))
})
