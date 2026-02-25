export type BlankPrimaryTabId = "overview" | "operations";
export type BlankSidebarVisibility = "open" | "hidden";

export interface BlankLayoutLevelOneState {
  sidebarVisibility: BlankSidebarVisibility;
  heroControlsExpanded: boolean;
}

export interface BlankLayoutLevelTwoState {
  activeTabId: BlankPrimaryTabId;
  activeCanvasSectionId: string;
}

export interface BlankLayoutPersistedState {
  version: 1;
  levelOne: BlankLayoutLevelOneState;
  levelTwo: BlankLayoutLevelTwoState;
}

export const BLANK_LAYOUT_STORAGE_KEY = "oko:blank-layout-ui:v1";

function getLocalStorageSafe(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage || null;
  } catch {
    return null;
  }
}

export function createDefaultBlankLayoutState(): BlankLayoutPersistedState {
  return {
    version: 1,
    levelOne: {
      sidebarVisibility: "open",
      heroControlsExpanded: true,
    },
    levelTwo: {
      activeTabId: "overview",
      activeCanvasSectionId: "",
    },
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function normalizeLevelOne(input: unknown): BlankLayoutLevelOneState {
  if (!isRecord(input)) {
    return createDefaultBlankLayoutState().levelOne;
  }

  const sidebar = String(input.sidebarVisibility || "open");
  return {
    sidebarVisibility: sidebar === "hidden" ? "hidden" : "open",
    heroControlsExpanded: Boolean(input.heroControlsExpanded),
  };
}

function normalizeLevelTwo(input: unknown): BlankLayoutLevelTwoState {
  if (!isRecord(input)) {
    return createDefaultBlankLayoutState().levelTwo;
  }

  const tab = String(input.activeTabId || "overview");
  return {
    activeTabId: tab === "operations" ? "operations" : "overview",
    activeCanvasSectionId: String(input.activeCanvasSectionId || ""),
  };
}

export function loadBlankLayoutState(
  storageKey = BLANK_LAYOUT_STORAGE_KEY,
): BlankLayoutPersistedState {
  const defaults = createDefaultBlankLayoutState();
  const storage = getLocalStorageSafe();
  if (!storage) return defaults;

  try {
    const raw = storage.getItem(storageKey);
    if (!raw) return defaults;

    const parsed = JSON.parse(raw);
    if (!isRecord(parsed)) return defaults;

    return {
      version: 1,
      levelOne: normalizeLevelOne(parsed.levelOne),
      levelTwo: normalizeLevelTwo(parsed.levelTwo),
    };
  } catch {
    return defaults;
  }
}

export function saveBlankLayoutState(
  snapshot: BlankLayoutPersistedState,
  storageKey = BLANK_LAYOUT_STORAGE_KEY,
): void {
  const storage = getLocalStorageSafe();
  if (!storage) return;

  try {
    storage.setItem(storageKey, JSON.stringify(snapshot));
  } catch {
    // ignore quota/security errors
  }
}

export function patchBlankLayoutLevelOne(
  partial: Partial<BlankLayoutLevelOneState>,
  storageKey = BLANK_LAYOUT_STORAGE_KEY,
): BlankLayoutPersistedState {
  const current = loadBlankLayoutState(storageKey);
  const next: BlankLayoutPersistedState = {
    ...current,
    levelOne: {
      ...current.levelOne,
      ...partial,
    },
  };
  saveBlankLayoutState(next, storageKey);
  return next;
}

export function patchBlankLayoutLevelTwo(
  partial: Partial<BlankLayoutLevelTwoState>,
  storageKey = BLANK_LAYOUT_STORAGE_KEY,
): BlankLayoutPersistedState {
  const current = loadBlankLayoutState(storageKey);
  const next: BlankLayoutPersistedState = {
    ...current,
    levelTwo: {
      ...current.levelTwo,
      ...partial,
    },
  };
  saveBlankLayoutState(next, storageKey);
  return next;
}
