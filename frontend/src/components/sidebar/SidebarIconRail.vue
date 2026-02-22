<template>
  <section
    v-if="treeGroups.length && isSidebarIconOnly"
    class="sidebar-icon-rail"
    aria-label="Иконки навигации"
  >
    <button
      v-for="node in sidebarIconNodes"
      :key="node.key"
      class="sidebar-icon-btn"
      :class="{
        active: isSidebarIconActive(node),
        group: node.type === 'group',
        subgroup: node.type === 'subgroup',
      }"
      type="button"
      :title="sidebarIconNodeTitle(node)"
      :aria-label="sidebarIconNodeTitle(node)"
      @click="selectSidebarIconNode(node)"
    >
      <component
        :is="
          node.type === 'group'
            ? resolveGroupIcon(node.group)
            : resolveSubgroupIcon(node.subgroup)
        "
        class="ui-icon sidebar-nav-icon"
      />
    </button>
  </section>
</template>

<script setup>
import { useDashboardStore } from "../../stores/dashboardStore.js";

const dashboard = useDashboardStore();

const {
  treeGroups,
  isSidebarIconOnly,
  sidebarIconNodes,
  isSidebarIconActive,
  sidebarIconNodeTitle,
  selectSidebarIconNode,
  resolveGroupIcon,
  resolveSubgroupIcon,
} = dashboard;
</script>
