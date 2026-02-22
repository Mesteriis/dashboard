/** @typedef {RequestInit} RequestJsonOptions */

/**
 * @param {string} path
 * @returns {string}
 */
export function resolveRequestUrl(path) {
  const inputPath = String(path || "");
  if (!inputPath) return inputPath;

  if (/^https?:\/\//i.test(inputPath)) {
    return inputPath;
  }

  const runtimeBase =
    typeof window === "undefined"
      ? ""
      : String(window.__OKO_API_BASE__ || "").trim();
  if (!runtimeBase) return inputPath;

  const normalizedBase = runtimeBase.endsWith("/")
    ? runtimeBase.slice(0, -1)
    : runtimeBase;
  const normalizedPath = inputPath.startsWith("/")
    ? inputPath
    : `/${inputPath}`;
  return `${normalizedBase}${normalizedPath}`;
}

/**
 * @param {unknown} body
 * @param {boolean} isJson
 * @param {number} status
 * @returns {string}
 */
function resolveErrorMessage(body, isJson, status) {
  const detail =
    isJson && typeof body === "object" && body !== null
      ? /** @type {{ detail?: unknown }} */ (body).detail
      : null;
  let message = `Request failed: ${status}`;
  if (status === 500 || status === 502 || status === 503 || status === 504) {
    message =
      "Не удалось связаться с backend. Проверьте, что сервер запущен и порт настроен корректно.";
  }

  if (Array.isArray(detail)) {
    message = detail
      .map((item) =>
        typeof item === "object" && item !== null && "message" in item
          ? String(/** @type {{ message?: unknown }} */ (item).message || "")
          : JSON.stringify(item),
      )
      .join("; ");
  } else if (typeof detail === "string" && detail) {
    message = detail;
  } else if (typeof body === "string" && body) {
    message = body;
  }

  return message;
}

/**
 * @param {string} path
 * @param {RequestJsonOptions} [options]
 * @returns {Promise<unknown>}
 */
export async function requestJson(path, options = {}) {
  const { headers: customHeaders = {}, ...fetchOptions } = options;
  /** @type {Record<string, string>} */
  const customHeadersObject = {};
  if (customHeaders instanceof Headers) {
    customHeaders.forEach((value, key) => {
      customHeadersObject[key] = value;
    });
  } else if (Array.isArray(customHeaders)) {
    for (const [key, value] of customHeaders) {
      customHeadersObject[key] = String(value);
    }
  } else {
    Object.assign(customHeadersObject, customHeaders);
  }
  /** @type {Record<string, string>} */
  const headers = {
    Accept: "application/json",
    ...customHeadersObject,
  };

  let response;
  try {
    response = await fetch(resolveRequestUrl(path), {
      credentials: "include",
      headers,
      ...fetchOptions,
    });
  } catch (cause) {
    const error = new Error(
      "Не удалось подключиться к backend. Проверьте, что сервер запущен и порт совпадает.",
    );
    const typedError =
      /** @type {Error & { status: number; body: unknown; cause?: unknown }} */ (
        error
      );
    typedError.status = 0;
    typedError.body = null;
    typedError.cause = cause;
    throw typedError;
  }

  const contentType = response.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");
  const body = isJson ? await response.json() : await response.text();

  if (!response.ok) {
    const error = new Error(resolveErrorMessage(body, isJson, response.status));
    const typedError =
      /** @type {Error & { status: number; body: unknown }} */ (error);
    typedError.status = response.status;
    typedError.body = body;
    throw typedError;
  }

  return body;
}
