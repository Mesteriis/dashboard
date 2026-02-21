<template>
  <section v-if="treeGroups.length && !isSidebarIconOnly" class="sidebar-tree" aria-label="Дерево сервисов">
    <div class="tree-topline">
      <p class="sidebar-tree-title">Навигация</p>
      <span class="tree-page-chip">{{ activePage?.title }}</span>
    </div>

    <label class="tree-search">
      <input v-model="treeFilter" type="search" placeholder="Поиск сервиса..." autocomplete="off" spellcheck="false" />
    </label>

    <div class="tree-root-page">
      <div class="tree-root-main">
        <component :is="resolvePageIcon(activePage)" class="ui-icon root-icon" />
        <div>
          <p class="tree-root-title">{{ activePage?.title }}</p>
          <p class="tree-root-subtitle">{{ activePage?.id }}</p>
        </div>
      </div>
      <span class="tree-root-meta">{{ pageHealthSummary.online }}/{{ pageHealthSummary.total }}</span>
    </div>

    <ul v-if="filteredTreeGroups.length" class="tree-root">
      <SidebarTreeGroupNode v-for="group in filteredTreeGroups" :key="group.key" :group="group" />
    </ul>

    <p v-else class="tree-empty">По вашему запросу ничего не найдено.</p>
  </section>
</template>

<script setup>
import { useDashboardStore } from '../../stores/dashboardStore.js'
import SidebarTreeGroupNode from './SidebarTreeGroupNode.vue'

const dashboard = useDashboardStore()

const {
  treeGroups,
  isSidebarIconOnly,
  activePage,
  treeFilter,
  resolvePageIcon,
  pageHealthSummary,
  filteredTreeGroups,
} = dashboard
</script>
