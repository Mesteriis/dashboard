import { onBeforeUnmount, onMounted, watch, type Ref } from "vue";
import { EVENT_FX_MODE_CHANGE, onOkoEvent } from "@/features/services/events";
import { ensureParticlesJs } from "@/features/services/particlesLoader";
import type { ParticlesConfig } from "@/features/stores/dashboard/storeTypes";

interface UseSidebarParticlesOptions {
  containerId: string;
  baseConfig: ParticlesConfig;
  /**
   * Опциональный флаг видимости сайдбара.
   * Если передан, частицы перезапускаются при повторном показе.
   */
  isSidebarHidden?: Ref<boolean>;
}

function currentFxMode(): string {
  if (typeof document === "undefined") return "full";
  return document.documentElement?.dataset?.fxMode || "full";
}

function cloneParticlesConfig(config: ParticlesConfig): ParticlesConfig {
  return JSON.parse(JSON.stringify(config)) as ParticlesConfig;
}

function tuneParticlesConfig(config: ParticlesConfig): ParticlesConfig | null {
  const mode = currentFxMode();
  if (mode === "off") return null;

  const tuned = cloneParticlesConfig(config);
  tuned.fps_limit = mode === "lite" ? 34 : 58;
  if (mode !== "lite") return tuned;

  tuned.particles.number.value = Math.max(
    24,
    Math.round(tuned.particles.number.value * 0.56),
  );
  tuned.particles.opacity.value = Number(
    (tuned.particles.opacity.value * 0.72).toFixed(2),
  );
  tuned.particles.move.speed = Number(
    (tuned.particles.move.speed * 0.74).toFixed(2),
  );
  tuned.particles.line_linked.opacity = Number(
    (tuned.particles.line_linked.opacity * 0.56).toFixed(2),
  );
  tuned.particles.line_linked.distance = Math.max(
    80,
    Math.round(tuned.particles.line_linked.distance * 0.84),
  );
  tuned.retina_detect = false;
  return tuned;
}

function resetParticlesContainer(containerId: string): void {
  if (typeof document === "undefined") return;
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = "";
  delete (container as HTMLElement & { dataset: DOMStringMap }).dataset
    .particlesReady;
}

export function useSidebarParticles(options: UseSidebarParticlesOptions): {
  initSidebarParticles: () => Promise<void>;
  resetSidebarParticles: () => void;
} {
  const { containerId, baseConfig, isSidebarHidden } = options;
  let removeFxModeListener: () => void = () => {};

  async function initSidebarParticles(): Promise<void> {
    if (typeof document === "undefined") return;
    const container = document.getElementById(containerId);
    if (!container) return;

    const tunedConfig = tuneParticlesConfig(baseConfig);
    if (!tunedConfig) {
      resetParticlesContainer(containerId);
      return;
    }

    // Не дублируем инициализацию, если уже отрисовано.
    if (
      (container as HTMLElement & { dataset: DOMStringMap }).dataset
        .particlesReady === "1"
    ) {
      return;
    }

    const isReady = await ensureParticlesJs();
    if (!isReady || !window.particlesJS) return;
    if (!document.getElementById(containerId)) return;

    resetParticlesContainer(containerId);
    await window.particlesJS(containerId, tunedConfig);
    (container as HTMLElement & { dataset: DOMStringMap }).dataset.particlesReady =
      "1";
  }

  onMounted(() => {
    if (!isSidebarHidden || !isSidebarHidden.value) {
      void initSidebarParticles();
    }

    removeFxModeListener = onOkoEvent(EVENT_FX_MODE_CHANGE, () => {
      void initSidebarParticles();
    });
  });

  if (isSidebarHidden) {
    watch(
      () => isSidebarHidden.value,
      (hidden) => {
        if (hidden) return;
        void initSidebarParticles();
      },
    );
  }

  onBeforeUnmount(() => {
    removeFxModeListener();
    removeFxModeListener = () => {};
    resetParticlesContainer(containerId);
  });

  return {
    initSidebarParticles,
    resetSidebarParticles: () => resetParticlesContainer(containerId),
  };
}

