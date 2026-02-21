import assert from 'node:assert/strict'
import test from 'node:test'
import {
  fetchDashboardConfig,
  fetchDashboardHealth,
  fetchIframeSource,
  fetchLanScanState,
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

function setAdminToken(token = 'admin-token') {
  globalThis.window = { localStorage: { getItem: () => token } }
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

test('updateDashboardConfig uses PUT, JSON body, and admin token header', async () => {
  setAdminToken('save-token')
  let options = null
  globalThis.fetch = async (_path, nextOptions) => {
    options = nextOptions
    return jsonResponse({ config: { app: { id: 'ok' } } })
  }

  await updateDashboardConfig({ app: { id: 'ok' } })
  assert.equal(options.method, 'PUT')
  assert.equal(options.headers['Content-Type'], 'application/json')
  assert.equal(options.headers['X-Dashboard-Token'], 'save-token')
  assert.equal(options.body, JSON.stringify({ app: { id: 'ok' } }))
})

test('fetchIframeSource and triggerLanScan require admin token and proper methods', async () => {
  setAdminToken('run-token')
  const calls = []
  globalThis.fetch = async (path, options) => {
    calls.push({ path, options })
    return jsonResponse({ ok: true })
  }

  await fetchIframeSource('item/id')
  await triggerLanScan()
  assert.equal(calls[0].path, '/api/v1/dashboard/iframe/item%2Fid/source')
  assert.equal(calls[0].options.headers['X-Dashboard-Token'], 'run-token')
  assert.equal(calls[1].path, '/api/v1/dashboard/lan/run')
  assert.equal(calls[1].options.method, 'POST')
  assert.equal(calls[1].options.headers['X-Dashboard-Token'], 'run-token')
})
