<template>
  <div class="shell" :class="{ 'shell-motion-static': disableHeroReenterMotion }">
    <img class="center-emblem" :src="EMBLEM_SRC" alt="" aria-hidden="true" />

    <div class="app-shell" :class="{ 'sidebar-sections': isSidebarSectionsOnly, 'sidebar-hidden': isSidebarHidden }">
      <DashboardSidebarView v-if="!isSidebarHidden" />
      <DashboardMainView />
    </div>

    <LanHostModal v-if="lanHostModal.open" />
    <IframeModal v-if="iframeModal.open" />
    <ItemEditorModal v-if="itemEditor.open" />
    <CommandPaletteModal v-if="commandPaletteOpen" />
  </div>
</template>

<script setup>
import { defineAsyncComponent, onBeforeUnmount, onMounted, ref } from 'vue'
import DashboardMainView from './views/DashboardMainView.vue'
import DashboardSidebarView from './views/DashboardSidebarView.vue'
import { useDashboardStore } from './stores/dashboardStore.js'

const LanHostModal = defineAsyncComponent(() => import('./components/modals/LanHostModal.vue'))
const IframeModal = defineAsyncComponent(() => import('./components/modals/IframeModal.vue'))
const ItemEditorModal = defineAsyncComponent(() => import('./components/modals/ItemEditorModal.vue'))
const CommandPaletteModal = defineAsyncComponent(() => import('./components/modals/CommandPaletteModal.vue'))

const dashboard = useDashboardStore()
const { EMBLEM_SRC, closeCommandPalette, commandPaletteOpen, iframeModal, isSidebarSectionsOnly, isSidebarHidden, itemEditor, lanHostModal, toggleCommandPalette } = dashboard
const disableHeroReenterMotion = ref(false)
let motionTimerId = 0

function handleGlobalShortcut(event) {
  const isShortcut = (event.metaKey || event.ctrlKey) && !event.altKey && !event.shiftKey && event.key.toLowerCase() === 'k'
  if (isShortcut) {
    event.preventDefault()
    toggleCommandPalette()
    return
  }

  if (event.key === 'Escape' && commandPaletteOpen.value) {
    event.preventDefault()
    closeCommandPalette()
  }
}

onMounted(() => {
  motionTimerId = globalThis.setTimeout(() => {
    disableHeroReenterMotion.value = true
  }, 1000)
  window.addEventListener('keydown', handleGlobalShortcut)
})

onBeforeUnmount(() => {
  if (motionTimerId) {
    globalThis.clearTimeout(motionTimerId)
    motionTimerId = 0
  }
  window.removeEventListener('keydown', handleGlobalShortcut)
})
</script>
