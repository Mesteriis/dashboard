<template>
  <aside class="sidebar">
    <div id="sidebar-particles" class="sidebar-particles" aria-hidden="true"></div>

    <div class="sidebar-content">
      <SidebarHeaderTabs />
      <SidebarTreePanel v-if="isSidebarDetailed" />
      <SidebarIndicatorsAccordion v-if="isSidebarDetailed" />
    </div>
  </aside>
</template>

<script setup>
import SidebarHeaderTabs from '../components/sidebar/SidebarHeaderTabs.vue'
import SidebarIndicatorsAccordion from '../components/sidebar/SidebarIndicatorsAccordion.vue'
import SidebarTreePanel from '../components/sidebar/SidebarTreePanel.vue'
import { useDashboardStore } from '../stores/dashboardStore.js'

const dashboard = useDashboardStore()
const { isSidebarDetailed } = dashboard
</script>
