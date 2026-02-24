import type { PersistedUiState } from "@/stores/dashboard/storeTypes";

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
