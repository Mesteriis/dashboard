import assert from 'node:assert/strict'
import test from 'node:test'
import { SHOWCASE_NODE_API } from '../../frontend/src/views/ui-showcase/showcaseNodeApi.ts'
import { UI_KIT_SHOWCASE_GROUPS } from '../../frontend/src/views/ui-showcase/sections/showcaseRegistry.ts'

function ensureUnique(values, label) {
  const unique = new Set(values)
  assert.equal(unique.size, values.length, `${label} must be unique`)
}

test('ui-kit registry has stable groups and flattened items', () => {
  assert.equal(UI_KIT_SHOWCASE_GROUPS.length > 0, true)
  ensureUnique(
    UI_KIT_SHOWCASE_GROUPS.map((group) => group.id),
    'group ids',
  )

  for (const group of UI_KIT_SHOWCASE_GROUPS) {
    assert.equal(typeof group.id, 'string')
    assert.equal(typeof group.label, 'string')
    assert.equal(typeof group.description, 'string')
    assert.equal(Array.isArray(group.sections), true)
    assert.equal(Array.isArray(group.items), true)

    const flattened = group.sections.flatMap((section) => section.items)
    assert.deepEqual(group.items, flattened, `group.items must be derived from sections for ${group.id}`)

    ensureUnique(
      group.sections.map((section) => section.id),
      `section ids for group ${group.id}`,
    )
    ensureUnique(
      group.items.map((item) => item.id),
      `item ids for group ${group.id}`,
    )
  }
})

test('ui-kit registry and node api remain in sync', () => {
  const itemIds = UI_KIT_SHOWCASE_GROUPS.flatMap((group) => group.items.map((item) => item.id))
  const apiIds = Object.keys(SHOWCASE_NODE_API)
  ensureUnique(itemIds, 'all ui-kit node ids')
  ensureUnique(apiIds, 'all showcase api ids')
  assert.deepEqual(new Set(apiIds), new Set(itemIds))

  for (const [nodeId, api] of Object.entries(SHOWCASE_NODE_API)) {
    assert.equal(typeof nodeId, 'string')
    assert.equal(Array.isArray(api.props), true)
    assert.equal(Array.isArray(api.slots), true)
    assert.equal(Array.isArray(api.signals), true)
    assert.equal(Array.isArray(api.model), true)
  }
})
