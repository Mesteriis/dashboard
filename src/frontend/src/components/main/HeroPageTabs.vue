<template>
  <nav class="hero-page-tabs" :class="{ 'hero-page-tabs--intro': shouldPlayIntro }" role="tablist" aria-label="Разделы">
    <button
      v-for="page in pages"
      :key="page.id"
      class="hero-page-tab-btn"
      :class="{
        active: activePage?.id === page.id,
        'hero-page-tab-btn--intro-active': shouldPlayIntro && activePage?.id === page.id,
      }"
      type="button"
      role="tab"
      :title="page.title"
      :aria-label="page.title"
      :aria-selected="activePage?.id === page.id"
      @click="activePageId = page.id"
    >
      <component :is="resolvePageIcon(page)" class="ui-icon hero-page-tab-icon" />
      <span class="hero-page-tab-label">{{ page.title }}</span>
    </button>
  </nav>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useDashboardStore } from '../../stores/dashboardStore.js'

let hasPlayedHeroTabsIntro = false

const dashboard = useDashboardStore()
const { pages, activePage, activePageId, resolvePageIcon } = dashboard
const shouldPlayIntro = ref(!hasPlayedHeroTabsIntro)
let introTimeoutId = 0

onMounted(() => {
  if (!shouldPlayIntro.value) return

  introTimeoutId = globalThis.setTimeout(() => {
    shouldPlayIntro.value = false
    hasPlayedHeroTabsIntro = true
  }, 700)
})

onBeforeUnmount(() => {
  if (introTimeoutId) {
    globalThis.clearTimeout(introTimeoutId)
    introTimeoutId = 0
  }
  if (shouldPlayIntro.value) {
    hasPlayedHeroTabsIntro = true
  }
})
</script>
