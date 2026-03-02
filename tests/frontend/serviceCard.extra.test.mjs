import assert from 'node:assert/strict'
import test from 'node:test'
import {
  normalizePluginBlocks,
  normalizeServiceCardCore,
} from '../../frontend/src/shared/contracts/serviceCard.ts'

test('normalizeServiceCardCore keeps defaults for non-object payload', () => {
  const normalized = normalizeServiceCardCore(null)
  assert.deepEqual(normalized, {
    id: 'service',
    title: 'service',
    url: '',
    check_url: '',
    tags: [],
    open: 'new_tab',
    type: 'link',
    plugin_blocks: [],
  })
})

test('normalizeServiceCardCore normalizes unknown type and open', () => {
  const normalized = normalizeServiceCardCore({
    id: 'svc',
    type: 'desktop',
    open: 'popup',
  })
  assert.equal(normalized.type, 'link')
  assert.equal(normalized.open, 'new_tab')
})

test('normalizeServiceCardCore trims and filters tags', () => {
  const normalized = normalizeServiceCardCore({
    id: 'svc',
    tags: ['  alpha ', '', 'beta', 1],
  })
  assert.deepEqual(normalized.tags, ['alpha', 'beta', '1'])
})

test('normalizePluginBlocks returns empty for invalid top-level input', () => {
  assert.deepEqual(normalizePluginBlocks(undefined), [])
  assert.deepEqual(normalizePluginBlocks({}), [])
  assert.deepEqual(normalizePluginBlocks('x'), [])
})

test('normalizePluginBlocks skips blocks without supported elements', () => {
  const blocks = normalizePluginBlocks([
    { plugin_id: 'a', elements: [] },
    { plugin_id: 'b', elements: [{ id: 'x', kind: 'custom' }] },
  ])
  assert.deepEqual(blocks, [])
})

test('normalizePluginBlocks applies default ids and plugin ids', () => {
  const blocks = normalizePluginBlocks([
    {
      elements: [{ kind: 'text', value: 'ok' }],
    },
  ])
  assert.equal(blocks.length, 1)
  assert.equal(blocks[0].plugin_id, 'plugin-0')
  assert.equal(blocks[0].elements[0].id, 'el-0')
})

test('normalizePluginBlocks normalizes text and badge elements', () => {
  const blocks = normalizePluginBlocks([
    {
      plugin_id: 'metrics',
      elements: [
        { id: 't1', kind: 'text', label: ' latency ', value: ' 42ms ' },
        { id: 'b1', kind: 'badge', value: 'degraded', tone: 'warning' },
        { id: 'b2', kind: 'badge', value: 'raw' },
      ],
    },
  ])
  assert.deepEqual(blocks[0].elements, [
    { id: 't1', kind: 'text', label: 'latency', value: '42ms' },
    { id: 'b1', kind: 'badge', value: 'degraded', tone: 'warning' },
    { id: 'b2', kind: 'badge', value: 'raw', tone: undefined },
  ])
})

test('normalizePluginBlocks normalizes link element defaults', () => {
  const blocks = normalizePluginBlocks([
    {
      plugin_id: 'links',
      elements: [
        { id: 'l1', kind: 'link', url: 'https://example.local' },
        { id: 'l2', kind: 'link', label: 'Open now', url: '/local', open: 'same_tab' },
      ],
    },
  ])
  assert.deepEqual(blocks[0].elements, [
    {
      id: 'l1',
      kind: 'link',
      label: 'Open',
      url: 'https://example.local',
      open: 'new_tab',
    },
    {
      id: 'l2',
      kind: 'link',
      label: 'Open now',
      url: '/local',
      open: 'same_tab',
    },
  ])
})

test('normalizePluginBlocks normalizes html trust and html payload', () => {
  const blocks = normalizePluginBlocks([
    {
      plugin_id: 'html',
      elements: [
        { id: 'h1', kind: 'html', trust: 'server_sanitized_v1', html: '<p>x</p>' },
        { id: 'h2', kind: 'html', trust: 'none', html: 42 },
      ],
    },
  ])
  assert.deepEqual(blocks[0].elements, [
    { id: 'h1', kind: 'html', trust: 'server_sanitized_v1', html: '<p>x</p>' },
    { id: 'h2', kind: 'html', trust: 'untrusted', html: '42' },
  ])
})

test('normalizeServiceCardCore keeps normalized plugin blocks', () => {
  const normalized = normalizeServiceCardCore({
    id: 'svc',
    plugin_blocks: [
      {
        plugin_id: 'metrics',
        title: ' Metrics ',
        elements: [{ kind: 'text', value: 'up' }],
      },
    ],
  })
  assert.equal(normalized.plugin_blocks.length, 1)
  assert.equal(normalized.plugin_blocks[0].plugin_id, 'metrics')
  assert.equal(normalized.plugin_blocks[0].title, 'Metrics')
  assert.equal(normalized.plugin_blocks[0].version, 'v1')
})
