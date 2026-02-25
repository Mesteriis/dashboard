import type { BuiltinIconPickerSet } from "@/shared/iconsets/simpleIconsUtils";
import {
  keywordsFromSlug,
  labelFromSlug,
  parseSvgMarkup,
  slugFromSvgFilePath,
} from "@/shared/iconsets/tablerSvgUtils";

const FILLED_SVG_MODULES = import.meta.glob<string>(
  "/node_modules/@tabler/icons/icons/filled/*.svg",
  {
    query: "?raw",
    import: "default",
    eager: true,
  },
);

const TABLER_FILLED_OPTIONS = Object.entries(FILLED_SVG_MODULES)
  .map(([filePath, svgMarkup]) => {
    const slug = slugFromSvgFilePath(filePath);
    if (!slug) return null;

    const parsedSvg = parseSvgMarkup(svgMarkup);
    return {
      id: `tabler-filled:${slug}`,
      label: labelFromSlug(slug),
      pack: "tabler-filled",
      keywords: keywordsFromSlug(slug, ["tabler", "filled"]),
      svgBody: parsedSvg.svgBody,
      svgViewBox: parsedSvg.svgViewBox,
    };
  })
  .filter((option): option is NonNullable<typeof option> => Boolean(option))
  .sort((left, right) => left.label.localeCompare(right.label));

export const BUILTIN_ICON_SET: BuiltinIconPickerSet = {
  id: "builtin:tabler-filled",
  label: "Tabler (Filled)",
  options: TABLER_FILLED_OPTIONS,
};
