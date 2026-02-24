function trimTrailingSlash(pathname: string): string {
  return pathname.replace(/\/+$/, "");
}

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

export function resolveUiKitPath(): string {
  const basePath = normalizeBasePath(import.meta.env.BASE_URL || "/");
  return basePath ? `${basePath}/ui-kit` : "/ui-kit";
}
