import {
  requestJson,
  resolveMergedCapabilities,
} from "@/features/services/requestJson";

export const FRONTEND_SUPPORTED_MANIFEST_MAJOR = 1;
export const FRONTEND_SUPPORTED_PLUGIN_API_MAJOR = 1;

export type PluginLayoutType =
  | "content-only"
  | "with-sidebar"
  | "dashboard"
  | "split-view";

export interface PluginDataSourceHttpV1 {
  type: "http";
  endpoint: string;
  method: "GET" | "POST";
  capability?: string;
  response_path?: string;
  body?: Record<string, unknown>;
}

export interface PluginRowActionAddToDashboardV1 {
  id: string;
  type: "add-to-dashboard";
  label: string;
  capability?: string;
  targetGroupId: string;
  targetGroupTitle: string;
  targetPageId?: string;
  subgroupField: string;
  urlField: string;
  titleField?: string;
  titleTemplate?: string;
  tagsFromFields: string[];
  openMode: "new_tab" | "same_tab";
}

export interface PluginTableColumnV1 {
  key: string;
  label: string;
}

export interface PluginTableGroupByLevelV1 {
  field: string;
  label: string;
  emptyLabel: string;
}

export interface PluginTextComponentV1 {
  id: string;
  type: "text";
  title?: string;
  text: string;
}

export interface PluginDataTableComponentV1 {
  id: string;
  type: "data-table";
  title?: string;
  columns: PluginTableColumnV1[];
  groupBy: PluginTableGroupByLevelV1[];
  dataSource: PluginDataSourceHttpV1;
  rowActions: PluginRowActionAddToDashboardV1[];
  loadingText?: string;
  emptyText?: string;
  errorText?: string;
}

export interface PluginUnknownComponentV1 {
  id: string;
  type: "unknown";
  originalType: string;
  title?: string;
}

export type PluginPageComponentV1 =
  | PluginTextComponentV1
  | PluginDataTableComponentV1
  | PluginUnknownComponentV1;

export interface PluginFrontendCustomBundleV1 {
  enabled: boolean;
  entry?: string;
  integrity?: string;
  sandbox: boolean;
  killSwitchKey: string;
}

export interface PluginFrontendV1 {
  renderer: "universal" | "custom";
  sandbox: boolean;
  customBundle: PluginFrontendCustomBundleV1;
}

export interface PluginPageV1 {
  enabled: boolean;
  layout: PluginLayoutType;
  components: PluginPageComponentV1[];
}

export interface PluginPageManifestV1 {
  plugin_id: string;
  version: string;
  manifest_version: string;
  plugin_api_version: string;
  capabilities: string[];
  frontend: PluginFrontendV1;
  page: PluginPageV1;
  schema: Record<string, unknown>;
}

export interface PluginManifestNegotiation {
  accepted: boolean;
  fallback_used: boolean;
  reason?: string;
  errors?: string[];
  supported_manifest_major?: number;
  supported_plugin_api_major?: number;
}

export interface PluginManifestEnvelope {
  plugin_id: string;
  manifest: PluginPageManifestV1;
  negotiation: PluginManifestNegotiation;
}

export class PluginManifestNotFoundError extends Error {
  readonly pluginId: string;

  constructor(pluginId: string) {
    super(`Plugin manifest not found for '${pluginId}'`);
    this.name = "PluginManifestNotFoundError";
    this.pluginId = pluginId;
  }
}

export class PluginManifestParseError extends Error {
  readonly pluginId: string;

