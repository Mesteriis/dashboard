<template>
  <main
    class="app-shell blank-page"
    :class="{ 'sidebar-hidden': sidebarHidden }"
    :data-layout-api-version="layoutApiVersion"
  >
    <slot name="app.shell.background" />

    <aside v-if="!sidebarHidden" class="sidebar blank-sidebar">
      <div
        v-if="sidebarParticlesId"
        :id="sidebarParticlesId"
        class="sidebar-particles"
        aria-hidden="true"
      ></div>

      <div class="sidebar-content">
        <section class="blank-sidebar-top">
          <slot name="app.sidebar.top" />
        </section>
        <section class="blank-sidebar-middle">
          <slot name="app.sidebar.middle" />
        </section>
        <section class="blank-sidebar-bottom">
          <slot name="app.sidebar.bottom" />
        </section>
      </div>
    </aside>

    <section class="blank-main">
      <UiHeroGlassTabsShell :emblem-src="emblemSrc">
        <div class="blank-header-main">
          <div v-if="hasHeaderLeft" class="blank-header-left">
            <slot name="app.header.left" />
          </div>
          <div class="blank-header-tabs">
            <slot name="app.header.tabs" />
          </div>
        </div>

        <template #actions>
          <slot name="app.header.actions" />
        </template>
      </UiHeroGlassTabsShell>

      <section class="blank-canvas" :aria-label="canvasAriaLabel">
        <section class="blank-canvas-top">
          <slot name="page.canvas.top" />
        </section>
        <section class="blank-canvas-main">
          <slot name="page.canvas.main" />
        </section>
        <section class="blank-canvas-bottom">
          <slot name="page.canvas.bottom" />
        </section>
      </section>
    </section>

    <slot name="app.notifications" />
    <slot name="app.modals" />
    <slot name="app.command_palette" />

    <slot
      name="entity.card.actions"
      :context-object="entityContextObject"
      :required-capabilities="entityRequiredCapabilities"
    />
    <slot name="entity.card.badges" />
    <slot
      name="entity.card.inline"
      :context-object="entityContextObject"
      :required-capabilities="entityRequiredCapabilities"
    />
  </main>
</template>

<script setup lang="ts">
import { computed, useSlots } from "vue";
import UiHeroGlassTabsShell from "@/components/ui-kit/primitives/UiHeroGlassTabsShell.vue";

withDefaults(
  defineProps<{
    emblemSrc: string;
    sidebarHidden?: boolean;
    sidebarParticlesId?: string;
    canvasAriaLabel?: string;
    layoutApiVersion?: "v1";
    entityContextObject?: Record<string, unknown> | null;
    entityRequiredCapabilities?: string[];
  }>(),
  {
    sidebarHidden: false,
    sidebarParticlesId: "",
    canvasAriaLabel: "Blank page",
    layoutApiVersion: "v1",
    entityContextObject: null,
    entityRequiredCapabilities: () => ["read.entity"],
  },
);

const slots = useSlots();
const hasHeaderLeft = computed(() => Boolean(slots["app.header.left"]));
</script>

<style scoped>
.blank-page {
  grid-template-columns: 420px minmax(0, 1fr);
}

.blank-page.sidebar-hidden {
  grid-template-columns: minmax(0, 1fr);
}

.blank-main {
  position: relative;
  isolation: isolate;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 10px;
  overflow: visible;
}

.blank-main :deep(.hero-glass-tabs-shell) {
  position: relative;
  z-index: 40;
  overflow: visible;
}

.blank-main :deep(.hero-layout) {
  position: relative;
  z-index: 50;
}

.blank-main :deep(.hero-action-menu) {
  z-index: 240;
}

.blank-main :deep(.hero-control-panel--menu .ui-menu__list) {
  z-index: 280;
}

.blank-header-main {
  display: contents;
}

.blank-header-left,
.blank-header-tabs {
  display: contents;
}

.blank-canvas {
  position: relative;
  z-index: 1;
  border: 1px solid rgba(89, 144, 166, 0.18);
  border-radius: var(--ui-radius);
  background: transparent;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
  padding: clamp(14px, 2vw, 24px);
  overflow: hidden;
  display: grid;
  align-content: start;
  gap: 10px;
}

.blank-canvas-top,
.blank-canvas-main,
.blank-canvas-bottom {
  min-width: 0;
  min-height: 0;
}
</style>
