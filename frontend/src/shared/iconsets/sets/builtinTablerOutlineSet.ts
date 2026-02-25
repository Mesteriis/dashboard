import type { BuiltinIconPickerSet } from "@/shared/iconsets/simpleIconsUtils";
import {
  keywordsFromSlug,
  labelFromSlug,
  parseSvgMarkup,
  slugFromSvgFilePath,
} from "@/shared/iconsets/tablerSvgUtils";

const OUTLINE_SVG_MODULES = import.meta.glob<string>(
  "/node_modules/@tabler/icons/icons/outline/*.svg",
  {
    query: "?raw",
    import: "default",
    eager: true,
  },
);

const TABLER_OUTLINE_OPTIONS = Object.entries(OUTLINE_SVG_MODULES)
  .map(([filePath, svgMarkup]) => {
    const slug = slugFromSvgFilePath(filePath);
    if (!slug) return null;

    const parsedSvg = parseSvgMarkup(svgMarkup);
    return {
      id: `tabler:${slug}`,
      label: labelFromSlug(slug),
      pack: "tabler",
      keywords: keywordsFromSlug(slug, ["tabler", "outline"]),
      svgBody: parsedSvg.svgBody,
      svgViewBox: parsedSvg.svgViewBox,
    };
  })
  .filter((option): option is NonNullable<typeof option> => Boolean(option))
  .sort((left, right) => left.label.localeCompare(right.label));

export const BUILTIN_ICON_SET: BuiltinIconPickerSet = {
  id: "builtin:tabler-outline",
  label: "Tabler (Outline)",
  options: TABLER_OUTLINE_OPTIONS,
};
