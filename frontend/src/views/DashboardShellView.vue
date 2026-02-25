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
import UiDashboardMainViewFacade from "@/components/ui-kit/facades/dashboard/UiDashboardMainViewFacade.vue";
import UiServicesHeroPanelFacade from "@/components/ui-kit/facades/dashboard/UiServicesHeroPanelFacade.vue";
import UiSidebarHeaderTabsFacade from "@/components/ui-kit/facades/dashboard/UiSidebarHeaderTabsFacade.vue";
import UiSidebarIndicatorsAccordionFacade from "@/components/ui-kit/facades/dashboard/UiSidebarIndicatorsAccordionFacade.vue";
import UiSidebarTreePanelFacade from "@/components/ui-kit/facades/dashboard/UiSidebarTreePanelFacade.vue";
import UiBlankLayout from "@/components/ui-kit/primitives/UiBlankLayout.vue";
import { EMBLEM_SRC, SIDEBAR_PARTICLES_ID } from "@/stores/ui/storeConstants";
import { useUiStore } from "@/stores/uiStore";

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
