import assert from 'node:assert/strict'
import test from 'node:test'
import {
  EVENT_API_ERROR,
  EVENT_OPEN_PLEIAD,
  emitOkoEvent,
  offOkoEvent,
  onOkoEvent,
} from '../../frontend/src/features/services/events.ts'

const hadWindow = 'window' in globalThis
const originalWindow = globalThis.window

function createMockWindow() {
  const listeners = new Map()
  return {
    listeners,
    addEventListener(type, listener) {
      if (!listeners.has(type)) listeners.set(type, new Set())
      listeners.get(type).add(listener)
    },
    removeEventListener(type, listener) {
      listeners.get(type)?.delete(listener)
    },
    dispatchEvent(event) {
      const items = Array.from(listeners.get(event.type) || [])
      for (const listener of items) {
        listener(event)
      }
      return true
    },
  }
}

test.afterEach(() => {
  if (hadWindow) {
    globalThis.window = originalWindow
  } else {
    delete globalThis.window
  }
})

test('emitOkoEvent returns false when window is not available', () => {
  delete globalThis.window
  assert.equal(emitOkoEvent(EVENT_OPEN_PLEIAD, { mode: 'default' }), false)
})

test('onOkoEvent returns noop disposer without window', () => {
  delete globalThis.window
  const dispose = onOkoEvent(EVENT_OPEN_PLEIAD, () => {})
  assert.equal(typeof dispose, 'function')
  dispose()
})

test('offOkoEvent does nothing without window', () => {
  delete globalThis.window
  offOkoEvent(EVENT_OPEN_PLEIAD, () => {})
})

test('emitOkoEvent dispatches CustomEvent with provided payload', () => {
  const mockWindow = createMockWindow()
  globalThis.window = mockWindow
  const received = []
  onOkoEvent(EVENT_OPEN_PLEIAD, (event) => {
    received.push(event.detail.mode)
  })

  const emitted = emitOkoEvent(EVENT_OPEN_PLEIAD, { mode: 'overlay' })
  assert.equal(emitted, true)
  assert.deepEqual(received, ['overlay'])
})

test('emitOkoEvent uses empty object when detail is undefined', () => {
  const mockWindow = createMockWindow()
  globalThis.window = mockWindow
  let detail = null
  onOkoEvent(EVENT_API_ERROR, (event) => {
    detail = event.detail
  })

  emitOkoEvent(EVENT_API_ERROR)
  assert.deepEqual(detail, {})
})

test('onOkoEvent disposer unsubscribes listener', () => {
  const mockWindow = createMockWindow()
  globalThis.window = mockWindow
  let count = 0
  const dispose = onOkoEvent(EVENT_OPEN_PLEIAD, () => {
    count += 1
  })

  emitOkoEvent(EVENT_OPEN_PLEIAD, { mode: 'x' })
  dispose()
  emitOkoEvent(EVENT_OPEN_PLEIAD, { mode: 'x' })
  assert.equal(count, 1)
})

test('offOkoEvent removes specific listener', () => {
  const mockWindow = createMockWindow()
  globalThis.window = mockWindow
  let first = 0
  let second = 0
  const listenerA = () => {
    first += 1
  }
  const listenerB = () => {
    second += 1
  }
  onOkoEvent(EVENT_OPEN_PLEIAD, listenerA)
  onOkoEvent(EVENT_OPEN_PLEIAD, listenerB)

  offOkoEvent(EVENT_OPEN_PLEIAD, listenerA)
  emitOkoEvent(EVENT_OPEN_PLEIAD, { mode: 'x' })
  assert.equal(first, 0)
  assert.equal(second, 1)
})

test('onOkoEvent passes options through add/remove calls', () => {
  const calls = []
  const listeners = new Set()
  globalThis.window = {
    addEventListener(type, listener, options) {
      calls.push({ phase: 'add', type, options })
      listeners.add(listener)
    },
    removeEventListener(type, listener, options) {
      calls.push({ phase: 'remove', type, options })
      listeners.delete(listener)
    },
    dispatchEvent(event) {
      for (const listener of listeners) listener(event)
      return true
    },
  }

  const options = { once: true, passive: true }
  const dispose = onOkoEvent(EVENT_OPEN_PLEIAD, () => {}, options)
  dispose()
  assert.equal(calls.length, 2)
  assert.deepEqual(calls[0], { phase: 'add', type: EVENT_OPEN_PLEIAD, options })
  assert.deepEqual(calls[1], { phase: 'remove', type: EVENT_OPEN_PLEIAD, options })
})