  constructor(pluginId: string, cause: unknown) {
    super(`Plugin manifest parse error for '${pluginId}'`);
    this.name = "PluginManifestParseError";
    this.pluginId = pluginId;
    if (cause instanceof Error) this.cause = cause;
  }
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function asString(value: unknown): string {
  return String(value || "").trim();
}

function asBool(value: unknown, fallback = false): boolean {
  if (typeof value === "boolean") return value;
  return fallback;
}

function parseMajor(version: string): number {
  const token = asString(version);
  if (!token) return 0;
  const chunk = token.split(".", 1)[0];
  const parsed = Number(chunk);
  if (!Number.isFinite(parsed) || parsed <= 0) return 0;
  return Math.floor(parsed);
}

function parseDataSource(raw: unknown): PluginDataSourceHttpV1 {
  const record = asRecord(raw);
  if (!record) {
    throw new Error("Component dataSource must be an object");
  }
  const type = asString(record.type || "http").toLowerCase();
  if (type !== "http") {
    throw new Error(`Unsupported dataSource type: ${type}`);
  }
  const endpoint = asString(record.endpoint);
  if (!endpoint.startsWith("/api/v1/")) {
    throw new Error("dataSource.endpoint must start with /api/v1/");
  }
  const methodToken = asString(record.method || "GET").toUpperCase();
  const method: "GET" | "POST" = methodToken === "POST" ? "POST" : "GET";
  const capability = asString(record.capability);
  const responsePath = asString(record.response_path || record.responsePath);
  const body = asRecord(record.body) || undefined;

  return {
    type: "http",
    endpoint,
    method,
    ...(capability ? { capability } : {}),
    ...(responsePath ? { response_path: responsePath } : {}),
    ...(body ? { body } : {}),
  };
}

function parseGroupBy(raw: unknown): PluginTableGroupByLevelV1[] {
  if (!Array.isArray(raw)) return [];
  const levels: PluginTableGroupByLevelV1[] = [];
  for (const entry of raw) {
    let field = "";
    let label = "";
    let emptyLabel = "Unknown";

    if (typeof entry === "string") {
      field = asString(entry);
      label = field;
    } else {
      const record = asRecord(entry);
      if (!record) continue;
      field = asString(record.field || record.key);
      label = asString(record.label) || field;
      emptyLabel = asString(record.emptyLabel || record.empty_label) || "Unknown";
    }

    if (!field) continue;
    levels.push({
      field,
      label: label || field,
      emptyLabel,
    });
  }
  return levels;
}

function parseRowActions(raw: unknown): PluginRowActionAddToDashboardV1[] {
  if (!Array.isArray(raw)) return [];
  const actions: PluginRowActionAddToDashboardV1[] = [];

  for (const entry of raw) {
    const record = asRecord(entry);
    if (!record) continue;
    const id = asString(record.id);
    const type = asString(record.type).toLowerCase();
    if (!id || type !== "add-to-dashboard") continue;

    const capability = asString(record.capability);
    const targetGroupId = asString(record.targetGroupId) || "autodiscover";
    const targetGroupTitle = asString(record.targetGroupTitle) || "Autodiscover";
    const targetPageId = asString(record.targetPageId);
    const subgroupField = asString(record.subgroupField) || "host_ip";
    const urlField = asString(record.urlField) || "url";
    const titleField = asString(record.titleField);
    const titleTemplate = asString(record.titleTemplate);
    const tagsFromFields = Array.isArray(record.tagsFromFields)
      ? record.tagsFromFields
          .map((value) => asString(value))
          .filter(Boolean)
      : ["host_ip", "service", "port"];
    const openModeToken = asString(record.openMode).toLowerCase();
    const openMode: "new_tab" | "same_tab" =
      openModeToken === "same_tab" ? "same_tab" : "new_tab";

    actions.push({
      id,
      type: "add-to-dashboard",
      label: asString(record.label) || "Add to Dashboard",
      ...(capability ? { capability } : {}),
      targetGroupId,
      targetGroupTitle,
      ...(targetPageId ? { targetPageId } : {}),
      subgroupField,
      urlField,
      ...(titleField ? { titleField } : {}),
      ...(titleTemplate ? { titleTemplate } : {}),
      tagsFromFields: tagsFromFields.length
        ? tagsFromFields
        : ["host_ip", "service", "port"],
      openMode,
    });
  }

  return actions;
}

function parseComponents(raw: unknown): PluginPageComponentV1[] {
  if (!Array.isArray(raw)) return [];
  const components: PluginPageComponentV1[] = [];
  for (const entry of raw) {
    const record = asRecord(entry);
    if (!record) continue;
    const id = asString(record.id);
    const type = asString(record.type).toLowerCase();
    const title = asString(record.title);
    if (!id || !type) continue;

    if (type === "text") {
      const text = asString(record.text);
      if (!text) continue;
      components.push({
        id,
        type: "text",
        ...(title ? { title } : {}),
        text,
      });
      continue;
    }

    if (type === "data-table") {
      const columnsRaw = Array.isArray(record.columns) ? record.columns : [];
      const columns: PluginTableColumnV1[] = [];
      for (const col of columnsRaw) {
        const colRecord = asRecord(col);
        if (!colRecord) continue;
        const key = asString(colRecord.key);
        const label = asString(colRecord.label);
        if (!key || !label) continue;
        columns.push({ key, label });
      }
      const dataSource = parseDataSource(record.dataSource);
      components.push({
        id,
        type: "data-table",
        ...(title ? { title } : {}),
        columns,
        groupBy: parseGroupBy(record.groupBy || record.group_by),
        dataSource,
        rowActions: parseRowActions(record.rowActions),
        ...(asString(record.loadingText)
          ? { loadingText: asString(record.loadingText) }
          : {}),
        ...(asString(record.emptyText) ? { emptyText: asString(record.emptyText) } : {}),
        ...(asString(record.errorText) ? { errorText: asString(record.errorText) } : {}),
      });
      continue;
    }

    components.push({
      id,
      type: "unknown",
      originalType: type,
      ...(title ? { title } : {}),
    });
  }
  return components;
}

function parseManifest(raw: unknown, pluginId: string): PluginPageManifestV1 {
  const root = asRecord(raw);
  if (!root) throw new Error("Manifest must be an object");

  const manifestVersion = asString(root.manifest_version);
  const pluginApiVersion = asString(root.plugin_api_version);
  if (parseMajor(manifestVersion) !== FRONTEND_SUPPORTED_MANIFEST_MAJOR) {
    throw new Error(`Unsupported manifest_version: ${manifestVersion || "unknown"}`);
  }
  if (parseMajor(pluginApiVersion) > FRONTEND_SUPPORTED_PLUGIN_API_MAJOR) {
    throw new Error(`Unsupported plugin_api_version: ${pluginApiVersion || "unknown"}`);
  }

  const manifestPluginId = asString(root.plugin_id);
  if (!manifestPluginId || manifestPluginId !== pluginId) {
    throw new Error("plugin_id mismatch");
  }

  const rawFrontend = asRecord(root.frontend);
  const rendererToken = asString(rawFrontend?.renderer).toLowerCase();
  const renderer: "universal" | "custom" =
    rendererToken === "custom" ? "custom" : "universal";
  const rawCustom = asRecord(rawFrontend?.customBundle || rawFrontend?.custom_bundle);

  const rawPage = asRecord(root.page);
  const layoutToken = asString(rawPage?.layout).toLowerCase();
  const layout: PluginLayoutType =
    layoutToken === "with-sidebar" ||
    layoutToken === "dashboard" ||
    layoutToken === "split-view"
      ? (layoutToken as PluginLayoutType)
      : "content-only";

  return {
    plugin_id: manifestPluginId,
    version: asString(root.version) || "0.0.0",
    manifest_version: manifestVersion,
    plugin_api_version: pluginApiVersion,
    capabilities: Array.isArray(root.capabilities)
      ? root.capabilities.map((entry) => asString(entry)).filter(Boolean)
      : [],
    frontend: {
      renderer,
      sandbox: asBool(rawFrontend?.sandbox, true),
      customBundle: {
        enabled: asBool(rawCustom?.enabled, false),
        ...(asString(rawCustom?.entry) ? { entry: asString(rawCustom?.entry) } : {}),
        ...(asString(rawCustom?.integrity)
          ? { integrity: asString(rawCustom?.integrity) }
          : {}),
        sandbox: asBool(rawCustom?.sandbox, true),
        killSwitchKey: asString(rawCustom?.killSwitchKey) || "oko:plugins:bundle:disabled",
      },
    },
    page: {
      enabled: asBool(rawPage?.enabled, false),
      layout,
      components: parseComponents(rawPage?.components),
    },
    schema: asRecord(root.schema) || {},
  };
}

function parseNegotiation(raw: unknown): PluginManifestNegotiation {
  const record = asRecord(raw) || {};
  return {
    accepted: asBool(record.accepted, false),
    fallback_used: asBool(record.fallback_used, false),
    ...(asString(record.reason) ? { reason: asString(record.reason) } : {}),
    ...(Array.isArray(record.errors)
      ? { errors: record.errors.map((entry) => asString(entry)).filter(Boolean) }
      : {}),
    ...(Number.isFinite(Number(record.supported_manifest_major))
      ? { supported_manifest_major: Number(record.supported_manifest_major) }
      : {}),
    ...(Number.isFinite(Number(record.supported_plugin_api_major))
      ? { supported_plugin_api_major: Number(record.supported_plugin_api_major) }
      : {}),
  };
}

function normalizeEnvelope(raw: unknown, pluginId: string): PluginManifestEnvelope {
  const root = asRecord(raw);
  if (!root) throw new Error("Invalid manifest envelope");
  return {
    plugin_id: asString(root.plugin_id) || pluginId,
    manifest: parseManifest(root.manifest, pluginId),
    negotiation: parseNegotiation(root.negotiation),
  };
}

export function getCurrentActorCapabilities(): Set<string> {
  return new Set(resolveMergedCapabilities());
}

export function getMissingManifestCapabilities(
  manifest: PluginPageManifestV1,
  actorCapabilities = getCurrentActorCapabilities(),
): string[] {
  const required = new Set<string>();
  for (const component of manifest.page.components) {
    if (component.type !== "data-table") continue;
    const capability = asString(component.dataSource.capability);
    if (capability) required.add(capability);
    const rowActions = Array.isArray(component.rowActions)
      ? component.rowActions
      : [];
    for (const action of rowActions) {
      const actionCapability = asString(action.capability);
      if (actionCapability) required.add(actionCapability);
    }
  }
  return Array.from(required).filter((capability) => !actorCapabilities.has(capability));
}

export async function loadPluginManifest(
  pluginId: string,
): Promise<PluginManifestEnvelope> {
  const normalizedPluginId = asString(pluginId);
  if (!normalizedPluginId) {
    throw new PluginManifestNotFoundError(pluginId);
  }

  let response: unknown;
  try {
    response = await requestJson(
      `/api/v1/plugins/${encodeURIComponent(normalizedPluginId)}/manifest`,
    );
  } catch (error: unknown) {
    const status = Number(
      (error as { status?: number } | undefined)?.status || 0,
    );
    if (status === 404) {
      throw new PluginManifestNotFoundError(normalizedPluginId);
    }
    throw error;
  }

  try {
    return normalizeEnvelope(response, normalizedPluginId);
  } catch (error: unknown) {
    throw new PluginManifestParseError(normalizedPluginId, error);
  }
}

export function resolveResponsePath(payload: unknown, path: string | undefined): unknown {
  const normalizedPath = asString(path);
  if (!normalizedPath) return payload;
  const chunks = normalizedPath.split(".").map((entry) => entry.trim()).filter(Boolean);
  let current: unknown = payload;
  for (const chunk of chunks) {
    const currentRecord = asRecord(current);
    if (!currentRecord) return undefined;
    current = currentRecord[chunk];
  }
  return current;
}
