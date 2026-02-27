import type {
  ThemeMode,
  ThemePalette,
} from "@/features/stores/dashboard/storeTypes";

const THEME_MODE_STORAGE_KEY = "oko:theme-mode:v1";
const THEME_PALETTE_STORAGE_KEY = "oko:theme-palette:v1";
const PREFERS_DARK_QUERY = "(prefers-color-scheme: dark)";

const THEME_COLORS: Record<ThemePalette, { dark: string; light: string }> = {
  emerald: {
    dark: "#0f1724",
    light: "#e9f0f5",
  },
  amethyst: {
    dark: "#0f0f1a",
    light: "#f3efff",
  },
};

let removeSystemThemeListener: (() => void) | null = null;

function getLocalStorageSafe(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage || null;
  } catch {
    return null;
  }
}

function normalizeThemeMode(value: unknown): ThemeMode {
  const normalized = String(value || "")
    .trim()
    .toLowerCase();
  if (
    normalized === "dark" ||
    normalized === "light" ||
    normalized === "system"
  ) {
    return normalized;
  }
  return "system";
}

function normalizeThemePalette(value: unknown): ThemePalette {
  const normalized = String(value || "")
    .trim()
    .toLowerCase();
  if (normalized === "amethyst" || normalized === "emerald") {
    return normalized;
  }
  return "emerald";
}

function prefersDarkTheme(): boolean {
  return Boolean(globalThis.matchMedia?.(PREFERS_DARK_QUERY).matches);
}

function resolveAppliedTheme(mode: ThemeMode): "dark" | "light" {
  if (mode === "dark" || mode === "light") return mode;
  return prefersDarkTheme() ? "dark" : "light";
}

function applyThemeMeta(
  appliedTheme: "dark" | "light",
  palette: ThemePalette,
): void {
  if (typeof document === "undefined") return;

  const colorSchemeMeta = document.querySelector<HTMLMetaElement>(
    'meta[name="color-scheme"]',
  );
  if (colorSchemeMeta) {
    colorSchemeMeta.setAttribute("content", appliedTheme);
  }

  const themeColorMeta = document.querySelector<HTMLMetaElement>(
    'meta[name="theme-color"]',
  );
  if (themeColorMeta) {
    themeColorMeta.setAttribute("content", THEME_COLORS[palette][appliedTheme]);
  }
}

function applyThemeToDocument(mode: ThemeMode, palette: ThemePalette): void {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  const appliedTheme = resolveAppliedTheme(mode);
  root.dataset.themeMode = mode;
  root.dataset.themePalette = palette;
  root.dataset.theme = appliedTheme;
  root.style.setProperty("--theme-color-scheme", appliedTheme);
  applyThemeMeta(appliedTheme, palette);
}

function persistThemeMode(mode: ThemeMode): void {
  const storage = getLocalStorageSafe();
  if (!storage) return;
  try {
    storage.setItem(THEME_MODE_STORAGE_KEY, mode);
  } catch {
    // ignore quota/privacy errors
  }
}

function persistThemePalette(palette: ThemePalette): void {
  const storage = getLocalStorageSafe();
  if (!storage) return;
  try {
    storage.setItem(THEME_PALETTE_STORAGE_KEY, palette);
  } catch {
    // ignore quota/privacy errors
  }
}

function syncSystemThemeMode(): void {
  if (typeof document === "undefined") return;
  if (document.documentElement.dataset.themeMode !== "system") return;
  applyThemeToDocument("system", getThemePalette());
}

function bindSystemThemeListener(mode: ThemeMode): void {
  if (removeSystemThemeListener) {
    removeSystemThemeListener();
    removeSystemThemeListener = null;
  }

  if (mode !== "system") return;
  const media = globalThis.matchMedia?.(PREFERS_DARK_QUERY);
  if (!media) return;

  if (media.addEventListener) {
    media.addEventListener("change", syncSystemThemeMode);
    removeSystemThemeListener = () => {
      media.removeEventListener("change", syncSystemThemeMode);
    };
    return;
  }

  if (media.addListener) {
    media.addListener(syncSystemThemeMode);
    removeSystemThemeListener = () => {
      media.removeListener(syncSystemThemeMode);
    };
  }
}

export function getThemeMode(): ThemeMode {
  if (typeof document !== "undefined") {
    const fromDataset = String(
      document.documentElement.dataset.themeMode || "",
    ).trim();
    if (fromDataset) {
      return normalizeThemeMode(fromDataset);
    }
  }

  const storage = getLocalStorageSafe();
  if (!storage) return "system";

  try {
    return normalizeThemeMode(storage.getItem(THEME_MODE_STORAGE_KEY));
  } catch {
    return "system";
  }
}

export function getThemePalette(): ThemePalette {
  if (typeof document !== "undefined") {
    const fromDataset = String(
      document.documentElement.dataset.themePalette || "",
    ).trim();
    if (fromDataset) {
      return normalizeThemePalette(fromDataset);
    }
  }

  const storage = getLocalStorageSafe();
  if (!storage) return "emerald";

  try {
    return normalizeThemePalette(storage.getItem(THEME_PALETTE_STORAGE_KEY));
  } catch {
    return "emerald";
  }
}

export function setThemeMode(
  mode: ThemeMode,
  options: { persist?: boolean } = {},
): ThemeMode {
  const normalizedMode = normalizeThemeMode(mode);
  const palette = getThemePalette();
  applyThemeToDocument(normalizedMode, palette);
  bindSystemThemeListener(normalizedMode);
  if (options.persist ?? true) {
    persistThemeMode(normalizedMode);
  }
  return normalizedMode;
}

export function setThemePalette(
  palette: ThemePalette,
  options: { persist?: boolean } = {},
): ThemePalette {
  const normalizedPalette = normalizeThemePalette(palette);
  const mode = getThemeMode();
  applyThemeToDocument(mode, normalizedPalette);
  if (options.persist ?? true) {
    persistThemePalette(normalizedPalette);
  }
  return normalizedPalette;
}

export function initThemeMode(): ThemeMode {
  const mode = normalizeThemeMode(getThemeMode());
  const palette = normalizeThemePalette(getThemePalette());
  applyThemeToDocument(mode, palette);
  bindSystemThemeListener(mode);
  return mode;
}
