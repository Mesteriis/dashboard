import {
  computed,
  getCurrentScope,
  onScopeDispose,
  readonly,
  ref,
  type ComputedRef,
  type Ref,
} from "vue";
import {
  EVENT_AGENT_FX_MODE_CHANGE,
  EVENT_FX_MODE_CHANGE,
  emitOkoEvent,
  onOkoEvent,
} from "@/features/services/events";

export type FxMode = "off" | "plasma" | "particles";
export type LegacyFxMode = "off" | "lite" | "full";

interface SetFxModeOptions {
  propagateLegacy?: boolean;
  source?: string;
}

const FX_MODE_STORAGE_KEY = "oko.fxMode";
const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";

const FX_MODE_ORDER: FxMode[] = ["off", "plasma", "particles"];

const currentFxMode = ref<FxMode>("plasma");
const reducedMotion = ref(false);
const effectiveFxMode = computed<FxMode>(() =>
  reducedMotion.value ? "off" : currentFxMode.value,
);

let initialized = false;
let consumerCount = 0;
let mediaQueryList: MediaQueryList | null = null;
let appliedLegacySync = false;
let removeLegacyFxListener: (() => void) | null = null;

function clampGlow(mode: LegacyFxMode): string {
  if (mode === "off") return "0";
  if (mode === "lite") return "0.58";
  return "1";
}

function isFxMode(value: unknown): value is FxMode {
  return value === "off" || value === "plasma" || value === "particles";
}

function isLegacyFxMode(value: unknown): value is LegacyFxMode {
  return value === "off" || value === "lite" || value === "full";
}

function normalizeLegacyFxMode(value: unknown): LegacyFxMode {
  const normalized = String(value || "")
    .trim()
    .toLowerCase();
  if (isLegacyFxMode(normalized)) return normalized;
  return "full";
}

function toLegacyFxMode(mode: FxMode): LegacyFxMode {
  if (mode === "off") return "off";
  if (mode === "particles") return "lite";
  return "full";
}

function fromLegacyFxMode(mode: LegacyFxMode): FxMode {
  if (mode === "off") return "off";
  if (mode === "lite") return "particles";
  return "plasma";
}

function readLegacyModeFromDom(): LegacyFxMode {
  if (typeof document === "undefined") return "full";
  return normalizeLegacyFxMode(
    document.documentElement?.dataset?.fxMode || "full",
  );
}

function readPersistedFxMode(): FxMode | "" {
  if (typeof window === "undefined") return "";
  const raw = window.localStorage.getItem(FX_MODE_STORAGE_KEY);
  if (!raw) return "";
  const normalized = raw.trim().toLowerCase();
  return isFxMode(normalized) ? normalized : "";
}

function persistFxMode(mode: FxMode): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(FX_MODE_STORAGE_KEY, mode);
}

function applyLegacyMode(mode: LegacyFxMode): void {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  root.dataset.fxMode = mode;
  root.style.setProperty("--glow-enabled", clampGlow(mode));
}

function dispatchLegacyModeChange(
  mode: LegacyFxMode,
  previousMode: LegacyFxMode,
): void {
  emitOkoEvent(EVENT_FX_MODE_CHANGE, {
    mode,
    previousMode,
  });
}

function dispatchAgentFxModeChange(
  mode: FxMode,
  previousMode: FxMode,
  source: string,
): void {
  emitOkoEvent(EVENT_AGENT_FX_MODE_CHANGE, {
    mode,
    previousMode,
    source,
  });
}

function resolveInitialFxMode(): FxMode {
  const persisted = readPersistedFxMode();
  if (persisted) return persisted;
  const legacy = readLegacyModeFromDom();
  return fromLegacyFxMode(legacy);
}

function syncFromLegacyMode(mode: LegacyFxMode): void {
  const mapped = fromLegacyFxMode(mode);
  if (mapped === currentFxMode.value) {
    persistFxMode(mapped);
    return;
  }
  const previousMode = currentFxMode.value;
  currentFxMode.value = mapped;
  persistFxMode(mapped);
  dispatchAgentFxModeChange(mapped, previousMode, "legacy-sync");
}

function handleLegacyModeChange(event: Event): void {
  if (appliedLegacySync) return;
  const customEvent = event as CustomEvent<{ mode?: LegacyFxMode }>;
  const incomingMode = normalizeLegacyFxMode(
    customEvent.detail?.mode || readLegacyModeFromDom(),
  );
  syncFromLegacyMode(incomingMode);
}

function handleReducedMotionChange(event: MediaQueryListEvent): void {
  reducedMotion.value = Boolean(event.matches);
}

