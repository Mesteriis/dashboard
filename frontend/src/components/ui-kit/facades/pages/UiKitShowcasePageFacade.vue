<template>
  <UiBlankLayout
    :emblem-src="EMBLEM_SRC"
    :sidebar-hidden="isSidebarHidden"
    :sidebar-particles-id="SIDEBAR_PARTICLES_ID"
    canvas-aria-label="UI Kit demo"
  >
    <template v-slot:[SLOT_APP_SIDEBAR_TOP]>
      <header class="brand">
        <img :src="EMBLEM_SRC" alt="" aria-hidden="true" />
        <div>
          <p class="brand-title">Oko</p>
          <p class="brand-subtitle">UI Kit primitives showcase</p>
        </div>
      </header>
    </template>

    <template v-slot:[SLOT_APP_HEADER_TABS]>
      <nav class="hero-page-tabs" role="tablist" aria-label="UI Kit">
        <button
          id="uikit-showcase-tab"
          class="hero-page-tab-btn active"
          type="button"
          role="tab"
          aria-selected="true"
          tabindex="0"
          aria-controls="uikit-showcase-panel"
        >
          <Palette class="ui-icon hero-page-tab-icon" />
          <span class="hero-page-tab-label">UI Kit Showcase</span>
        </button>
      </nav>
    </template>

    <template v-slot:[SLOT_PAGE_CANVAS_MAIN]>
      <section
        id="uikit-showcase-panel"
        role="tabpanel"
        aria-labelledby="uikit-showcase-tab"
      >
        <UiPrimitivesDemoView @close="emit('close')" />
      </section>
    </template>
  </UiBlankLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, watch } from "vue";
import { Palette } from "lucide-vue-next";
import UiBlankLayout from "@/components/ui-kit/primitives/UiBlankLayout.vue";
import UiPrimitivesDemoView from "@/views/UiPrimitivesDemoView.vue";
import { EMBLEM_SRC, SIDEBAR_PARTICLES_ID } from "@/stores/ui/storeConstants";
import { useUiStore } from "@/stores/uiStore";

const SLOT_APP_SIDEBAR_TOP = "app.sidebar.top";
const SLOT_APP_HEADER_TABS = "app.header.tabs";
const SLOT_PAGE_CANVAS_MAIN = "page.canvas.main";

const emit = defineEmits<{
  close: [];
}>();

const uiStore = useUiStore();
const { initSidebarParticles } = uiStore;
const isSidebarHidden = computed(() => uiStore.sidebarView.value === "hidden");

onMounted(() => {
  void initSidebarParticles();
});

watch(
  () => isSidebarHidden.value,
  (hidden) => {
    if (hidden) return;
    void initSidebarParticles();
  },
);
</script>
