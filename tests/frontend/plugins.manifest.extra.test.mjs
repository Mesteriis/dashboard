import assert from 'node:assert/strict'
import test from 'node:test'
import {
  PluginManifestNotFoundError,
  PluginManifestParseError,
  getCurrentActorCapabilities,
  loadPluginManifest,
  resolveResponsePath,
} from '../../frontend/src/features/plugins/manifest.ts'
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

function manifestBase(overrides = {}) {
  return {
    plugin_id: 'autodiscover',
    version: '1.2.3',
    manifest_version: '1.0',
    plugin_api_version: '1.0',
    capabilities: ['read.plugins.services'],
    frontend: {
      renderer: 'universal',
      sandbox: true,
      customBundle: {
        enabled: false,
        sandbox: true,
        killSwitchKey: 'oko:plugins:bundle:disabled',
      },
    },
    page: {
      enabled: true,
      layout: 'content-only',
      sidebarActions: [],
      components: [],
    },
    schema: {},
    ...overrides,
  }
}

function envelope(manifestOverrides = {}, negotiationOverrides = {}) {
  return {
    plugin_id: 'autodiscover',
    manifest: manifestBase(manifestOverrides),
    negotiation: {
      accepted: true,
      fallback_used: false,
      ...negotiationOverrides,
    },
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

test('loadPluginManifest rejects empty plugin id', async () => {
  await assert.rejects(
    () => loadPluginManifest('   '),
    (error) => {
      assert.equal(error instanceof PluginManifestNotFoundError, true)
      return true
    },
  )
})

test('loadPluginManifest maps backend 404 to PluginManifestNotFoundError', async () => {
  globalThis.fetch = async () => jsonResponse({ detail: 'not found' }, 404)
  await assert.rejects(
    () => loadPluginManifest('autodiscover'),
    (error) => {
      assert.equal(error instanceof PluginManifestNotFoundError, true)
      assert.equal(error.pluginId, 'autodiscover')
      return true
    },
  )
})

test('loadPluginManifest keeps non-404 backend errors', async () => {
  globalThis.fetch = async () => jsonResponse({ detail: 'forbidden' }, 403)
  await assert.rejects(
    () => loadPluginManifest('autodiscover'),
    (error) => {
      assert.equal(isApiRequestError(error), true)
      assert.equal(error.status, 403)
      return true
    },
  )
})

test('loadPluginManifest wraps unsupported manifest version', async () => {
  globalThis.fetch = async () =>
    jsonResponse(envelope({ manifest_version: '2.0' }))
  await assert.rejects(
    () => loadPluginManifest('autodiscover'),
    (error) => {
      assert.equal(error instanceof PluginManifestParseError, true)
      assert.match(String(error.cause?.message || ''), /Unsupported manifest_version/)
      return true
    },
  )
})

test('loadPluginManifest wraps unsupported plugin api version', async () => {
  globalThis.fetch = async () =>
    jsonResponse(envelope({ plugin_api_version: '2.1' }))
  await assert.rejects(
    () => loadPluginManifest('autodiscover'),
    (error) => {
      assert.equal(error instanceof PluginManifestParseError, true)
      assert.match(String(error.cause?.message || ''), /Unsupported plugin_api_version/)
      return true
    },
  )
})

test('loadPluginManifest wraps plugin_id mismatch', async () => {
  globalThis.fetch = async () =>
    jsonResponse(envelope({ plugin_id: 'other' }))
  await assert.rejects(
    () => loadPluginManifest('autodiscover'),
    (error) => {
      assert.equal(error instanceof PluginManifestParseError, true)
      assert.match(String(error.cause?.message || ''), /plugin_id mismatch/)
      return true
    },
  )
})

test('loadPluginManifest validates dataSource object', async () => {
  globalThis.fetch = async () =>
    jsonResponse(
      envelope({
        page: {
          enabled: true,
          layout: 'content-only',
          components: [
            {
              id: 'tbl',
              type: 'data-table',
              columns: [],
              dataSource: null,
            },
          ],
        },
      }),
    )
  await assert.rejects(
    () => loadPluginManifest('autodiscover'),
    (error) => {
      assert.equal(error instanceof PluginManifestParseError, true)
      assert.match(String(error.cause?.message || ''), /dataSource must be an object/)
      return true
    },
  )
})

test('loadPluginManifest validates dataSource type and endpoint prefix', async () => {
  globalThis.fetch = async () =>
    jsonResponse(
      envelope({
        page: {
          enabled: true,
          layout: 'content-only',
          components: [
            {
              id: 'tbl',
              type: 'data-table',
              columns: [],
              dataSource: { type: 'ws', endpoint: '/api/v1/x' },
            },
          ],
        },
      }),
    )
  await assert.rejects(() => loadPluginManifest('autodiscover'))

  globalThis.fetch = async () =>
    jsonResponse(
      envelope({
        page: {
          enabled: true,
          layout: 'content-only',
          components: [
            {
              id: 'tbl',
              type: 'data-table',
              columns: [],
              dataSource: { type: 'http', endpoint: '/internal/x' },
            },
          ],
        },
      }),
    )
  await assert.rejects(
    () => loadPluginManifest('autodiscover'),
    (error) => {
      assert.equal(error instanceof PluginManifestParseError, true)
      assert.match(String(error.cause?.message || ''), /must start with \/api\/v1/)
      return true
    },
  )
})

test('loadPluginManifest normalizes data-table shape and defaults', async () => {
  globalThis.fetch = async () =>
    jsonResponse(
      envelope({
        page: {
          enabled: true,
          layout: 'dashboard',
          components: [
            {
              id: 'tbl',
              type: 'data-table',
              title: 'Services',
              columns: [
                { key: 'host_ip', label: 'Host IP' },
                { key: 'bad' },
              ],
              group_by: ['host_ip', { key: 'service', empty_label: 'n/a' }],
              dataSource: {
                type: 'http',
                endpoint: '/api/v1/plugins/autodiscover/services',
                method: 'patch',
                responsePath: 'result.items',
                body: { limit: 10 },
              },
              rowActions: [],
              loadingText: 'loading...',
              emptyText: 'empty',
              errorText: 'error',
            },
          ],
        },
      }),
    )

  const parsed = await loadPluginManifest('autodiscover')
  const table = parsed.manifest.page.components[0]
  assert.equal(table.type, 'data-table')
  assert.equal(table.dataSource.method, 'GET')
  assert.equal(table.dataSource.response_path, 'result.items')
  assert.deepEqual(table.dataSource.body, { limit: 10 })
  assert.deepEqual(table.groupBy, [
    { field: 'host_ip', label: 'host_ip', emptyLabel: 'Unknown' },
    { field: 'service', label: 'service', emptyLabel: 'n/a' },
  ])
  assert.deepEqual(table.columns, [{ key: 'host_ip', label: 'Host IP' }])
})

test('loadPluginManifest normalizes row actions defaults', async () => {
  globalThis.fetch = async () =>
    jsonResponse(
      envelope({
        page: {
          enabled: true,
          layout: 'content-only',
          components: [
            {
              id: 'tbl',
              type: 'data-table',
              columns: [],
              dataSource: {
                type: 'http',
                endpoint: '/api/v1/plugins/autodiscover/services',
              },
              rowActions: [
                { id: 'ignored', type: 'open-link' },
                {
                  id: 'add',
                  type: 'add-to-dashboard',
                  tagsFromFields: [],
                  openMode: 'same_tab',
                },
              ],
            },
          ],
        },
      }),
    )

  const parsed = await loadPluginManifest('autodiscover')
  const table = parsed.manifest.page.components[0]
  assert.equal(table.type, 'data-table')
  assert.equal(table.rowActions.length, 1)
  assert.deepEqual(table.rowActions[0], {
    id: 'add',
    type: 'add-to-dashboard',
    label: 'Add to Dashboard',
    targetGroupId: 'autodiscover',
    targetGroupTitle: 'Autodiscover',
    subgroupField: 'host_ip',
    urlField: 'url',
    tagsFromFields: ['host_ip', 'service', 'port'],
    openMode: 'same_tab',
  })
})

test('loadPluginManifest parses sidebar actions and layout fallbacks', async () => {
  globalThis.fetch = async () =>
    jsonResponse(
      envelope({
        frontend: {
          renderer: 'custom',
          sandbox: false,
          custom_bundle: {
            enabled: true,
            entry: '/bundle.js',
            integrity: 'sha256-abc',
            sandbox: false,
            killSwitchKey: 'disable-key',
          },
        },
        page: {
          enabled: true,
          layout: 'not-supported',
          sidebar_actions: [
            { id: 'a', route: '/a', target: 'new_tab', title: '' },
            { id: 'b', route: '/b', target: 'wrong', icon: 'cpu' },
            { id: '', route: '/skip' },
          ],
          components: [],
        },
      }),
    )

  const parsed = await loadPluginManifest('autodiscover')
  assert.equal(parsed.manifest.frontend.renderer, 'custom')
  assert.equal(parsed.manifest.frontend.sandbox, false)
  assert.equal(parsed.manifest.frontend.customBundle.enabled, true)
  assert.equal(parsed.manifest.frontend.customBundle.entry, '/bundle.js')
  assert.equal(parsed.manifest.frontend.customBundle.integrity, 'sha256-abc')
  assert.equal(parsed.manifest.frontend.customBundle.sandbox, false)
  assert.equal(parsed.manifest.frontend.customBundle.killSwitchKey, 'disable-key')
  assert.equal(parsed.manifest.page.layout, 'content-only')
  assert.deepEqual(parsed.manifest.page.sidebarActions, [
    { id: 'a', title: 'a', route: '/a', target: 'new_tab' },
    { id: 'b', title: 'b', icon: 'cpu', route: '/b', target: 'same_tab' },
  ])
})

test('loadPluginManifest keeps negotiation details and fallback plugin id', async () => {
  globalThis.fetch = async () =>
    jsonResponse({
      manifest: manifestBase(),
      negotiation: {
        accepted: false,
        fallback_used: true,
        reason: 'fallback',
        errors: ['a', '', 'b'],
        supported_manifest_major: '1',
        supported_plugin_api_major: 1,
      },
    })

  const parsed = await loadPluginManifest('autodiscover')
  assert.equal(parsed.plugin_id, 'autodiscover')
  assert.deepEqual(parsed.negotiation, {
    accepted: false,
    fallback_used: true,
    reason: 'fallback',
    errors: ['a', 'b'],
    supported_manifest_major: 1,
    supported_plugin_api_major: 1,
  })
})

test('loadPluginManifest keeps defaults for missing optional sections', async () => {
  globalThis.fetch = async () =>
    jsonResponse(
      envelope({
        capabilities: ['x', '', 'y'],
        frontend: {},
        page: {},
        schema: null,
      }),
    )

  const parsed = await loadPluginManifest('autodiscover')
  assert.deepEqual(parsed.manifest.capabilities, ['x', 'y'])
  assert.equal(parsed.manifest.frontend.renderer, 'universal')
  assert.equal(parsed.manifest.frontend.customBundle.killSwitchKey, 'oko:plugins:bundle:disabled')
  assert.equal(parsed.manifest.page.enabled, false)
  assert.deepEqual(parsed.manifest.page.components, [])
  assert.deepEqual(parsed.manifest.page.sidebarActions, [])
  assert.deepEqual(parsed.manifest.schema, {})
})

test('getCurrentActorCapabilities merges runtime and defaults', () => {
  globalThis.window = {
    __OKO_CAPABILITIES__: ['custom.read', 'read.config', ''],
  }
  const capabilities = getCurrentActorCapabilities()
  assert.equal(capabilities.has('custom.read'), true)
  assert.equal(capabilities.has('read.config'), true)
  assert.equal(capabilities.has('read.plugins.manifest'), true)
})

test('resolveResponsePath resolves nested values and handles missing path', () => {
  const payload = {
    result: {
      items: {
        total: 42,
      },
    },
  }
  assert.equal(resolveResponsePath(payload, undefined), payload)
  assert.equal(resolveResponsePath(payload, 'result.items.total'), 42)
  assert.equal(resolveResponsePath(payload, ' result . items . total '), 42)
  assert.equal(resolveResponsePath(payload, 'result.missing.total'), undefined)
  assert.equal(resolveResponsePath(10, 'result.any'), undefined)
})
