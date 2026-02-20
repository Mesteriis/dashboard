const DASHBOARD_API_BASE = '/api/v1/dashboard'

export async function requestJson(path, options = {}) {
  const response = await fetch(path, {
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  })

  const contentType = response.headers.get('content-type') || ''
  const isJson = contentType.includes('application/json')
  const body = isJson ? await response.json() : await response.text()

  if (!response.ok) {
    const detail = isJson ? body?.detail : null
    let message = `Request failed: ${response.status}`

    if (Array.isArray(detail)) {
      message = detail.map((item) => item?.message || JSON.stringify(item)).join('; ')
    } else if (typeof detail === 'string' && detail) {
      message = detail
    } else if (typeof body === 'string' && body) {
      message = body
    }

    const error = new Error(message)
    error.status = response.status
    error.body = body
    throw error
  }

  return body
}

export function fetchDashboardConfig() {
  return requestJson(`${DASHBOARD_API_BASE}/config`)
}

export function fetchIframeSource(itemId) {
  return requestJson(`${DASHBOARD_API_BASE}/iframe/${encodeURIComponent(itemId)}/source`)
}

export function fetchDashboardHealth(itemIds = []) {
  const params = new URLSearchParams()
  for (const id of itemIds) {
    params.append('item_id', id)
  }
  const query = params.toString()
  return requestJson(`${DASHBOARD_API_BASE}/health${query ? `?${query}` : ''}`)
}
