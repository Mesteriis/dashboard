import assert from 'node:assert/strict'
import test from 'node:test'
import { requestJson } from '../../src/frontend/src/services/dashboardApi.js'

const originalFetch = globalThis.fetch
const hadWindow = 'window' in globalThis
const originalWindow = globalThis.window

function makeResponse({ ok = true, status = 200, contentType = 'application/json', jsonBody = {}, textBody = '' } = {}) {
  return {
    ok,
    status,
    headers: new Headers({ 'content-type': contentType }),
    json: async () => jsonBody,
    text: async () => textBody,
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

test('requestJson returns parsed JSON and sends default headers', async () => {
  let call = null
  globalThis.fetch = async (path, options) => {
    call = { path, options }
    return makeResponse({ jsonBody: { ok: true } })
  }

  const payload = await requestJson('/api/ping')
  assert.deepEqual(payload, { ok: true })
  assert.equal(call.path, '/api/ping')
  assert.equal(call.options.credentials, 'same-origin')
  assert.equal(call.options.headers.Accept, 'application/json')
})

test('requestJson formats validation errors from detail array', async () => {
  globalThis.fetch = async () =>
    makeResponse({ ok: false, status: 422, jsonBody: { detail: [{ message: 'bad A' }, { code: 'bad_b' }] } })

  await assert.rejects(
    () => requestJson('/api/fail'),
    (error) => {
      assert.equal(error.message, 'bad A; {"code":"bad_b"}')
      assert.equal(error.status, 422)
      assert.deepEqual(error.body, { detail: [{ message: 'bad A' }, { code: 'bad_b' }] })
      return true
    }
  )
})

test('requestJson adds admin token from localStorage when required', async () => {
  let headers = null
  globalThis.window = {
    localStorage: { getItem: () => '  secret-token  ' },
    __DASHBOARD_ADMIN_TOKEN__: 'fallback-token',
  }
  globalThis.fetch = async (_path, options) => {
    headers = options.headers
    return makeResponse({ jsonBody: { ok: true } })
  }

  await requestJson('/api/secure', { requireAdminToken: true })
  assert.equal(headers['X-Dashboard-Token'], 'secret-token')
})

test('requestJson falls back to global admin token and supports text response', async () => {
  globalThis.window = {
    localStorage: { getItem: () => '' },
    __DASHBOARD_ADMIN_TOKEN__: '  global-token  ',
  }
  globalThis.fetch = async (_path, options) => {
    assert.equal(options.headers['X-Dashboard-Token'], 'global-token')
    return makeResponse({ contentType: 'text/plain', textBody: 'ok-text' })
  }

  const payload = await requestJson('/api/text', { requireAdminToken: true })
  assert.equal(payload, 'ok-text')
})

test('requestJson uses embedded desktop token when runtime is embedded', async () => {
  globalThis.window = {
    localStorage: { getItem: () => '' },
    __DASHBOARD_ADMIN_TOKEN__: '',
    __OKO_DESKTOP_RUNTIME__: { desktop: true, mode: 'embedded' },
  }
  globalThis.fetch = async (_path, options) => {
    assert.equal(options.headers['X-Dashboard-Token'], 'oko-desktop-embedded')
    return makeResponse({ jsonBody: { ok: true } })
  }

  const payload = await requestJson('/api/embedded', { requireAdminToken: true })
  assert.deepEqual(payload, { ok: true })
})
