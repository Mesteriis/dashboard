<template>
  <section v-if="treeGroups.length" class="sidebar-tree" aria-label="Дерево сервисов">
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
  filteredTreeGroups,
} = dashboard
</script>
