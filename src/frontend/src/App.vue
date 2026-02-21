<template>
  <div class="shell">
    <img class="center-emblem" :src="EMBLEM_SRC" alt="" aria-hidden="true" />

    <div class="app-shell" :class="{ 'sidebar-compact': isSidebarIconOnly }">
      <DashboardSidebarView />
      <DashboardMainView />
    </div>

    <LanHostModal />
    <IframeModal />
    <ItemEditorModal />
  </div>
</template>

<script setup>
import IframeModal from './components/modals/IframeModal.vue'
import ItemEditorModal from './components/modals/ItemEditorModal.vue'
import LanHostModal from './components/modals/LanHostModal.vue'
import DashboardMainView from './views/DashboardMainView.vue'
import DashboardSidebarView from './views/DashboardSidebarView.vue'
import { useDashboardStore } from './stores/dashboardStore.js'

const dashboard = useDashboardStore()
const { EMBLEM_SRC, isSidebarIconOnly } = dashboard
</script>
