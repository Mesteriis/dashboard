import { parse as parseYaml } from "yaml";

export type PluginRendererType = "built_in" | "remote";

export interface PluginManifestRenderer {
  type: PluginRendererType;
  component?: string;
}

export interface PluginManifestCard {
  title: string;
  text?: string;
}

export interface PluginManifestLink {
  label: string;
  url: string;
  description?: string;
  open?: "_self" | "_blank";
}

export interface PluginManifestCardsSection {
  kind: "cards";
  title?: string;
  cards: PluginManifestCard[];
}

export interface PluginManifestLinksSection {
  kind: "links";
  title?: string;
  items: PluginManifestLink[];
}

export interface PluginManifestIframeSection {
  kind: "iframe";
  title?: string;
  src: string;
  height?: number;
  sandbox?: string;
}

export interface PluginManifestSettingsSection {
  kind: "settings";
  title?: string;
  schema: Record<string, unknown>;
}

export type PluginManifestSection =
  | PluginManifestCardsSection
  | PluginManifestLinksSection
  | PluginManifestIframeSection
  | PluginManifestSettingsSection;

export interface PluginManifest {
  id: string;
  title: string;
  version?: string;
  icon?: string;
  description?: string;
  renderer: PluginManifestRenderer;
  sections: PluginManifestSection[];
}

export class PluginManifestNotFoundError extends Error {
  readonly pluginId: string;
  readonly candidates: string[];

  constructor(pluginId: string, candidates: string[]) {
    super(`Plugin manifest not found for '${pluginId}'`);
    this.name = "PluginManifestNotFoundError";
    this.pluginId = pluginId;
    this.candidates = candidates;
  }
}

export class PluginManifestParseError extends Error {
  readonly pluginId: string;
  readonly sourcePath: string;

