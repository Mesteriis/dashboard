export interface ParsedSvgIcon {
  svgBody: string;
  svgViewBox: string;
}

function splitSlug(slug: string): string[] {
  return slug
    .split(/[^a-z0-9]+/i)
    .map((chunk) => chunk.trim())
    .filter(Boolean);
}

export function slugFromSvgFilePath(filePath: string): string {
  const fileName = filePath.split("/").pop() || "";
  return fileName.replace(/\.svg$/i, "").trim();
}

export function labelFromSlug(slug: string): string {
  return splitSlug(slug)
    .map((chunk) => chunk.charAt(0).toUpperCase() + chunk.slice(1))
    .join(" ");
}

export function keywordsFromSlug(
  slug: string,
  extras: string[] = [],
): string[] {
  return Array.from(
    new Set(
      [...splitSlug(slug), ...extras.map((item) => item.trim())].filter(
        Boolean,
      ),
    ),
  );
}

export function parseSvgMarkup(svgMarkup: string): ParsedSvgIcon {
  const normalizedMarkup = String(svgMarkup || "").trim();
  const viewBoxMatch = normalizedMarkup.match(/viewBox="([^"]+)"/i);
  const bodyMatch = normalizedMarkup.match(/<svg[^>]*>([\s\S]*?)<\/svg>/i);

  return {
    svgViewBox: viewBoxMatch?.[1] || "0 0 24 24",
    svgBody: (bodyMatch?.[1] || "").trim(),
  };
}
