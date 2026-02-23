import { onBeforeUnmount, onMounted, ref, unref, watch } from "vue";

const DEFAULT_TIMEOUT_MS = 10 * 60 * 1000;
const ACTIVITY_EVENTS = [
  "mousemove",
  "mousedown",
  "keydown",
  "scroll",
  "touchstart",
  "click",
];

export function useIdleScreensaver(options = {}) {
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
  let idleTimerId = 0;

  function clearIdleTimer() {
    if (!idleTimerId) return;
    window.clearTimeout(idleTimerId);
    idleTimerId = 0;
  }

  function scheduleIdleTimer() {
    clearIdleTimer();
    if (!isRunning.value) return;

    idleTimerId = window.setTimeout(() => {
      idleTimerId = 0;
      if (!isRunning.value || isIdle.value) return;
      isIdle.value = true;
      onIdle();
    }, timeoutMs);
  }

  function markActivity(source = "activity") {
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

  function handleVisibilityChange() {
    if (document.visibilityState === "hidden") {
      clearIdleTimer();
      return;
    }
    markActivity("visibilitychange");
  }

  function handleUserActivity() {
    markActivity("activity");
  }

  function attachListeners() {
    for (const eventName of ACTIVITY_EVENTS) {
      window.addEventListener(eventName, handleUserActivity, {
        capture: true,
        passive: true,
      });
    }
    document.addEventListener("visibilitychange", handleVisibilityChange);
  }

  function detachListeners() {
    for (const eventName of ACTIVITY_EVENTS) {
      window.removeEventListener(eventName, handleUserActivity, true);
    }
    document.removeEventListener("visibilitychange", handleVisibilityChange);
  }

  function start() {
    if (isRunning.value) return;
    isRunning.value = true;
    attachListeners();
    markActivity("start");
  }

  function stop() {
    if (!isRunning.value) return;
    isRunning.value = false;
    clearIdleTimer();
    detachListeners();
    if (isIdle.value) {
      isIdle.value = false;
      onActive();
    }
  }

  function poke() {
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
