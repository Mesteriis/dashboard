export const PLEIAD_OPEN_EVENT = "oko:open-pleiad";
export const PLEIAD_PRIMARY_AGENT_EVENT = "oko:pleiad-primary-agent";

/**
 * @param {string} pathname
 * @returns {string}
 */
function trimTrailingSlash(pathname) {
  return pathname.replace(/\/+$/, "");
}

/**
 * @param {string} rawBase
 * @returns {string}
 */
function normalizeBasePath(rawBase) {
  const raw = String(rawBase || "/").trim();
  if (!raw || raw === "/") return "";
  const withLeadingSlash = raw.startsWith("/") ? raw : `/${raw}`;
  return trimTrailingSlash(withLeadingSlash);
}

/**
 * @param {string} pathname
 * @returns {string}
 */
export function normalizePathname(pathname) {
  const raw = String(pathname || "/").trim();
  if (!raw || raw === "/") return "/";
  const withLeadingSlash = raw.startsWith("/") ? raw : `/${raw}`;
  const trimmed = trimTrailingSlash(withLeadingSlash);
  return trimmed || "/";
}

/**
 * @param {string} pathname
 * @returns {boolean}
 */
export function isPleiadPath(pathname) {
  const normalized = normalizePathname(pathname);
  const segments = normalized.split("/").filter(Boolean);
  if (!segments.length) return false;
  return segments[segments.length - 1] === "pleiad";
}

export function resolveShellPath() {
  const basePath = normalizeBasePath(import.meta.env.BASE_URL || "/");
  return basePath || "/";
}

export function resolvePleiadPath() {
  const basePath = normalizeBasePath(import.meta.env.BASE_URL || "/");
  return basePath ? `${basePath}/pleiad` : "/pleiad";
}

/**
 * @param {Record<string, unknown>} [detail]
 * @returns {void}
 */
export function dispatchOpenPleiad(detail = {}) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent(PLEIAD_OPEN_EVENT, {
      detail,
    }),
  );
}

/**
 * @param {string} agentId
 * @param {Record<string, unknown>} [detail]
 * @returns {void}
 */
export function dispatchPleiadPrimaryAgent(agentId, detail = {}) {
  if (typeof window === "undefined") return;
  const normalizedAgentId = String(agentId || "")
    .trim()
    .toUpperCase();
  if (!normalizedAgentId) return;
  window.dispatchEvent(
    new CustomEvent(PLEIAD_PRIMARY_AGENT_EVENT, {
      detail: {
        ...detail,
        agentId: normalizedAgentId,
      },
    }),
  );
}
