import type {
  PersistedUiState,
  PersistedUiStateByRoute,
} from "@/stores/dashboard/storeTypes";

function getLocalStorageSafe(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage || null;
  } catch {
    return null;
  }
}

export function loadPersistedUiState(
  storageKey: string,
): PersistedUiState | null {
  const storage = getLocalStorageSafe();
  if (!storage) return null;

  try {
    const raw = storage.getItem(storageKey);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object"
      ? (parsed as PersistedUiState)
      : null;
  } catch {
    return null;
  }
}

export function savePersistedUiState(
  storageKey: string,
  snapshot: PersistedUiState,
): void {
  const storage = getLocalStorageSafe();
  if (!storage) return;

  try {
    storage.setItem(storageKey, JSON.stringify(snapshot));
  } catch {
    // ignore localStorage quota/security errors
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function asPersistedUiState(value: unknown): PersistedUiState | null {
  return isRecord(value) ? (value as PersistedUiState) : null;
}

export function loadPersistedUiStateByRoute(
  storageKey: string,
): PersistedUiStateByRoute {
  const storage = getLocalStorageSafe();
  if (!storage) {
    return { version: 2, byRoute: {} };
  }

  try {
    const raw = storage.getItem(storageKey);
    if (!raw) {
      return { version: 2, byRoute: {} };
    }

    const parsed = JSON.parse(raw);
    if (!isRecord(parsed)) {
      return { version: 2, byRoute: {} };
    }

    const rawByRoute = parsed.byRoute;
    if (isRecord(rawByRoute)) {
      const byRoute: Record<string, PersistedUiState> = {};
      for (const [routeKey, routeSnapshot] of Object.entries(rawByRoute)) {
        const normalizedRouteKey = String(routeKey || "").trim();
        if (!normalizedRouteKey) continue;
        const snapshot = asPersistedUiState(routeSnapshot);
        if (!snapshot) continue;
        byRoute[normalizedRouteKey] = snapshot;
      }

      return {
        version: Number(parsed.version || 2),
        byRoute,
      };
    }

    // Backward compatibility with v1 shape (single snapshot object).
    const legacySnapshot = asPersistedUiState(parsed);
    if (legacySnapshot) {
      return {
        version: 2,
        byRoute: {
          "/": legacySnapshot,
        },
      };
    }
  } catch {
    return { version: 2, byRoute: {} };
  }

  return { version: 2, byRoute: {} };
}

export function savePersistedUiStateByRoute(
  storageKey: string,
  byRoute: Record<string, PersistedUiState>,
): void {
  const storage = getLocalStorageSafe();
  if (!storage) return;

  const payload: PersistedUiStateByRoute = {
    version: 2,
    byRoute,
  };

  try {
    storage.setItem(storageKey, JSON.stringify(payload));
  } catch {
    // ignore localStorage quota/security errors
  }
}
