import { onBeforeUnmount, onMounted, ref, unref, watch, type MaybeRef } from "vue";

const DEFAULT_TIMEOUT_MS = 10 * 60 * 1000;
const ACTIVITY_EVENTS = [
  "mousemove",
  "mousedown",
  "keydown",
  "scroll",
  "touchstart",
  "click",
 ] as const;

interface UseIdleScreensaverOptions {
  timeoutMs?: number;
  onIdle?: () => void;
  onActive?: () => void;
  enabled?: MaybeRef<boolean>;
}

export function useIdleScreensaver(options: UseIdleScreensaverOptions = {}) {
  const timeoutMs = Math.max(
    1000,
    Number(options.timeoutMs || DEFAULT_TIMEOUT_MS),
  );
  const onIdle =
    typeof options.onIdle === "function" ? options.onIdle : () => {};
  const onActive =
    typeof options.onActive === "function" ? options.onActive : () => {};
  const enabledRef = options.enabled;

  const isIdle = ref(false);
  const isRunning = ref(false);
  const lastActivityAt = ref(Date.now());
  let idleTimerId: number | null = null;

  function clearIdleTimer(): void {
    if (idleTimerId === null) return;
    window.clearTimeout(idleTimerId);
    idleTimerId = null;
  }

  function scheduleIdleTimer(): void {
    clearIdleTimer();
    if (!isRunning.value) return;

    idleTimerId = window.setTimeout(() => {
      idleTimerId = null;
      if (!isRunning.value || isIdle.value) return;
      isIdle.value = true;
      onIdle();
    }, timeoutMs);
  }

  function markActivity(source = "activity"): void {
    if (!isRunning.value) return;
    if (document.visibilityState === "hidden" && source !== "visibilitychange") {
      return;
    }

    lastActivityAt.value = Date.now();
    if (isIdle.value) {
      isIdle.value = false;
      onActive();
    }
    scheduleIdleTimer();
  }

  function handleVisibilityChange(): void {
    if (document.visibilityState === "hidden") {
      clearIdleTimer();
      return;
    }
    markActivity("visibilitychange");
  }

  function handleUserActivity(): void {
    markActivity("activity");
  }

  function attachListeners(): void {
    for (const eventName of ACTIVITY_EVENTS) {
      window.addEventListener(eventName, handleUserActivity, {
        capture: true,
        passive: true,
      });
    }
    document.addEventListener("visibilitychange", handleVisibilityChange);
  }

  function detachListeners(): void {
    for (const eventName of ACTIVITY_EVENTS) {
      window.removeEventListener(eventName, handleUserActivity, true);
    }
    document.removeEventListener("visibilitychange", handleVisibilityChange);
  }

  function start(): void {
    if (isRunning.value) return;
    isRunning.value = true;
    attachListeners();
    markActivity("start");
  }

  function stop(): void {
    if (!isRunning.value) return;
    isRunning.value = false;
    clearIdleTimer();
    detachListeners();
    if (isIdle.value) {
      isIdle.value = false;
      onActive();
    }
  }

  function poke(): void {
    markActivity("poke");
  }

  onMounted(() => {
    if (enabledRef === undefined) {
      start();
      return;
    }

    if (unref(enabledRef)) {
      start();
    }
  });

  if (enabledRef !== undefined) {
    watch(
      () => Boolean(unref(enabledRef)),
      (enabled) => {
        if (enabled) {
          start();
          return;
        }
        stop();
      },
    );
  }

  onBeforeUnmount(() => {
    stop();
  });

  return {
    isIdle,
    isRunning,
    lastActivityAt,
    poke,
    start,
    stop,
  };
}
