const ADMIN_TOKEN_HEADER = 'X-Dashboard-Token'
const DESKTOP_EMBEDDED_ADMIN_TOKEN = 'oko-desktop-embedded'

/**
 * @typedef {RequestInit & {
 *   requireAdminToken?: boolean
 * }} RequestJsonOptions
 */

function getAdminToken() {
  if (typeof window === 'undefined') return ''
  let fromStorage = ''
  try {
    fromStorage = window.localStorage?.getItem('dashboard_admin_token') || ''
  } catch {
    fromStorage = ''
  }
  if (String(fromStorage).trim()) {
    return String(fromStorage).trim()
  }
  const runtimeProfile = window.__OKO_DESKTOP_RUNTIME__
  if (runtimeProfile?.desktop && runtimeProfile?.mode === 'embedded') {
    return DESKTOP_EMBEDDED_ADMIN_TOKEN
  }
  const fromGlobal = window.__DASHBOARD_ADMIN_TOKEN__ || ''
  return String(fromGlobal).trim()
}

/**
 * @param {string} path
 * @returns {string}
 */
export function resolveRequestUrl(path) {
  const inputPath = String(path || '')
  if (!inputPath) return inputPath

  if (/^https?:\/\//i.test(inputPath)) {
    return inputPath
  }

  const runtimeBase = typeof window === 'undefined' ? '' : String(window.__OKO_API_BASE__ || '').trim()
  if (!runtimeBase) return inputPath

  const normalizedBase = runtimeBase.endsWith('/') ? runtimeBase.slice(0, -1) : runtimeBase
  const normalizedPath = inputPath.startsWith('/') ? inputPath : `/${inputPath}`
  return `${normalizedBase}${normalizedPath}`
}

/**
 * @param {unknown} body
 * @param {boolean} isJson
 * @param {number} status
 * @returns {string}
 */
function resolveErrorMessage(body, isJson, status) {
  const detail = isJson && typeof body === 'object' && body !== null ? /** @type {{ detail?: unknown }} */ (body).detail : null
  let message = `Request failed: ${status}`

  if (Array.isArray(detail)) {
    message = detail
      .map((item) => (typeof item === 'object' && item !== null && 'message' in item
        ? String(/** @type {{ message?: unknown }} */ (item).message || '')
        : JSON.stringify(item)))
      .join('; ')
  } else if (typeof detail === 'string' && detail) {
    message = detail
  } else if (typeof body === 'string' && body) {
    message = body
  }

  return message
}

/**
 * @param {string} path
 * @param {RequestJsonOptions} [options]
 * @returns {Promise<unknown>}
 */
export async function requestJson(path, options = {}) {
  const { requireAdminToken = false, headers: customHeaders = {}, ...fetchOptions } = options
  /** @type {Record<string, string>} */
  const customHeadersObject = {}
  if (customHeaders instanceof Headers) {
    customHeaders.forEach((value, key) => {
      customHeadersObject[key] = value
    })
  } else if (Array.isArray(customHeaders)) {
    for (const [key, value] of customHeaders) {
      customHeadersObject[key] = String(value)
    }
  } else {
    Object.assign(customHeadersObject, customHeaders)
  }
  /** @type {Record<string, string>} */
  const headers = {
    Accept: 'application/json',
    ...customHeadersObject,
  }

  if (requireAdminToken) {
    const adminToken = getAdminToken()
    if (adminToken) {
      headers[ADMIN_TOKEN_HEADER] = adminToken
    }
  }

  const response = await fetch(resolveRequestUrl(path), {
    credentials: 'include',
    headers,
    ...fetchOptions,
  })

  const contentType = response.headers.get('content-type') || ''
  const isJson = contentType.includes('application/json')
  const body = isJson ? await response.json() : await response.text()

  if (!response.ok) {
    const error = new Error(resolveErrorMessage(body, isJson, response.status))
    const typedError = /** @type {Error & { status: number; body: unknown }} */ (error)
    typedError.status = response.status
    typedError.body = body
    throw typedError
  }

  return body
}
