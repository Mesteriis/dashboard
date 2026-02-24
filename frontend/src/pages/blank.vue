<template>
  <UiBlankLayout
    :emblem-src="EMBLEM_SRC"
    :sidebar-hidden="isSidebarHidden"
    :sidebar-particles-id="BLANK_SIDEBAR_PARTICLES_ID"
  >
    <template v-slot:[SLOT_APP_SIDEBAR_TOP]>
      <header class="brand">
        <img :src="EMBLEM_SRC" alt="" aria-hidden="true" />
        <div>
          <p class="brand-title">Oko</p>
          <p class="brand-subtitle">Your Infrastructure in Sight</p>
        </div>
      </header>
    </template>

    <template v-slot:[SLOT_APP_HEADER_TABS]>
      <UiHeroBlankPanel
        v-model="activeBlankTab"
        v-model:hero-controls-open="heroControlsOpen"
      />
    </template>

    <template v-slot:[SLOT_PAGE_CANVAS_MAIN]>
      <article
        id="blank-panel-overview"
        class="blank-demo blank-demo--overview"
        role="tabpanel"
        :tabindex="activeBlankTab === 'overview' ? 0 : -1"
        aria-labelledby="blank-tab-overview"
        :hidden="activeBlankTab !== 'overview'"
      >
        <header>
          <h2>Обзор пространства</h2>
          <p>Демонстрационный таб: основной контент переключается из hero-tabs.</p>
        </header>
        <div class="blank-demo-grid">
          <section class="blank-demo-card">
            <h3>Контур 01</h3>
            <p>Точка для размещения ключевых виджетов и summary-блоков.</p>
          </section>
          <section class="blank-demo-card">
            <h3>Контур 02</h3>
            <p>Блок для статусов и актуальных событий в оперативной зоне.</p>
          </section>
        </div>
      </article>

      <article
        id="blank-panel-operations"
        class="blank-demo blank-demo--operations"
        role="tabpanel"
        :tabindex="activeBlankTab === 'operations' ? 0 : -1"
        aria-labelledby="blank-tab-operations"
        :hidden="activeBlankTab !== 'operations'"
      >
        <header>
          <h2>Оперативный контур</h2>
          <p>Второй демо-таб для проверки плавного раскрытия и смены контента.</p>
        </header>
        <div class="blank-demo-stack">
          <section class="blank-demo-strip">
            <strong>Сценарий A</strong>
            <span>Заглушка под workflow и управляющие действия.</span>
          </section>
          <section class="blank-demo-strip">
            <strong>Сценарий B</strong>
            <span>Зона под мониторинг и блок реакции на инциденты.</span>
          </section>
        </div>
      </article>
    </template>
  </UiBlankLayout>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import UiHeroBlankPanel from "@/components/ui-kit/primitives/UiHeroBlankPanel.vue";
import UiBlankLayout from "@/components/ui-kit/primitives/UiBlankLayout.vue";
import { EVENT_FX_MODE_CHANGE, onOkoEvent } from "@/services/events";
import { ensureParticlesJs } from "@/services/particlesLoader";
import { useUiStore } from "@/stores/uiStore";
import {
  type BlankPrimaryTabId,
  loadBlankLayoutState,
  patchBlankLayoutLevelOne,
  patchBlankLayoutLevelTwo,
} from "@/stores/blankLayoutStore";
import {
  EMBLEM_SRC,
  SIDEBAR_PARTICLES_CONFIG,
} from "@/stores/ui/storeConstants";
import type { ParticlesConfig } from "@/stores/ui/storeTypes";

const BLANK_SIDEBAR_PARTICLES_ID = "blank-sidebar-particles";
const SLOT_APP_SIDEBAR_TOP = "app.sidebar.top";
const SLOT_APP_HEADER_TABS = "app.header.tabs";
const SLOT_PAGE_CANVAS_MAIN = "page.canvas.main";
let removeFxModeListener: () => void = () => {};
const uiStore = useUiStore();
const restoredBlankLayoutState = loadBlankLayoutState();
const activeBlankTab = ref<BlankPrimaryTabId>(
  restoredBlankLayoutState.levelTwo.activeTabId,
);
const heroControlsOpen = ref(
  restoredBlankLayoutState.levelOne.heroControlsExpanded,
);
const isSidebarHidden = computed(
  () => uiStore.sidebarView.value === "hidden",
);

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
  uiStore.sidebarView.value =
    restoredBlankLayoutState.levelOne.sidebarVisibility === "hidden"
      ? "hidden"
      : "detailed";

  removeFxModeListener = onOkoEvent(EVENT_FX_MODE_CHANGE, () => {
    void initSidebarParticles();
  });
  void initSidebarParticles();
});

watch(
  () => activeBlankTab.value,
  (tabId) => {
    patchBlankLayoutLevelTwo({ activeTabId: tabId });
  },
);

watch(
  () => heroControlsOpen.value,
  (expanded) => {
    patchBlankLayoutLevelOne({ heroControlsExpanded: expanded });
  },
);

watch(
  () => uiStore.sidebarView.value,
  (value) => {
    patchBlankLayoutLevelOne({
      sidebarVisibility: value === "hidden" ? "hidden" : "open",
    });
  },
);

watch(
  () => isSidebarHidden.value,
  (hidden) => {
    if (hidden) return;
    void initSidebarParticles();
  },
);

onBeforeUnmount(() => {
  removeFxModeListener();
  removeFxModeListener = () => {};
  resetSidebarParticles();
});
</script>

<style scoped>
.blank-demo {
  min-height: 100%;
  border: 1px solid rgba(88, 148, 173, 0.2);
  border-radius: var(--ui-radius);
  background: linear-gradient(
    152deg,
    rgba(7, 21, 34, 0.42),
    rgba(5, 15, 26, 0.26)
  );
  backdrop-filter: blur(4px) saturate(115%);
  padding: clamp(14px, 2vw, 24px);
}

.blank-demo > header h2 {
  margin: 0;
  font-size: clamp(1rem, 1.3vw, 1.3rem);
  letter-spacing: 0.04em;
}

.blank-demo > header p {
  margin: 8px 0 0;
  color: #97b8ce;
  font-size: 0.88rem;
}

.blank-demo-grid {
  margin-top: 14px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.blank-demo-card {
  border: 1px solid rgba(95, 153, 177, 0.24);
  border-radius: var(--ui-radius);
  padding: 14px;
  background: rgba(8, 24, 37, 0.36);
}

.blank-demo-card h3 {
  margin: 0;
  font-size: 0.92rem;
}

.blank-demo-card p {
  margin: 8px 0 0;
  font-size: 0.82rem;
  color: #a4c3d8;
}

.blank-demo-stack {
  margin-top: 14px;
  display: grid;
  gap: 10px;
}

.blank-demo-strip {
  border: 1px solid rgba(95, 153, 177, 0.24);
  border-radius: var(--ui-radius);
  padding: 12px 14px;
  background: rgba(8, 24, 37, 0.28);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.blank-demo-strip strong {
  font-size: 0.88rem;
  font-weight: 600;
}

.blank-demo-strip span {
  color: #9ebcd1;
  font-size: 0.8rem;
  text-align: right;
}

@media (max-width: 900px) {
  .blank-demo-grid {
    grid-template-columns: 1fr;
  }

  .blank-demo-strip {
    flex-direction: column;
    align-items: flex-start;
  }

  .blank-demo-strip span {
    text-align: left;
  }
}
</style>
