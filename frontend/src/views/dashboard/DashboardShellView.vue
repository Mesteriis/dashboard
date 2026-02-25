<template>
  <UiBlankLayout
    :emblem-src="EMBLEM_SRC"
    :sidebar-hidden="isSidebarHidden"
    :sidebar-particles-id="SIDEBAR_PARTICLES_ID"
    sidebar-bottom-accordion-label="Индикаторы"
    :sidebar-bottom-visible="isSidebarDetailed"
    canvas-aria-label="Dashboard content"
  >
    <template v-slot:[SLOT_APP_SIDEBAR_TOP]>
      <UiSidebarHeaderTabsFacade />
    </template>

    <template v-slot:[SLOT_APP_SIDEBAR_MIDDLE]>
      <UiSidebarTreePanelFacade v-if="isSidebarDetailed" />
    </template>

    <template v-slot:[SLOT_APP_SIDEBAR_BOTTOM]>
      <UiSidebarIndicatorsAccordionFacade v-if="isSidebarDetailed" />
    </template>

    <template v-slot:[SLOT_APP_HEADER_TABS]>
      <UiServicesHeroPanelFacade />
    </template>

    <template v-slot:[SLOT_PAGE_CANVAS_MAIN]>
      <UiDashboardMainViewFacade />
    </template>

    <template v-slot:[SLOT_APP_MODALS]>
      <IframeModal v-if="iframeModal.open" />
      <ItemEditorModal v-if="itemEditor.open" />
      <CreateEntityChooserModal v-if="createChooser.open" />
      <CreateEntityModal v-if="createEntityEditor.open" />
      <DashboardSettingsModal v-if="settingsPanel.open" />
    </template>

    <template v-slot:[SLOT_APP_COMMAND_PALETTE]>
      <CommandPaletteModal v-if="commandPaletteOpen" />
    </template>
  </UiBlankLayout>
</template>

<script setup lang="ts">
import { defineAsyncComponent } from "vue";
import UiDashboardMainViewFacade from "@/views/dashboard/facades/UiDashboardMainViewFacade.vue";
import UiServicesHeroPanelFacade from "@/views/dashboard/facades/UiServicesHeroPanelFacade.vue";
import UiSidebarHeaderTabsFacade from "@/views/dashboard/facades/UiSidebarHeaderTabsFacade.vue";
import UiSidebarIndicatorsAccordionFacade from "@/views/dashboard/facades/UiSidebarIndicatorsAccordionFacade.vue";
import UiSidebarTreePanelFacade from "@/views/dashboard/facades/UiSidebarTreePanelFacade.vue";
import UiBlankLayout from "@/components/layout/UiBlankLayout.vue";
import { EMBLEM_SRC, SIDEBAR_PARTICLES_ID } from "@/features/stores/ui/storeConstants";
import { useUiStore } from "@/features/stores/uiStore";

const IframeModal = defineAsyncComponent(
  () => import("@/views/dashboard/modals/IframeModal.vue"),
);
const ItemEditorModal = defineAsyncComponent(
  () => import("@/views/dashboard/modals/ItemEditorModal.vue"),
);
const CreateEntityChooserModal = defineAsyncComponent(
  () => import("@/views/dashboard/modals/CreateEntityChooserModal.vue"),
);
const CreateEntityModal = defineAsyncComponent(
  () => import("@/views/dashboard/modals/CreateEntityModal.vue"),
);
const DashboardSettingsModal = defineAsyncComponent(
  () => import("@/views/dashboard/modals/DashboardSettingsModal.vue"),
);
const CommandPaletteModal = defineAsyncComponent(
  () => import("@/views/dashboard/modals/CommandPaletteModal.vue"),
);

const SLOT_APP_SIDEBAR_TOP = "app.sidebar.top";
const SLOT_APP_SIDEBAR_MIDDLE = "app.sidebar.middle";
const SLOT_APP_SIDEBAR_BOTTOM = "app.sidebar.bottom";
const SLOT_APP_HEADER_TABS = "app.header.tabs";
const SLOT_PAGE_CANVAS_MAIN = "page.canvas.main";
const SLOT_APP_MODALS = "app.modals";
const SLOT_APP_COMMAND_PALETTE = "app.command_palette";
const dashboard = useUiStore();
const {
  commandPaletteOpen,
  createChooser,
  createEntityEditor,
  iframeModal,
  isSidebarDetailed,
  isSidebarHidden,
  itemEditor,
  settingsPanel,
} = dashboard;
</script>
