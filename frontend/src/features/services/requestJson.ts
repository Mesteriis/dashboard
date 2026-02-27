import { createAndEmitApiRequestError } from "@/features/services/apiErrors";

export type RequestJsonOptions = RequestInit & {
  headers?: HeadersInit;
};

const DEFAULT_ACTOR = "frontend-local";
const DEFAULT_CAPABILITIES = [
  "read.state",
  "read.config",
  "read.config.revisions",
  "read.events",
  "read.registry.widgets",
  "read.registry.actions",
  "exec.actions.validate",
  "exec.actions.execute",
  "read.actions.history",
  "write.config.import",
  "write.config.patch",
  "write.config.rollback",
  "exec.system.echo",
  "exec.system.ping",
];

export function resolveRequestUrl(path: string): string {
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

function resolveActor(): string {
  if (typeof window === "undefined") return DEFAULT_ACTOR;
  const value = String(window.__OKO_ACTOR__ || "").trim();
  return value || DEFAULT_ACTOR;
}

function resolveCapabilities(): string {
  if (typeof window === "undefined") return DEFAULT_CAPABILITIES.join(",");

  const configured = Array.isArray(window.__OKO_CAPABILITIES__)
    ? window.__OKO_CAPABILITIES__
    : [];
  const normalized = configured
    .map((entry) => String(entry || "").trim())
    .filter(Boolean);

  if (!normalized.length) {
    return DEFAULT_CAPABILITIES.join(",");
  }
  return normalized.join(",");
}

export function buildOkoRequestHeaders(
  extra: Record<string, string> = {},
): Record<string, string> {
  return {
    "X-Oko-Actor": resolveActor(),
    "X-Oko-Capabilities": resolveCapabilities(),
    ...extra,
  };
}

function resolveErrorMessage(
  body: unknown,
  isJson: boolean,
  status: number,
): string {
  const payload =
    isJson && typeof body === "object" && body !== null
      ? (body as { detail?: unknown; message?: unknown; code?: unknown })
      : null;

  let message = `Request failed: ${status}`;
  if (status >= 500) {
    message =
      "Не удалось связаться с backend. Проверьте, что сервер запущен и порт настроен корректно.";
  }

  if (
    payload &&
    typeof payload.message === "string" &&
    payload.message.trim()
  ) {
    return payload.message;
  }

  const detail = payload?.detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) =>
        typeof item === "object" && item !== null && "message" in item
          ? String((item as { message?: unknown }).message || "")
          : JSON.stringify(item),
      )
      .join("; ");
  }

  if (typeof detail === "string" && detail) {
    return detail;
  }
  if (typeof body === "string" && body) {
    return body;
  }

  return message;
}

export async function requestJson(
  path: string,
  options: RequestJsonOptions = {},
): Promise<unknown> {
  const { headers: customHeaders = {}, ...fetchOptions } = options;
  const requestUrl = resolveRequestUrl(path);
  const method = String(fetchOptions.method || "GET").toUpperCase();
  const customHeadersObject: Record<string, string> = {};

  if (customHeaders instanceof Headers) {
    customHeaders.forEach((value, key) => {
      customHeadersObject[key] = value;
    });
  } else if (Array.isArray(customHeaders)) {
    for (const [key, value] of customHeaders) {
      customHeadersObject[key] = String(value);
    }
  } else {
    for (const [key, value] of Object.entries(customHeaders)) {
      customHeadersObject[key] = String(value);
    }
  }

  const headers: Record<string, string> = {
    Accept: "application/json",
    ...buildOkoRequestHeaders(),
    ...customHeadersObject,
  };

  let response: Response;
  try {
    response = await fetch(requestUrl, {
      credentials: "include",
      headers,
      ...fetchOptions,
    });
  } catch (cause) {
    throw createAndEmitApiRequestError({
      message:
        "Не удалось подключиться к backend. Проверьте, что сервер запущен и порт совпадает.",
      status: 0,
      body: null,
      kind: "network",
      url: requestUrl,
      method,
      source: "requestJson",
      cause,
    });
  }

  const contentType = response.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");
  let body: unknown;
  try {
    body = isJson ? await response.json() : await response.text();
  } catch (cause) {
    throw createAndEmitApiRequestError({
      message: "Не удалось прочитать ответ backend.",
      status: response.status,
      body: null,
      kind: "parse",
      url: requestUrl,
      method,
      source: "requestJson",
      cause,
    });
  }

  if (!response.ok) {
    throw createAndEmitApiRequestError({
      message: resolveErrorMessage(body, isJson, response.status),
      status: response.status,
      body,
      kind: "http",
      url: requestUrl,
      method,
      source: "requestJson",
    });
  }

  return body;
}
