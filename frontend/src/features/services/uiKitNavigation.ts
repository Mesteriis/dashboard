function trimTrailingSlash(pathname: string): string {
  return pathname.replace(/\/+$/, "");
}

type RuntimeImportMeta = ImportMeta & {
  env?: {
    BASE_URL?: string;
  };
};

const runtimeImportMeta = import.meta as RuntimeImportMeta;

function normalizeBasePath(rawBase: string): string {
  const raw = String(rawBase || "/").trim();
  if (!raw || raw === "/") return "";
  const withLeadingSlash = raw.startsWith("/") ? raw : `/${raw}`;
  return trimTrailingSlash(withLeadingSlash);
}

export function isUiKitPath(pathname: string): boolean {
  const raw = String(pathname || "/").trim();
  if (!raw || raw === "/") return false;
  const withLeadingSlash = raw.startsWith("/") ? raw : `/${raw}`;
  const normalized = trimTrailingSlash(withLeadingSlash) || "/";
  const segments = normalized.split("/").filter(Boolean);
  if (!segments.length) return false;
  return segments[segments.length - 1] === "ui-kit";
}

export function resolveUiKitPathFromBase(rawBase: string): string {
  const basePath = normalizeBasePath(rawBase || "/");
  return basePath ? `${basePath}/ui-kit` : "/ui-kit";
}

export function resolveUiKitPath(): string {
  return resolveUiKitPathFromBase(runtimeImportMeta.env?.BASE_URL || "/");
}

export function __setUiKitBaseUrlForTests(baseUrl: string | undefined | null): void {
  if (baseUrl === null) {
    runtimeImportMeta.env = undefined;
    return;
  }
  runtimeImportMeta.env = {
    ...(runtimeImportMeta.env || {}),
    BASE_URL: baseUrl,
  };
}
