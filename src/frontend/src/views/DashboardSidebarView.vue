<template>
  <aside class="sidebar" :class="{ compact: isSidebarIconOnly }">
    <div id="sidebar-particles" class="sidebar-particles" aria-hidden="true"></div>

    <div class="sidebar-content" :class="{ compact: isSidebarIconOnly }">
      <SidebarHeaderTabs />
      <SidebarTreePanel />
      <SidebarIconRail />
      <SidebarIndicatorsAccordion />
    </div>
  </aside>
</template>

<script setup>
import SidebarHeaderTabs from '../components/sidebar/SidebarHeaderTabs.vue'
import SidebarIconRail from '../components/sidebar/SidebarIconRail.vue'
import SidebarIndicatorsAccordion from '../components/sidebar/SidebarIndicatorsAccordion.vue'
import SidebarTreePanel from '../components/sidebar/SidebarTreePanel.vue'
import { useDashboardStore } from '../stores/dashboardStore.js'

const dashboard = useDashboardStore()
const { isSidebarIconOnly } = dashboard
</script>
