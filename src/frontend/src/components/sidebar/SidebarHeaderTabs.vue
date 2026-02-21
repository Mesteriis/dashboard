<template>
  <div class="brand" :class="{ compact: isSidebarIconOnly }">
    <img :src="EMBLEM_SRC" alt="Oko" />
    <div v-if="!isSidebarIconOnly">
      <p class="brand-title">{{ appTitle }}</p>
      <p class="brand-subtitle">{{ appTagline }}</p>
    </div>
  </div>

  <nav class="tab-list" :class="{ compact: isSidebarIconOnly }" role="tablist" aria-label="Разделы">
    <button
      v-for="page in pages"
      :key="page.id"
      class="tab-btn"
      :class="{ active: activePage?.id === page.id, compact: isSidebarIconOnly }"
      type="button"
      role="tab"
      :title="page.title"
      :aria-label="page.title"
      :aria-selected="activePage?.id === page.id"
      @click="activePageId = page.id"
    >
      <component :is="resolvePageIcon(page)" class="ui-icon tab-tile-icon" />
      <span class="tab-tile-label">{{ page.title }}</span>
    </button>
  </nav>
</template>

<script setup>
import { useDashboardStore } from '../../stores/dashboardStore.js'

const dashboard = useDashboardStore()
const { EMBLEM_SRC, isSidebarIconOnly, appTitle, appTagline, pages, activePage, activePageId, resolvePageIcon } = dashboard
</script>
