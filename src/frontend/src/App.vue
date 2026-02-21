<template>
  <div class="shell" :class="{ 'shell-motion-static': disableHeroReenterMotion }">
    <img class="center-emblem" :src="EMBLEM_SRC" alt="" aria-hidden="true" />

    <div class="app-shell" :class="{ 'sidebar-hidden': isSidebarHidden }">
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

const loadLanHostModal = () => import('./components/modals/LanHostModal.vue')
const loadIframeModal = () => import('./components/modals/IframeModal.vue')
const loadItemEditorModal = () => import('./components/modals/ItemEditorModal.vue')
const loadCommandPaletteModal = () => import('./components/modals/CommandPaletteModal.vue')
const loadIndicatorTabPanel = () => import('./components/main/IndicatorTabPanel.vue')
const loadLanPageView = () => import('./components/main/LanPageView.vue')

const LanHostModal = defineAsyncComponent(loadLanHostModal)
const IframeModal = defineAsyncComponent(loadIframeModal)
const ItemEditorModal = defineAsyncComponent(loadItemEditorModal)
const CommandPaletteModal = defineAsyncComponent(loadCommandPaletteModal)

const dashboard = useDashboardStore()
const { EMBLEM_SRC, closeCommandPalette, commandPaletteOpen, iframeModal, isSidebarHidden, itemEditor, lanHostModal, toggleCommandPalette } = dashboard
const disableHeroReenterMotion = ref(false)
let motionTimerId = 0
let idlePrefetchTimerId = 0
let idlePrefetchCallbackId = 0

function runIdlePrefetch() {
  Promise.allSettled([
    loadLanHostModal(),
    loadIframeModal(),
    loadItemEditorModal(),
    loadCommandPaletteModal(),
    loadIndicatorTabPanel(),
    loadLanPageView(),
  ])
}

function scheduleIdlePrefetch() {
  if ('requestIdleCallback' in window) {
    idlePrefetchCallbackId = window.requestIdleCallback(
      () => {
        idlePrefetchCallbackId = 0
        runIdlePrefetch()
      },
      { timeout: 2000 },
    )
    return
  }

  idlePrefetchTimerId = window.setTimeout(() => {
    idlePrefetchTimerId = 0
    runIdlePrefetch()
  }, 1400)
}

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
  scheduleIdlePrefetch()
})

onBeforeUnmount(() => {
  if (motionTimerId) {
    globalThis.clearTimeout(motionTimerId)
    motionTimerId = 0
  }
  if (idlePrefetchTimerId) {
    window.clearTimeout(idlePrefetchTimerId)
    idlePrefetchTimerId = 0
  }
  if (idlePrefetchCallbackId && 'cancelIdleCallback' in window) {
    window.cancelIdleCallback(idlePrefetchCallbackId)
    idlePrefetchCallbackId = 0
  }
  window.removeEventListener('keydown', handleGlobalShortcut)
})
</script>
