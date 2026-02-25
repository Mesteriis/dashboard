import { isInfraSlug, type BuiltinIconPickerSet } from "@/shared/iconsets/simpleIconsUtils";

export type { BuiltinIconPickerOption, BuiltinIconPickerSet } from "@/shared/iconsets/simpleIconsUtils";

export interface BuiltinIconSetCatalogEntry {
  id: string;
  label: string;
  pack: string;
}

export const BUILTIN_ICON_SET_CATALOG: BuiltinIconSetCatalogEntry[] = [
  {
    id: "builtin:basic-ui",
    label: "Basic UI",
    pack: "basic-ui",
  },
  {
    id: "builtin:tabler-outline",
    label: "Tabler (Outline)",
    pack: "tabler",
  },
  {
    id: "builtin:tabler-filled",
    label: "Tabler (Filled)",
    pack: "tabler-filled",
  },
  {
    id: "builtin:simple-services",
    label: "Services",
    pack: "simple-services",
  },
  {
    id: "builtin:simple-infra",
    label: "Infrastructure",
    pack: "simple-infra",
  },
];

export const DEFAULT_BUILTIN_ICON_SET_ID = "builtin:basic-ui";

type BuiltinSetModule = {
  BUILTIN_ICON_SET: BuiltinIconPickerSet;
};

const BUILTIN_SET_LOADERS: Record<string, () => Promise<BuiltinSetModule>> = {
  "builtin:basic-ui": () => import("@/shared/iconsets/sets/builtinBasicUiSet"),
  "builtin:tabler-outline": () => import("@/shared/iconsets/sets/builtinTablerOutlineSet"),
  "builtin:tabler-filled": () => import("@/shared/iconsets/sets/builtinTablerFilledSet"),
  "builtin:simple-services": () => import("@/shared/iconsets/sets/builtinSimpleServicesSet"),
  "builtin:simple-infra": () => import("@/shared/iconsets/sets/builtinSimpleInfraSet"),
};

const builtinSetCache = new Map<string, BuiltinIconPickerSet>();

export function resolveBuiltinSetIdByPack(pack: string): string | null {
  const normalizedPack = String(pack || "").trim();
  if (!normalizedPack) return null;
  const entry = BUILTIN_ICON_SET_CATALOG.find((candidate) => candidate.pack === normalizedPack);
  return entry?.id || null;
}

export function guessBuiltinSetIdByIconId(iconId: string): string | null {
  const normalizedId = String(iconId || "").trim();
  if (!normalizedId) return null;

  if (normalizedId.startsWith("basic:")) {
    return "builtin:basic-ui";
  }
  if (normalizedId.startsWith("tabler:")) {
    return "builtin:tabler-outline";
  }
  if (normalizedId.startsWith("tabler-filled:")) {
    return "builtin:tabler-filled";
  }
  if (normalizedId.startsWith("simple:")) {
    const slug = normalizedId.slice("simple:".length);
    return isInfraSlug(slug) ? "builtin:simple-infra" : "builtin:simple-services";
  }
  return null;
}

export async function loadBuiltinIconSet(setId: string): Promise<BuiltinIconPickerSet | null> {
  const normalizedSetId = String(setId || "").trim();
  if (!normalizedSetId) return null;

  if (builtinSetCache.has(normalizedSetId)) {
    return builtinSetCache.get(normalizedSetId) || null;
  }

  const loader = BUILTIN_SET_LOADERS[normalizedSetId];
  if (!loader) return null;

  const module = await loader();
  const iconSet = module.BUILTIN_ICON_SET;
  builtinSetCache.set(normalizedSetId, iconSet);
  return iconSet;
}

export async function loadBuiltinIconSets(setIds: string[]): Promise<BuiltinIconPickerSet[]> {
  const requestedSetIds = Array.from(
    new Set(setIds.map((setId) => String(setId || "").trim()).filter(Boolean)),
  );

  const loadedSets = await Promise.all(requestedSetIds.map((setId) => loadBuiltinIconSet(setId)));
  return loadedSets.filter((set): set is BuiltinIconPickerSet => Boolean(set));
}
