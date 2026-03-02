import assert from 'node:assert/strict'
import test from 'node:test'
import {
  buildOkoRequestHeaders,
  requestJson,
  resolveMergedCapabilities,
  resolveRequestUrl,
} from '../../frontend/src/features/services/requestJson.ts'
import { isApiRequestError } from '../../frontend/src/features/services/apiErrors.ts'

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

function textResponse(body = '', status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers({ 'content-type': 'text/plain' }),
    json: async () => {
      throw new Error('json disabled')
    },
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

test('resolveMergedCapabilities returns defaults without window', () => {
  delete globalThis.window
  const capabilities = resolveMergedCapabilities()
  assert.equal(capabilities.includes('read.config'), true)
  assert.equal(capabilities.includes('read.plugins.manifest'), true)
})

test('resolveMergedCapabilities merges configured capabilities', () => {
  globalThis.window = {
    __OKO_CAPABILITIES__: [' custom.exec ', '', 'read.config'],
  }
  const capabilities = resolveMergedCapabilities()
  assert.equal(capabilities.includes('custom.exec'), true)
  assert.equal(capabilities.filter((item) => item === 'read.config').length, 1)
})

test('resolveRequestUrl handles absolute, empty and runtime base', () => {
  globalThis.window = { __OKO_API_BASE__: 'http://127.0.0.1:8010/' }
  assert.equal(resolveRequestUrl(''), '')
  assert.equal(resolveRequestUrl('https://api.example.test/x'), 'https://api.example.test/x')
  assert.equal(resolveRequestUrl('/api/v1/ping'), 'http://127.0.0.1:8010/api/v1/ping')
  assert.equal(resolveRequestUrl('api/v1/ping'), 'http://127.0.0.1:8010/api/v1/ping')
})

test('buildOkoRequestHeaders uses runtime actor and merged capabilities', () => {
  globalThis.window = {
    __OKO_ACTOR__: 'frontend-admin',
    __OKO_CAPABILITIES__: ['custom.read'],
  }
  const headers = buildOkoRequestHeaders({ 'X-Trace-Id': 'trace-1' })
  assert.equal(headers['X-Oko-Actor'], 'frontend-admin')
  assert.equal(headers['X-Trace-Id'], 'trace-1')
  assert.equal(String(headers['X-Oko-Capabilities']).includes('custom.read'), true)
})

test('requestJson supports Headers instance in options', async () => {
  let captured = null
  globalThis.fetch = async (url, options) => {
    captured = { url, options }
    return jsonResponse({ ok: true })
  }
  const headers = new Headers({ 'Content-Type': 'application/json' })
  await requestJson('/api/v1/test', { method: 'post', headers })
  assert.equal(captured.options.method, 'post')
  assert.equal(captured.options.headers['content-type'], 'application/json')
  assert.equal(captured.options.headers['X-Oko-Actor'], 'frontend-local')
})

test('requestJson supports tuple headers and stringifies values', async () => {
  let captured = null
  globalThis.fetch = async (url, options) => {
    captured = { url, options }
    return jsonResponse({ ok: true })
  }
  await requestJson('/api/v1/test', {
    headers: [
      ['X-Retry', 3],
      ['X-Feature', true],
    ],
  })
  assert.equal(captured.options.headers['X-Retry'], '3')
  assert.equal(captured.options.headers['X-Feature'], 'true')
})

test('requestJson converts JSON parse errors to api parse error', async () => {
  globalThis.fetch = async () => ({
    ok: true,
    status: 200,
    headers: new Headers({ 'content-type': 'application/json' }),
    json: async () => {
      throw new SyntaxError('broken json')
    },
    text: async () => 'never',
  })

  await assert.rejects(
    () => requestJson('/api/v1/bad-json'),
    (error) => {
      assert.equal(isApiRequestError(error), true)
      assert.equal(error.kind, 'parse')
      assert.equal(error.status, 200)
      assert.equal(error.source, 'requestJson')
      return true
    },
  )
})

test('requestJson keeps backend message field for HTTP errors', async () => {
  globalThis.fetch = async () => jsonResponse({ message: 'backend denied' }, 403)
  await assert.rejects(
    () => requestJson('/api/v1/forbidden'),
    (error) => {
      assert.equal(error.message, 'backend denied')
      assert.equal(error.kind, 'http')
      return true
    },
  )
})

test('requestJson resolves detail string for HTTP errors', async () => {
  globalThis.fetch = async () => jsonResponse({ detail: 'bad request' }, 400)
  await assert.rejects(
    () => requestJson('/api/v1/bad-request'),
    (error) => {
      assert.equal(error.message, 'bad request')
      assert.equal(error.status, 400)
      return true
    },
  )
})

test('requestJson uses text body for HTTP errors when non-json', async () => {
  globalThis.fetch = async () => textResponse('teapot', 418)
  await assert.rejects(
    () => requestJson('/api/v1/teapot'),
    (error) => {
      assert.equal(error.message, 'teapot')
      assert.equal(error.status, 418)
      return true
    },
  )
})

test('requestJson formats detail array without message via JSON stringify', async () => {
  globalThis.fetch = async () =>
    jsonResponse(
      {
        detail: [{ code: 'a' }, { message: 'B' }],
      },
      422,
    )
  await assert.rejects(
    () => requestJson('/api/v1/validation'),
    (error) => {
      assert.equal(error.message, '{"code":"a"}; B')
      return true
    },
  )
})
