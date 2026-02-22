import { requestJson, resolveRequestUrl } from "./requestJson.js";

const DASHBOARD_API_BASE = "/api/v1/dashboard";

export { requestJson };

/**
 * @returns {Promise<unknown>}
 */
export function fetchDashboardConfig() {
  return requestJson(`${DASHBOARD_API_BASE}/config`);
}

/**
 * @returns {Promise<{ yaml: string; filename: string }>}
 */
export async function fetchDashboardConfigBackup() {
  const response = await fetch(
    resolveRequestUrl(`${DASHBOARD_API_BASE}/config/backup`),
    {
      credentials: "include",
      headers: {
        Accept: "application/x-yaml, text/yaml, text/plain, */*",
      },
    },
  );

  const body = await response.text();
  if (!response.ok) {
    throw new Error(body || `Request failed: ${response.status}`);
  }

  const disposition = String(response.headers.get("content-disposition") || "");
  const filenameMatch = disposition.match(/filename="?([^";]+)"?/i);
  const fallbackName = `dashboard-backup-${new Date().toISOString().slice(0, 19).replaceAll(":", "-")}.yaml`;

  return {
    yaml: body,
    filename: filenameMatch?.[1] || fallbackName,
  };
}

/**
 * @param {string} itemId
 * @returns {Promise<unknown>}
 */
export function fetchIframeSource(itemId) {
  return requestJson(
    `${DASHBOARD_API_BASE}/iframe/${encodeURIComponent(itemId)}/source`,
  ).then((payload) => {
    if (!payload || typeof payload !== "object") return payload;
    const sourcePayload = /** @type {{ src?: unknown }} */ (payload);
    if (typeof sourcePayload.src !== "string") return payload;
    return {
      ...payload,
      src: resolveRequestUrl(sourcePayload.src),
    };
  });
}

/**
 * @param {string[]} [itemIds]
 * @returns {Promise<unknown>}
 */
export function fetchDashboardHealth(itemIds = []) {
  const params = new URLSearchParams();
  for (const id of itemIds) {
    params.append("item_id", id);
  }
  const query = params.toString();
  return requestJson(`${DASHBOARD_API_BASE}/health${query ? `?${query}` : ""}`);
}

/**
 * @param {string[]} [itemIds]
 * @returns {EventSource | null}
 */
export function createDashboardHealthStream(itemIds = []) {
  if (typeof EventSource === "undefined") return null;

  const params = new URLSearchParams();
  for (const id of itemIds) {
    params.append("item_id", id);
  }
  const query = params.toString();
  const streamUrl = `${DASHBOARD_API_BASE}/health/stream${query ? `?${query}` : ""}`;
  return new EventSource(resolveRequestUrl(streamUrl), {
    withCredentials: true,
  });
}

/**
 * @param {unknown} config
 * @returns {Promise<unknown>}
 */
export function updateDashboardConfig(config) {
  return requestJson(`${DASHBOARD_API_BASE}/config`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(config),
  });
}

/**
 * @param {string} yamlContent
 * @returns {Promise<{ valid: boolean; issues: Array<{ type: string; message: string; location?: { line?: number; column?: number } }> }>}
 */
export function validateDashboardYaml(yamlContent) {
  return /** @type {Promise<{ valid: boolean; issues: Array<{ type: string; message: string; location?: { line?: number; column?: number } }> }>} */ (
    requestJson(`${DASHBOARD_API_BASE}/validate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ yaml: yamlContent }),
    })
  );
}

/**
 * @param {string} yamlContent
 * @returns {Promise<{ yaml: string; filename: string }>}
 */
export async function restoreDashboardConfig(yamlContent) {
  return /** @type {Promise<{ yaml: string; filename: string }>} */ (
    requestJson(`${DASHBOARD_API_BASE}/config/restore`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ yaml: yamlContent }),
    })
  );
}

/**
 * @returns {Promise<unknown>}
 */
export function fetchLanScanState() {
  return requestJson(`${DASHBOARD_API_BASE}/lan/state`);
}

/**
 * @returns {EventSource | null}
 */
export function createLanScanStream() {
  if (typeof EventSource === "undefined") return null;
  const streamUrl = `${DASHBOARD_API_BASE}/lan/stream`;
  return new EventSource(resolveRequestUrl(streamUrl), {
    withCredentials: true,
  });
}

/**
 * @returns {Promise<unknown>}
 */
export function triggerLanScan() {
  return requestJson(`${DASHBOARD_API_BASE}/lan/run`, {
    method: "POST",
  });
}
