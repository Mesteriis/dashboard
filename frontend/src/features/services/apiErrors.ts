import { EVENT_API_ERROR, emitOkoEvent } from "@/features/services/events";

export type ApiErrorKind = "network" | "http" | "parse" | "unknown";

export interface ApiRequestError extends Error {
  name: "ApiRequestError";
  status: number;
  body: unknown;
  kind: ApiErrorKind;
  url: string;
  method: string;
  source: string;
  timestamp: string;
  isApiError: true;
  cause?: unknown;
}

export interface ApiRequestErrorInit {
  message: string;
  status?: number;
  body?: unknown;
  kind?: ApiErrorKind;
  url?: string;
  method?: string;
  source?: string;
  cause?: unknown;
}

export function isApiRequestError(error: unknown): error is ApiRequestError {
  return Boolean(
    error &&
      typeof error === "object" &&
      "isApiError" in error &&
      (error as { isApiError?: unknown }).isApiError === true,
  );
}

export function createApiRequestError(init: ApiRequestErrorInit): ApiRequestError {
  const error = new Error(String(init.message || "API request failed"));
  const typedError = error as ApiRequestError;
  typedError.name = "ApiRequestError";
  typedError.status = Number.isFinite(init.status) ? Number(init.status) : 0;
  typedError.body = init.body ?? null;
  typedError.kind = init.kind || "unknown";
  typedError.url = String(init.url || "");
  typedError.method = String(init.method || "GET").toUpperCase();
  typedError.source = String(init.source || "requestJson");
  typedError.timestamp = new Date().toISOString();
  typedError.isApiError = true;
  if (init.cause !== undefined) {
    typedError.cause = init.cause;
  }
  return typedError;
}

export function emitApiRequestError(error: ApiRequestError): void {
  emitOkoEvent(EVENT_API_ERROR, {
    message: error.message,
    status: error.status,
    kind: error.kind,
    method: error.method,
    url: error.url,
    source: error.source,
    timestamp: error.timestamp,
  });
}

export function createAndEmitApiRequestError(
  init: ApiRequestErrorInit,
): ApiRequestError {
  const error = createApiRequestError(init);
  emitApiRequestError(error);
  return error;
}
