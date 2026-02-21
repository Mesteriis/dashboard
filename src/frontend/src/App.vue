<template>
  <div class="shell" :class="{ 'shell-motion-static': disableHeroReenterMotion }">
    <img class="center-emblem" :src="EMBLEM_SRC" alt="" aria-hidden="true" />

    <div class="app-shell" :class="{ 'sidebar-sections': isSidebarSectionsOnly, 'sidebar-hidden': isSidebarHidden }">
      <DashboardSidebarView v-if="!isSidebarHidden" />
      <DashboardMainView />
    </div>

    <LanHostModal />
    <IframeModal />
    <ItemEditorModal />
    <CommandPaletteModal />
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import CommandPaletteModal from './components/modals/CommandPaletteModal.vue'
import IframeModal from './components/modals/IframeModal.vue'
import ItemEditorModal from './components/modals/ItemEditorModal.vue'
import LanHostModal from './components/modals/LanHostModal.vue'
import DashboardMainView from './views/DashboardMainView.vue'
import DashboardSidebarView from './views/DashboardSidebarView.vue'
import { useDashboardStore } from './stores/dashboardStore.js'

const dashboard = useDashboardStore()
const { EMBLEM_SRC, isSidebarSectionsOnly, isSidebarHidden } = dashboard
const disableHeroReenterMotion = ref(false)
let motionTimerId = 0

onMounted(() => {
  motionTimerId = globalThis.setTimeout(() => {
    disableHeroReenterMotion.value = true
  }, 1000)
})

onBeforeUnmount(() => {
  if (motionTimerId) {
    globalThis.clearTimeout(motionTimerId)
    motionTimerId = 0
  }
})
</script>
