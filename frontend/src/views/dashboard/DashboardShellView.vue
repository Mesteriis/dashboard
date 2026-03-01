<template>
  <UiBlankLayout
    :emblem-src="EMBLEM_SRC"
    :sidebar-hidden="isSidebarHidden"
    :sidebar-particles-id="SIDEBAR_PARTICLES_ID"
    :header-panel-active="editMode"
    content-label="Dashboard content"
    @logout="handleLogout"
  >
    <template #sidebar-mid>
      <UiSidebarTreePanel v-if="isSidebarDetailed" />
    </template>

    <template #sidebar-bottom-indicators>
      <UiSidebarIndicatorsAccordion v-if="isSidebarDetailed" />
    </template>

    <template #header-tabs>
      <UiServicesHeroPanel segment="tabs" />
    </template>

    <template #drawer>
      <UiServicesHeroPanel segment="panel.drawer" />
    </template>

    <template #drawer-footer>
      <UiServicesHeroPanel segment="panel.footer" />
    </template>

    <template #canvas-main>
      <DashboardMainView hide-hero />
    </template>
  </UiBlankLayout>
</template>

<script setup lang="ts">
import DashboardMainView from "@/views/dashboard/DashboardMainView.vue";
import UiServicesHeroPanel from "@/views/dashboard/components/UiServicesHeroPanel.vue";
import UiSidebarIndicatorsAccordion from "@/views/dashboard/components/UiSidebarIndicatorsAccordion.vue";
import UiSidebarTreePanel from "@/views/dashboard/components/UiSidebarTreePanel.vue";
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
  // eslint-disable-next-line no-console
  console.log("Logout requested");
}
</script>
