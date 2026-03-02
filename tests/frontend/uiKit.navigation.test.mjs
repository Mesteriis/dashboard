import assert from 'node:assert/strict'
import test from 'node:test'
import {
  __setUiKitBaseUrlForTests,
  isUiKitPath,
  resolveUiKitPath,
  resolveUiKitPathFromBase,
} from '../../frontend/src/features/services/uiKitNavigation.ts'

test('isUiKitPath detects ui-kit leaf route', () => {
  assert.equal(isUiKitPath('/'), false)
  assert.equal(isUiKitPath(''), false)
  assert.equal(isUiKitPath('/ui-kit'), true)
  assert.equal(isUiKitPath('/ui-kit/'), true)
  assert.equal(isUiKitPath('ui-kit'), true)
  assert.equal(isUiKitPath('/dashboard/ui-kit'), true)
  assert.equal(isUiKitPath('/dashboard/ui-kit/'), true)
  assert.equal(isUiKitPath('/dashboard/ui-kit/section'), false)
  assert.equal(isUiKitPath('/dashboard/uikit'), false)
  assert.equal(isUiKitPath('///'), false)
})

test('resolveUiKitPathFromBase normalizes base url variants', () => {
  assert.equal(resolveUiKitPathFromBase('/'), '/ui-kit')
  assert.equal(resolveUiKitPathFromBase(''), '/ui-kit')
  assert.equal(resolveUiKitPathFromBase('   '), '/ui-kit')
  assert.equal(resolveUiKitPathFromBase('/dashboard'), '/dashboard/ui-kit')
  assert.equal(resolveUiKitPathFromBase('/dashboard/'), '/dashboard/ui-kit')
  assert.equal(resolveUiKitPathFromBase('dashboard'), '/dashboard/ui-kit')
  assert.equal(resolveUiKitPathFromBase('dashboard/'), '/dashboard/ui-kit')
})

test('resolveUiKitPath falls back to root when BASE_URL is unavailable', () => {
  __setUiKitBaseUrlForTests(null)
  assert.equal(resolveUiKitPath(), '/ui-kit')
  __setUiKitBaseUrlForTests(undefined)
  assert.equal(resolveUiKitPath(), '/ui-kit')
})

test('resolveUiKitPath uses configured BASE_URL when available', () => {
  __setUiKitBaseUrlForTests('/console/')
  assert.equal(resolveUiKitPath(), '/console/ui-kit')
  __setUiKitBaseUrlForTests(undefined)
})
