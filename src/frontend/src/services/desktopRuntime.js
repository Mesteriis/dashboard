const DEFAULT_REMOTE_BASE_URL = 'http://127.0.0.1:8090'

/**
 * @typedef {'web' | 'embedded' | 'remote'} RuntimeMode
 */

/**
 * @typedef {object} RuntimeProfile
 * @property {boolean} desktop
 * @property {RuntimeMode} mode
 * @property {string} apiBaseUrl
 * @property {string} remoteBaseUrl
 * @property {boolean} embeddedRunning
 */

/** @type {RuntimeProfile} */
let runtimeProfile = {
  desktop: false,
  mode: 'web',
  apiBaseUrl: '',
  remoteBaseUrl: DEFAULT_REMOTE_BASE_URL,
  embeddedRunning: false,
}

/** @type {Promise<RuntimeProfile> | null} */
let bridgeReadyPromise = null
/** @type {((command: string, args?: Record<string, unknown>) => Promise<unknown>) | null} */
let invokeBridge = null

function isDesktopShell() {
  return typeof window !== 'undefined' && Boolean(window.__TAURI_INTERNALS__)
}

/**
 * @param {unknown} rawValue
 * @returns {string}
 */
function normalizeBaseUrl(rawValue) {
  const value = String(rawValue || '').trim()
  if (!value) return ''
  return value.endsWith('/') ? value.slice(0, -1) : value
}

/**
 * @param {unknown} nextProfile
 * @returns {RuntimeProfile}
 */
function applyRuntimeProfile(nextProfile) {
  const payload = /** @type {Partial<RuntimeProfile> | null | undefined} */ (nextProfile)
  const normalized = {
    desktop: Boolean(payload?.desktop),
    mode: /** @type {RuntimeMode} */ (String(payload?.mode || 'web')),
    apiBaseUrl: normalizeBaseUrl(payload?.apiBaseUrl),
    remoteBaseUrl: normalizeBaseUrl(payload?.remoteBaseUrl) || DEFAULT_REMOTE_BASE_URL,
    embeddedRunning: Boolean(payload?.embeddedRunning),
  }

  runtimeProfile = normalized

  if (typeof window !== 'undefined') {
    window.__OKO_API_BASE__ = normalized.apiBaseUrl || ''
    window.__OKO_DESKTOP_RUNTIME__ = normalized
    window.dispatchEvent(new CustomEvent('oko:api-base-change', { detail: { apiBaseUrl: normalized.apiBaseUrl } }))
  }

  return normalized
}

/**
 * @param {unknown} actionId
 */
function emitDesktopAction(actionId) {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new CustomEvent('oko:desktop-action', { detail: { action: String(actionId || '') } }))
}

async function loadDesktopBridge() {
  const [coreApi, eventApi] = await Promise.all([
    import('@tauri-apps/api/core'),
    import('@tauri-apps/api/event'),
  ])

  invokeBridge = coreApi.invoke

  const profile = await invokeBridge('desktop_get_runtime_profile')
  applyRuntimeProfile(profile)

  await eventApi.listen('desktop://runtime-profile', (event) => {
    applyRuntimeProfile(event.payload)
  })

  await eventApi.listen('desktop://action', (event) => {
    emitDesktopAction(event.payload)
  })

  return runtimeProfile
}

/**
 * @returns {RuntimeProfile}
 */
export function getRuntimeProfile() {
  return { ...runtimeProfile }
}

/**
 * @returns {Promise<RuntimeProfile>}
 */
export async function initDesktopRuntimeBridge() {
  if (!isDesktopShell()) {
    applyRuntimeProfile({
      desktop: false,
      mode: 'web',
      apiBaseUrl: '',
      remoteBaseUrl: DEFAULT_REMOTE_BASE_URL,
      embeddedRunning: false,
    })
    return runtimeProfile
  }

  if (!bridgeReadyPromise) {
    bridgeReadyPromise = loadDesktopBridge().catch((error) => {
      bridgeReadyPromise = null
      // Keep UI operational in browser mode if desktop bridge fails to initialize.
      void error
      applyRuntimeProfile({
        desktop: true,
        mode: 'remote',
        apiBaseUrl: DEFAULT_REMOTE_BASE_URL,
        remoteBaseUrl: DEFAULT_REMOTE_BASE_URL,
        embeddedRunning: false,
      })
      return runtimeProfile
    })
  }

  return bridgeReadyPromise
}

/**
 * @param {{ mode?: RuntimeMode; remoteBaseUrl?: string }} nextProfile
 * @returns {Promise<RuntimeProfile>}
 */
export async function setDesktopRuntimeProfile(nextProfile) {
  if (!invokeBridge) {
    const initialized = await initDesktopRuntimeBridge()
    if (!initialized.desktop || !invokeBridge) {
      throw new Error('Desktop runtime bridge is not available')
    }
  }

  const payload = {
    mode: String(nextProfile?.mode || runtimeProfile.mode),
    remote_base_url: normalizeBaseUrl(nextProfile?.remoteBaseUrl || runtimeProfile.remoteBaseUrl || DEFAULT_REMOTE_BASE_URL),
  }

  const updated = await invokeBridge('desktop_set_runtime_profile', payload)
  return applyRuntimeProfile(updated)
}

export { DEFAULT_REMOTE_BASE_URL, isDesktopShell }
