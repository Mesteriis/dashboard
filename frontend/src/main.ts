import { createApp } from "vue";
import { MotionPlugin } from "@vueuse/motion";
import App from "@/App.vue";
import router from "@/router";
import { bindNavigationRouter } from "@/core/navigation/nav";
import { initDesktopRuntimeBridge } from "@/services/desktopRuntime";
import { EVENT_FX_MODE_CHANGE, emitOkoEvent } from "@/services/events";
import { initDevPerfTelemetry } from "@/services/perfTelemetry";
import "./styles.scss";

type LegacyFxMode = "off" | "lite" | "full";

function resolveFxMode(): LegacyFxMode {
  const prefersReduced = globalThis.matchMedia?.(
    "(prefers-reduced-motion: reduce)",
  )?.matches;
  if (prefersReduced) return "off";

  const cores = Number(globalThis.navigator?.hardwareConcurrency || 8);
  const memory = Number(globalThis.navigator?.deviceMemory || 8);
  if (cores <= 4 || memory <= 4) return "lite";
  return "full";
}

function applyFxMode(mode: LegacyFxMode): void {
  const root = document.documentElement;
  const previousMode = root.dataset.fxMode || "";
  root.dataset.fxMode = mode;

  if (mode === "off") {
    root.style.setProperty("--glow-enabled", "0");
  } else if (mode === "lite") {
    root.style.setProperty("--glow-enabled", "0.58");
  } else {
    root.style.setProperty("--glow-enabled", "1");
  }

  if (previousMode && previousMode !== mode) {
    emitOkoEvent(EVENT_FX_MODE_CHANGE, { mode, previousMode });
  }
}

function initFxModeProfile(): void {
  const mq = globalThis.matchMedia?.("(prefers-reduced-motion: reduce)");
  const sync = () => applyFxMode(resolveFxMode());
  sync();

  if (mq?.addEventListener) {
    mq.addEventListener("change", sync);
  } else if (mq?.addListener) {
    mq.addListener(sync);
  }
}

initFxModeProfile();
initDevPerfTelemetry({ enabled: import.meta.env.DEV });

async function bootstrap(): Promise<void> {
  await initDesktopRuntimeBridge();
  bindNavigationRouter(router);
  createApp(App).use(router).use(MotionPlugin).mount("#app");
}

void bootstrap();