  constructor(pluginId: string, sourcePath: string, cause: unknown) {
    super(`Plugin manifest parse error for '${pluginId}' at '${sourcePath}'`);
    this.name = "PluginManifestParseError";
    this.pluginId = pluginId;
    this.sourcePath = sourcePath;
    if (cause instanceof Error) {
      this.cause = cause;
    }
  }
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function asNonEmptyString(value: unknown): string {
  return String(value || "").trim();
}

function asOptionalString(value: unknown): string | undefined {
  const normalized = asNonEmptyString(value);
  return normalized ? normalized : undefined;
}

function asPositiveNumber(value: unknown): number | undefined {
  const normalized = Number(value);
  if (!Number.isFinite(normalized) || normalized <= 0) return undefined;
  return normalized;
}

function parseRenderer(rawValue: unknown): PluginManifestRenderer {
  const raw = asRecord(rawValue);
  if (!raw) {
    return { type: "built_in" };
  }

  const rawType = asNonEmptyString(raw.type).toLowerCase();
  const type: PluginRendererType = rawType === "remote" ? "remote" : "built_in";
  const component = asOptionalString(raw.component);

  return {
    type,
    component,
  };
}

function parseCardsSection(
  rawSection: Record<string, unknown>,
): PluginManifestCardsSection {
  const rawCards = Array.isArray(rawSection.cards) ? rawSection.cards : [];
  const cards: PluginManifestCard[] = [];

  for (const entry of rawCards) {
    const rawCard = asRecord(entry);
    if (!rawCard) continue;
    const title = asNonEmptyString(rawCard.title);
    if (!title) continue;
    const text = asOptionalString(rawCard.text || rawCard.body);
    cards.push({
      title,
      ...(text ? { text } : {}),
    });
  }

  return {
    kind: "cards",
    title: asOptionalString(rawSection.title),
    cards,
  };
}

function parseLinksSection(
  rawSection: Record<string, unknown>,
): PluginManifestLinksSection {
  const rawItems = Array.isArray(rawSection.items)
    ? rawSection.items
    : Array.isArray(rawSection.links)
      ? rawSection.links
      : [];

  const items: PluginManifestLink[] = [];

  for (const entry of rawItems) {
    const rawLink = asRecord(entry);
    if (!rawLink) continue;
    const label = asNonEmptyString(rawLink.label || rawLink.title);
    const url = asNonEmptyString(rawLink.url || rawLink.href);
    if (!label || !url) continue;
    const open = asNonEmptyString(rawLink.open).toLowerCase();
    const description = asOptionalString(rawLink.description);
    items.push({
      label,
      url,
      ...(description ? { description } : {}),
      open: open === "_self" ? "_self" : "_blank",
    });
  }

  return {
    kind: "links",
    title: asOptionalString(rawSection.title),
    items,
  };
}

function parseIframeSection(
  rawSection: Record<string, unknown>,
): PluginManifestIframeSection | null {
  const src = asNonEmptyString(rawSection.src || rawSection.url);
  if (!src) return null;

  return {
    kind: "iframe",
    title: asOptionalString(rawSection.title),
    src,
    height: asPositiveNumber(rawSection.height),
    sandbox: asOptionalString(rawSection.sandbox),
  };
}

function parseSettingsSection(
  rawSection: Record<string, unknown>,
): PluginManifestSettingsSection {
  const rawSchema = asRecord(rawSection.schema);
  return {
    kind: "settings",
    title: asOptionalString(rawSection.title),
    schema: rawSchema || {},
  };
}

function parseSections(rawValue: unknown): PluginManifestSection[] {
  if (!Array.isArray(rawValue)) return [];

  const sections: PluginManifestSection[] = [];

  for (const entry of rawValue) {
    const rawSection = asRecord(entry);
    if (!rawSection) continue;

    const kind = asNonEmptyString(rawSection.kind).toLowerCase();
    if (kind === "cards") {
      sections.push(parseCardsSection(rawSection));
      continue;
    }
    if (kind === "links") {
      sections.push(parseLinksSection(rawSection));
      continue;
    }
    if (kind === "iframe") {
      const section = parseIframeSection(rawSection);
      if (section) sections.push(section);
      continue;
    }
    if (kind === "settings") {
      sections.push(parseSettingsSection(rawSection));
    }
  }

  return sections;
}

function normalizeManifest(
  pluginId: string,
  rawValue: unknown,
): PluginManifest {
  const raw = asRecord(rawValue);
  if (!raw) {
    throw new Error("Manifest root must be a YAML mapping");
  }

  const id = asNonEmptyString(raw.id) || pluginId;
  const title = asNonEmptyString(raw.title) || asNonEmptyString(raw.name) || id;

  return {
    id,
    title,
    version: asOptionalString(raw.version),
    icon: asOptionalString(raw.icon),
    description: asOptionalString(raw.description),
    renderer: parseRenderer(raw.renderer),
    sections: parseSections(raw.sections),
  };
}

function ensureTrailingSlash(raw: string): string {
  const normalized = String(raw || "/").trim();
  if (!normalized) return "/";
  return normalized.endsWith("/") ? normalized : `${normalized}/`;
}

function resolveManifestCandidates(pluginId: string): string[] {
  const normalizedPluginId = encodeURIComponent(pluginId);
  const fileCandidates = [
    "plugin.yaml",
    "manifest.yaml",
    "plugin.yml",
    "manifest.yml",
  ];

  const roots = new Set<string>();
  const baseRoot = ensureTrailingSlash(import.meta.env.BASE_URL || "/");
  roots.add(baseRoot);
  roots.add("/static/");
  roots.add("/");

  const paths: string[] = [];
  for (const root of roots) {
    for (const filename of fileCandidates) {
      paths.push(`${root}plugins/${normalizedPluginId}/${filename}`);
    }
  }

  return Array.from(new Set(paths));
}

async function fetchManifestSource(path: string): Promise<string | null> {
  const response = await fetch(path, {
    headers: {
      Accept: "application/x-yaml, text/yaml, text/plain",
    },
  });

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error(`Failed to fetch manifest (${response.status})`);
  }

  return await response.text();
}

export async function loadPluginManifest(
  pluginId: string,
): Promise<PluginManifest> {
  const normalizedPluginId = asNonEmptyString(pluginId);
  if (!normalizedPluginId) {
    throw new PluginManifestNotFoundError(pluginId, []);
  }

  const candidates = resolveManifestCandidates(normalizedPluginId);

  for (const path of candidates) {
    const source = await fetchManifestSource(path);
    if (source === null) continue;

    try {
      const parsed = parseYaml(source);
      return normalizeManifest(normalizedPluginId, parsed);
    } catch (error: unknown) {
      throw new PluginManifestParseError(normalizedPluginId, path, error);
    }
  }

  throw new PluginManifestNotFoundError(normalizedPluginId, candidates);
}
