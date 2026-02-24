<template>
  <div class="app-shell" :class="{ 'sidebar-hidden': isSidebarHidden }">
    <DashboardSidebarView v-if="!isSidebarHidden" />
    <DashboardMainView />
  </div>

  <IframeModal v-if="iframeModal.open" />
  <ItemEditorModal v-if="itemEditor.open" />
  <CreateEntityChooserModal v-if="createChooser.open" />
  <CreateEntityModal v-if="createEntityEditor.open" />
  <DashboardSettingsModal v-if="settingsPanel.open" />
  <CommandPaletteModal v-if="commandPaletteOpen" />
</template>

<script setup lang="ts">
import { defineAsyncComponent } from "vue";
import DashboardMainView from "@/views/DashboardMainView.vue";
import DashboardSidebarView from "@/views/DashboardSidebarView.vue";
import { useDashboardStore } from "@/stores/dashboardStore";

const IframeModal = defineAsyncComponent(
  () => import("@/components/modals/IframeModal.vue"),
);
const ItemEditorModal = defineAsyncComponent(
  () => import("@/components/modals/ItemEditorModal.vue"),
);
const CreateEntityChooserModal = defineAsyncComponent(
  () => import("@/components/modals/CreateEntityChooserModal.vue"),
);
const CreateEntityModal = defineAsyncComponent(
  () => import("@/components/modals/CreateEntityModal.vue"),
);
const DashboardSettingsModal = defineAsyncComponent(
  () => import("@/components/modals/DashboardSettingsModal.vue"),
);
const CommandPaletteModal = defineAsyncComponent(
  () => import("@/components/modals/CommandPaletteModal.vue"),
);

const dashboard = useDashboardStore();
const {
  commandPaletteOpen,
  createChooser,
  createEntityEditor,
  iframeModal,
  isSidebarHidden,
  itemEditor,
  settingsPanel,
} = dashboard;
</script>
