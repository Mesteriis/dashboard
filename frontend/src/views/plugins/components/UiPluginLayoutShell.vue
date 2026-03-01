<template>
  <section class="plugin-layout-shell" :class="layoutClass">
    <aside v-if="hasSidebar" class="plugin-layout-sidebar panel">
      <slot name="sidebar">
        <p class="plugin-layout-sidebar-placeholder">Sidebar</p>
      </slot>
    </aside>
    <main class="plugin-layout-main">
      <slot />
    </main>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { PluginLayoutType } from "@/features/plugins/manifest";

const props = defineProps<{
  layout: PluginLayoutType;
}>();

const hasSidebar = computed(
  () => props.layout === "with-sidebar" || props.layout === "split-view",
);
const layoutClass = computed(() => `layout-${props.layout}`);
</script>

<style scoped>
.plugin-layout-shell {
  display: grid;
  gap: 12px;
}

.layout-content-only,
.layout-dashboard {
  grid-template-columns: minmax(0, 1fr);
}

.layout-with-sidebar {
  grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);
}

.layout-split-view {
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
}

.plugin-layout-sidebar,
.plugin-layout-main {
  min-width: 0;
  min-height: 0;
}

.plugin-layout-sidebar {
  padding: 14px;
}

.plugin-layout-main {
  padding: 0;
}

.plugin-layout-sidebar-placeholder {
  margin: 0;
  color: rgba(181, 201, 223, 0.82);
}

@media (max-width: 980px) {
  .layout-with-sidebar,
  .layout-split-view {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
