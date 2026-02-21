<template>
  <section v-if="treeGroups.length && isSidebarIconOnly" class="sidebar-icon-rail" aria-label="Иконки навигации">
    <button
      v-for="node in sidebarIconNodes"
      :key="node.key"
      class="sidebar-icon-btn"
      :class="{ active: isSidebarIconActive(node), group: node.type === 'group', subgroup: node.type === 'subgroup', item: node.type === 'item' }"
      type="button"
      :title="sidebarIconNodeTitle(node)"
      :aria-label="sidebarIconNodeTitle(node)"
      @click="selectSidebarIconNode(node)"
    >
      <img
        v-if="node.type === 'item' && itemFaviconSrc(node.item)"
        :src="itemFaviconSrc(node.item)"
        class="service-favicon sidebar-nav-favicon"
        alt=""
        loading="lazy"
        referrerpolicy="no-referrer"
        @error="markItemFaviconFailed(node.item)"
      />
      <component
        v-else
        :is="node.type === 'group' ? resolveGroupIcon(node.group) : node.type === 'subgroup' ? resolveSubgroupIcon(node.subgroup) : resolveItemIcon(node.item)"
        class="ui-icon sidebar-nav-icon"
      />
      <span v-if="node.type === 'item'" class="health-dot sidebar-icon-health" :class="healthClass(node.itemId)"></span>
    </button>
  </section>
</template>

<script setup>
import { useDashboardStore } from '../../stores/dashboardStore.js'

const dashboard = useDashboardStore()

const {
  treeGroups,
  isSidebarIconOnly,
  sidebarIconNodes,
  isSidebarIconActive,
  sidebarIconNodeTitle,
  selectSidebarIconNode,
  itemFaviconSrc,
  markItemFaviconFailed,
  resolveGroupIcon,
  resolveSubgroupIcon,
  resolveItemIcon,
  healthClass,
} = dashboard
</script>
