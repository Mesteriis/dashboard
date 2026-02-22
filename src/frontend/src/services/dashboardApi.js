import { requestJson, resolveRequestUrl } from './requestJson.js'

const DASHBOARD_API_BASE = '/api/v1/dashboard'

export { requestJson }

/**
 * @returns {Promise<unknown>}
 */
export function fetchDashboardConfig() {
  return requestJson(`${DASHBOARD_API_BASE}/config`)
}

/**
 * @param {string} itemId
 * @returns {Promise<unknown>}
 */
export function fetchIframeSource(itemId) {
  return requestJson(`${DASHBOARD_API_BASE}/iframe/${encodeURIComponent(itemId)}/source`, { requireAdminToken: true }).then(
    (payload) => {
      if (!payload || typeof payload !== 'object') return payload
      const sourcePayload = /** @type {{ src?: unknown }} */ (payload)
      if (typeof sourcePayload.src !== 'string') return payload
      return {
        ...payload,
        src: resolveRequestUrl(sourcePayload.src),
      }
    }
  )
}

/**
 * @param {string[]} [itemIds]
 * @returns {Promise<unknown>}
 */
export function fetchDashboardHealth(itemIds = []) {
  const params = new URLSearchParams()
  for (const id of itemIds) {
    params.append('item_id', id)
  }
  const query = params.toString()
  return requestJson(`${DASHBOARD_API_BASE}/health${query ? `?${query}` : ''}`)
}

/**
 * @param {unknown} config
 * @returns {Promise<unknown>}
 */
export function updateDashboardConfig(config) {
  return requestJson(`${DASHBOARD_API_BASE}/config`, {
    requireAdminToken: true,
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(config),
  })
}

/**
 * @returns {Promise<unknown>}
 */
export function fetchLanScanState() {
  return requestJson(`${DASHBOARD_API_BASE}/lan/state`)
}

/**
 * @returns {Promise<unknown>}
 */
export function triggerLanScan() {
  return requestJson(`${DASHBOARD_API_BASE}/lan/run`, {
    requireAdminToken: true,
    method: 'POST',
  })
}
