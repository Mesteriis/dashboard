<template>
  <UiBlankLayout
    :emblem-src="EMBLEM_SRC"
    :sidebar-hidden="isSidebarHidden"
    :sidebar-particles-id="SIDEBAR_PARTICLES_ID"
    :header-panel-active="editMode"
    canvas-aria-label="Dashboard content"
    @logout="handleLogout"
  >
    <template #sidebar-mid>
      <UiSidebarTreePanelFacade v-if="isSidebarDetailed" />
    </template>

    <template #sidebar-bottom-indicators>
      <UiSidebarIndicatorsAccordionFacade v-if="isSidebarDetailed" />
    </template>

    <template #header-tabs>
      <UiServicesHeroPanelFacade segment="tabs" />
    </template>

    <template #drawer>
      <UiServicesHeroPanelFacade segment="panel.drawer" />
    </template>

    <template #drawer-footer>
      <UiServicesHeroPanelFacade segment="panel.footer" />
    </template>

    <template #canvas-main>
      <UiDashboardMainViewFacade />
    </template>
  </UiBlankLayout>
</template>

<script setup lang="ts">
import UiDashboardMainViewFacade from "@/views/dashboard/facades/UiDashboardMainViewFacade.vue";
import UiServicesHeroPanelFacade from "@/views/dashboard/facades/UiServicesHeroPanelFacade.vue";
import UiSidebarIndicatorsAccordionFacade from "@/views/dashboard/facades/UiSidebarIndicatorsAccordionFacade.vue";
import UiSidebarTreePanelFacade from "@/views/dashboard/facades/UiSidebarTreePanelFacade.vue";
import UiBlankLayout from "@/components/layout/UiBlankLayout.vue";
import {
  EMBLEM_SRC,
  SIDEBAR_PARTICLES_CONFIG,
  SIDEBAR_PARTICLES_ID,
} from "@/features/stores/ui/storeConstants";
import { useUiStore } from "@/features/stores/uiStore";
import { useSidebarParticles } from "@/features/composables/useSidebarParticles";

const dashboard = useUiStore();
const { editMode, isSidebarDetailed, isSidebarHidden } = dashboard;

useSidebarParticles({
  containerId: SIDEBAR_PARTICLES_ID,
  baseConfig: SIDEBAR_PARTICLES_CONFIG,
  isSidebarHidden,
});

function handleLogout(): void {
  // TODO: Implement logout logic
  // eslint-disable-next-line no-console
  console.log("Logout requested");
}
</script>
