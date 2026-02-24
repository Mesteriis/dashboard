<template>
  <main class="app-shell blank-page">
    <aside class="sidebar blank-sidebar">
      <div
        :id="BLANK_SIDEBAR_PARTICLES_ID"
        class="sidebar-particles"
        aria-hidden="true"
      ></div>

      <div class="sidebar-content">
        <header class="brand">
          <img :src="EMBLEM_SRC" alt="Oko" />
          <div>
            <p class="brand-title">Oko</p>
            <p class="brand-subtitle">Your Infrastructure in Sight</p>
          </div>
        </header>
      </div>
    </aside>

    <section class="blank-main">
      <HeroGlassTabsShell :emblem-src="EMBLEM_SRC">
        <div class="blank-main-head">
          <div class="hero-logo-square" aria-hidden="true">
            <img :src="EMBLEM_SRC" alt="" />
          </div>
          <p class="blank-main-title">Blank</p>
        </div>
      </HeroGlassTabsShell>

      <section class="blank-canvas" aria-label="Blank page"></section>
    </section>
  </main>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted } from "vue";
import HeroGlassTabsShell from "@/components/primitives/HeroGlassTabsShell.vue";
import { EVENT_FX_MODE_CHANGE, onOkoEvent } from "@/services/events";
import { ensureParticlesJs } from "@/services/particlesLoader";
import {
  EMBLEM_SRC,
  SIDEBAR_PARTICLES_CONFIG,
} from "@/stores/dashboard/storeConstants";
import type { ParticlesConfig } from "@/stores/dashboard/storeTypes";

const BLANK_SIDEBAR_PARTICLES_ID = "blank-sidebar-particles";
let removeFxModeListener: () => void = () => {};

function currentFxMode(): string {
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

function resetSidebarParticles(): void {
  const container = document.getElementById(BLANK_SIDEBAR_PARTICLES_ID);
  if (!container) return;
  container.innerHTML = "";
}

async function initSidebarParticles(): Promise<void> {
  const container = document.getElementById(BLANK_SIDEBAR_PARTICLES_ID);
  if (!container) return;

  const tunedConfig = tuneParticlesConfig(SIDEBAR_PARTICLES_CONFIG);
  if (!tunedConfig) {
    resetSidebarParticles();
    return;
  }

  const isParticlesReady = await ensureParticlesJs();
  if (!isParticlesReady || !window.particlesJS) return;
  if (!document.getElementById(BLANK_SIDEBAR_PARTICLES_ID)) return;

  resetSidebarParticles();
  await window.particlesJS(BLANK_SIDEBAR_PARTICLES_ID, tunedConfig);
}

onMounted(() => {
  removeFxModeListener = onOkoEvent(EVENT_FX_MODE_CHANGE, () => {
    void initSidebarParticles();
  });
  void initSidebarParticles();
});

onBeforeUnmount(() => {
  removeFxModeListener();
  removeFxModeListener = () => {};
  resetSidebarParticles();
});
</script>

<style scoped>
.blank-page {
  grid-template-columns: 420px minmax(0, 1fr) !important;
}

.blank-sidebar {
  top: 0;
  height: calc(100vh - 48px - var(--desktop-drag-strip));
  height: calc(100dvh - 48px - var(--desktop-drag-strip));
  max-height: calc(100vh - 48px - var(--desktop-drag-strip));
  max-height: calc(100dvh - 48px - var(--desktop-drag-strip));
}

.blank-main {
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 10px;
}

.blank-main-head {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.blank-main-title {
  margin: 0;
  font-family: "Cinzel", "Times New Roman", serif;
  letter-spacing: 0.05em;
  font-size: 1rem;
}

.blank-canvas {
  border: 1px solid rgba(89, 144, 166, 0.18);
  border-radius: calc(var(--card-radius) + 4px);
  background: rgba(5, 13, 21, 0.16);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}
</style>
