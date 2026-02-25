import { createAndEmitApiRequestError } from "@/features/services/apiErrors";
import { requestJson } from "@/features/services/requestJson";

const CORE_API_BASE = "/api/v1";

export interface DashboardConfigBackup {
  yaml: string;
  filename: string;
}

export interface DashboardValidationIssue {
  type: string;
  message: string;
  location?: {
    line?: number;
    column?: number;
  };
}

export interface DashboardValidationResult {
  valid: boolean;
  issues: DashboardValidationIssue[];
}

export { requestJson };

function extractConfigPayload(
  response: unknown,
): Record<string, unknown> | null {
  if (!response || typeof response !== "object") return null;
  const record = response as Record<string, unknown>;

  const directConfig = record.config;
  if (directConfig && typeof directConfig === "object") {
    return directConfig as Record<string, unknown>;
  }

  const revision = record.revision;
  if (revision && typeof revision === "object") {
    const payload = (revision as Record<string, unknown>).payload;
    if (payload && typeof payload === "object") {
      return payload as Record<string, unknown>;
    }
  }

  return null;
}

function stringifyYamlLike(payload: unknown): string {
  return `${JSON.stringify(payload, null, 2)}\n`;
}

export function fetchDashboardConfig(): Promise<unknown> {
  return requestJson(`${CORE_API_BASE}/config`);
}

export async function fetchDashboardConfigBackup(): Promise<DashboardConfigBackup> {
  const config = await fetchDashboardConfig();
  const fallbackName = `dashboard-backup-${new Date().toISOString().slice(0, 19).replaceAll(":", "-")}.yaml`;
  return {
    yaml: stringifyYamlLike(config),
    filename: fallbackName,
  };
}

export async function updateDashboardConfig(
  config: unknown,
): Promise<{ config: Record<string, unknown> }> {
  const response = await requestJson(`${CORE_API_BASE}/config/patch`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ patch: config, source: "patch" }),
  });

  const payload = extractConfigPayload(response);
  if (payload) {
    return { config: payload };
  }

  const fallback =
    config && typeof config === "object"
      ? (config as Record<string, unknown>)
      : {};
  return { config: fallback };
}

export async function validateDashboardYaml(
  yamlContent: string,
): Promise<DashboardValidationResult> {
  const response = (await requestJson(`${CORE_API_BASE}/config/validate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ format: "yaml", payload: yamlContent }),
  })) as {
    valid?: unknown;
    issues?: unknown;
  };

  return {
    valid: Boolean(response?.valid),
    issues: Array.isArray(response?.issues)
      ? (response.issues as DashboardValidationIssue[])
      : [],
  };
}

export async function restoreDashboardConfig(
  yamlContent: string,
): Promise<DashboardConfigBackup> {
  await requestJson(`${CORE_API_BASE}/config/import`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ format: "yaml", payload: yamlContent, source: "import" }),
  });

  return {
    yaml: yamlContent,
    filename: "dashboard-restored.yaml",
  };
}

export function validateActionEnvelope(payload: unknown): Promise<unknown> {
  return requestJson(`${CORE_API_BASE}/actions/validate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export function executeActionEnvelope(payload: unknown): Promise<unknown> {
  return requestJson(`${CORE_API_BASE}/actions/execute`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export async function unsupportedFeature(message: string): Promise<never> {
  throw createAndEmitApiRequestError({
    message,
    status: 410,
    body: null,
    kind: "http",
    method: "GET",
    url: CORE_API_BASE,
    source: "dashboardApi",
  });
}