function handleStorageSync(event: StorageEvent): void {
  if (event.key !== FX_MODE_STORAGE_KEY) return;
  const incoming = readPersistedFxMode();
  if (!incoming || incoming === currentFxMode.value) return;
  const previousMode = currentFxMode.value;
  currentFxMode.value = incoming;
  dispatchAgentFxModeChange(incoming, previousMode, "storage-sync");

  const nextLegacy = toLegacyFxMode(incoming);
  const previousLegacy = readLegacyModeFromDom();
  if (nextLegacy === previousLegacy) return;
  appliedLegacySync = true;
  try {
    applyLegacyMode(nextLegacy);
    dispatchLegacyModeChange(nextLegacy, previousLegacy);
  } finally {
    appliedLegacySync = false;
  }
}

function bindGlobalListeners(): void {
  if (typeof window === "undefined") return;
  removeLegacyFxListener = onOkoEvent(
    EVENT_FX_MODE_CHANGE,
    handleLegacyModeChange,
  );
  window.addEventListener("storage", handleStorageSync);

  mediaQueryList = window.matchMedia?.(REDUCED_MOTION_QUERY) || null;
  reducedMotion.value = Boolean(mediaQueryList?.matches);
  if (!mediaQueryList) return;
  if (mediaQueryList.addEventListener) {
    mediaQueryList.addEventListener("change", handleReducedMotionChange);
    return;
  }
  if (mediaQueryList.addListener) {
    mediaQueryList.addListener(handleReducedMotionChange);
  }
}

function unbindGlobalListeners(): void {
  if (typeof window !== "undefined") {
    removeLegacyFxListener?.();
    removeLegacyFxListener = null;
    window.removeEventListener("storage", handleStorageSync);
  }

  if (!mediaQueryList) return;
  if (mediaQueryList.removeEventListener) {
    mediaQueryList.removeEventListener("change", handleReducedMotionChange);
  } else if (mediaQueryList.removeListener) {
    mediaQueryList.removeListener(handleReducedMotionChange);
  }
  mediaQueryList = null;
}

function ensureInitialized(): void {
  if (initialized) return;
  initialized = true;
  currentFxMode.value = resolveInitialFxMode();
  persistFxMode(currentFxMode.value);
  bindGlobalListeners();
}

function setFxMode(nextMode: FxMode, options: SetFxModeOptions = {}): void {
  if (!isFxMode(nextMode)) return;
  ensureInitialized();

  const previousMode = currentFxMode.value;
  if (previousMode === nextMode) {
    persistFxMode(nextMode);
  } else {
    currentFxMode.value = nextMode;
    persistFxMode(nextMode);
    dispatchAgentFxModeChange(nextMode, previousMode, options.source || "set");
  }

  const shouldPropagate = options.propagateLegacy !== false;
  if (!shouldPropagate) return;

  const nextLegacy = toLegacyFxMode(nextMode);
  const previousLegacy = readLegacyModeFromDom();
  if (nextLegacy === previousLegacy) return;

  appliedLegacySync = true;
  try {
    applyLegacyMode(nextLegacy);
    dispatchLegacyModeChange(nextLegacy, previousLegacy);
  } finally {
    appliedLegacySync = false;
  }
}

function cycleFxMode(step = 1): void {
  ensureInitialized();
  const direction = Number.isFinite(step) ? Math.trunc(step) : 1;
  if (!direction) return;

  const currentIndex = FX_MODE_ORDER.indexOf(currentFxMode.value);
  const normalizedIndex = currentIndex >= 0 ? currentIndex : 0;
  const delta = Math.abs(direction) % FX_MODE_ORDER.length || 1;
  const nextIndex =
    (normalizedIndex +
      (direction > 0 ? delta : -delta) +
      FX_MODE_ORDER.length * 2) %
    FX_MODE_ORDER.length;
  setFxMode(FX_MODE_ORDER[nextIndex], { source: "cycle" });
}

function retainComposableScope(): void {
  ensureInitialized();
  consumerCount += 1;
}

function releaseComposableScope(): void {
  consumerCount = Math.max(0, consumerCount - 1);
  if (consumerCount > 0) return;
  unbindGlobalListeners();
  initialized = false;
}

export function useFxMode(): {
  fxMode: Readonly<Ref<FxMode>>;
  effectiveFxMode: ComputedRef<FxMode>;
  prefersReducedMotion: Readonly<Ref<boolean>>;
  setFxMode: (mode: FxMode, options?: SetFxModeOptions) => void;
  cycleFxMode: (step?: number) => void;
  fxModeOrder: Readonly<FxMode[]>;
} {
  retainComposableScope();

  if (getCurrentScope()) {
    onScopeDispose(() => {
      releaseComposableScope();
    });
  }

  return {
    fxMode: readonly(currentFxMode),
    effectiveFxMode,
    prefersReducedMotion: readonly(reducedMotion),
    setFxMode,
    cycleFxMode,
    fxModeOrder: FX_MODE_ORDER,
  };
}

export const FX_MODE_STORAGE = FX_MODE_STORAGE_KEY;
export const AGENT_FX_MODE_CHANGE_EVENT = EVENT_AGENT_FX_MODE_CHANGE;
