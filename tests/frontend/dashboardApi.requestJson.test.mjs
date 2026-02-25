import assert from 'node:assert/strict'
import test from 'node:test'
import { requestJson } from '../../frontend/src/features/services/dashboardApi.ts'

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
  assert.equal(call.options.credentials, 'include')
  assert.equal(call.options.headers.Accept, 'application/json')
  assert.equal(call.options.headers['X-Oko-Actor'], 'frontend-local')
  assert.ok(String(call.options.headers['X-Oko-Capabilities']).includes('read.config'))
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

test('requestJson resolves relative path against runtime api base', async () => {
  let calledPath = ''
  globalThis.window = {
    __OKO_API_BASE__: 'http://127.0.0.1:9000',
  }
  globalThis.fetch = async (path) => {
    calledPath = path
    return makeResponse({ jsonBody: { ok: true } })
  }

  const payload = await requestJson('/api/embedded')
  assert.deepEqual(payload, { ok: true })
  assert.equal(calledPath, 'http://127.0.0.1:9000/api/embedded')
})

test('requestJson supports text response bodies', async () => {
  globalThis.fetch = async () => makeResponse({ contentType: 'text/plain', textBody: 'ok-text' })
  const payload = await requestJson('/api/text')
  assert.equal(payload, 'ok-text')
})

test('requestJson returns human readable message for backend 500 errors', async () => {
  globalThis.fetch = async () =>
    makeResponse({ ok: false, status: 500, contentType: 'text/plain', textBody: '' })

  await assert.rejects(
    () => requestJson('/api/fail'),
    (error) => {
      assert.equal(
        error.message,
        'Не удалось связаться с backend. Проверьте, что сервер запущен и порт настроен корректно.',
      )
      assert.equal(error.status, 500)
      return true
    }
  )
})

test('requestJson returns human readable message for network errors', async () => {
  globalThis.fetch = async () => {
    throw new TypeError('Failed to fetch')
  }

  await assert.rejects(
    () => requestJson('/api/fail'),
    (error) => {
      assert.equal(
        error.message,
        'Не удалось подключиться к backend. Проверьте, что сервер запущен и порт совпадает.',
      )
      assert.equal(error.status, 0)
      assert.equal(error.body, null)
      return true
    }
  )
})
