export type ServiceCardTypeV1 = "link" | "iframe";
export type ServiceCardOpenV1 = "new_tab" | "same_tab";

export type ServicePluginElementKindV1 = "text" | "badge" | "link" | "html";

export interface ServicePluginTextElementV1 {
  id: string;
  kind: "text";
  label?: string;
  value: string;
}

export interface ServicePluginBadgeElementV1 {
  id: string;
  kind: "badge";
  value: string;
  tone?: "neutral" | "info" | "success" | "warning" | "danger";
}

export interface ServicePluginLinkElementV1 {
  id: string;
  kind: "link";
  label: string;
  url: string;
  open?: ServiceCardOpenV1;
}

export interface ServicePluginHtmlElementV1 {
  id: string;
  kind: "html";
  trust: "server_sanitized_v1" | "untrusted";
  html: string;
}

export type ServicePluginElementV1 =
  | ServicePluginTextElementV1
  | ServicePluginBadgeElementV1
  | ServicePluginLinkElementV1
  | ServicePluginHtmlElementV1;

export interface ServiceCardPluginBlockV1 {
  plugin_id: string;
  title?: string;
  version: "v1";
  elements: ServicePluginElementV1[];
}

export interface ServiceCardCoreV1 {
  id: string;
  title: string;
  url: string;
  check_url: string;
  tags: string[];
  open: ServiceCardOpenV1;
  type: ServiceCardTypeV1;
  plugin_blocks: ServiceCardPluginBlockV1[];
  [key: string]: unknown;
}

function asString(value: unknown): string {
  return String(value ?? "").trim();
}

function normalizeTags(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((entry) => asString(entry))
    .filter(Boolean);
}

function normalizeOpen(value: unknown): ServiceCardOpenV1 {
  return asString(value) === "same_tab" ? "same_tab" : "new_tab";
}

function normalizeType(value: unknown): ServiceCardTypeV1 {
  return asString(value).toLowerCase() === "iframe" ? "iframe" : "link";
}

function normalizePluginElement(
  value: unknown,
  fallbackIndex: number,
): ServicePluginElementV1 | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const raw = value as Record<string, unknown>;
  const kind = asString(raw.kind).toLowerCase() as ServicePluginElementKindV1;
  const id = asString(raw.id) || `el-${fallbackIndex}`;

  if (kind === "text") {
    return {
      id,
      kind: "text",
      label: asString(raw.label) || undefined,
      value: asString(raw.value),
    };
  }

  if (kind === "badge") {
    const tone = asString(raw.tone).toLowerCase();
    return {
      id,
      kind: "badge",
      value: asString(raw.value),
      tone: tone
        ? (tone as "neutral" | "info" | "success" | "warning" | "danger")
        : undefined,
    };
  }

  if (kind === "link") {
    return {
      id,
      kind: "link",
      label: asString(raw.label) || "Open",
      url: asString(raw.url),
      open: normalizeOpen(raw.open),
    };
  }

  if (kind === "html") {
    return {
      id,
      kind: "html",
      trust:
        asString(raw.trust) === "server_sanitized_v1"
          ? "server_sanitized_v1"
          : "untrusted",
      html: String(raw.html ?? ""),
    };
  }

  return null;
}

export function normalizePluginBlocks(
  value: unknown,
): ServiceCardPluginBlockV1[] {
  if (!Array.isArray(value)) return [];

  const blocks: ServiceCardPluginBlockV1[] = [];

  value.forEach((entry, blockIndex) => {
    if (!entry || typeof entry !== "object" || Array.isArray(entry)) return;
    const raw = entry as Record<string, unknown>;
    const elementsRaw = Array.isArray(raw.elements) ? raw.elements : [];
    const elements = elementsRaw
      .map((element, elementIndex) =>
        normalizePluginElement(element, elementIndex),
      )
      .filter((element): element is ServicePluginElementV1 => Boolean(element));

    if (!elements.length) return;

    blocks.push({
      plugin_id: asString(raw.plugin_id) || `plugin-${blockIndex}`,
      title: asString(raw.title) || undefined,
      version: "v1",
      elements,
    });
  });

  return blocks;
}

export function normalizeServiceCardCore(
  value: unknown,
): ServiceCardCoreV1 {
  const raw =
    value && typeof value === "object" && !Array.isArray(value)
      ? (value as Record<string, unknown>)
      : {};

  const id = asString(raw.id) || "service";
  const title = asString(raw.title) || id;
  const url = asString(raw.url);
  const healthcheck =
    raw.healthcheck && typeof raw.healthcheck === "object"
      ? (raw.healthcheck as Record<string, unknown>)
      : null;
  const checkUrl = asString(raw.check_url) || asString(healthcheck?.url) || url;

  return {
    id,
    title,
    url,
    check_url: checkUrl,
    tags: normalizeTags(raw.tags),
    open: normalizeOpen(raw.open),
    type: normalizeType(raw.type),
    plugin_blocks: normalizePluginBlocks(raw.plugin_blocks),
  };
}
