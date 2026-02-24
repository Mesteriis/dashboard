<template>
  <section
    v-if="treeGroups.length"
    class="sidebar-tree"
    aria-label="Дерево сервисов"
  >
    <ul
      v-if="filteredTreeGroups.length"
      v-auto-animate="treeAutoAnimateOptions"
      class="tree-root"
    >
      <SidebarTreeGroupNode
        v-for="group in filteredTreeGroups"
        :key="group.key"
        :group="group"
      />
    </ul>

    <p v-else class="tree-empty">По вашему запросу ничего не найдено.</p>
  </section>
</template>

<script setup lang="ts">
import { vAutoAnimate } from "@formkit/auto-animate/vue";
import { useDashboardStore } from "@/stores/dashboardStore";
import SidebarTreeGroupNode from "@/components/sidebar/SidebarTreeGroupNode.vue";

const dashboard = useDashboardStore();

const { treeGroups, filteredTreeGroups } = dashboard;

const treeAutoAnimateOptions = {
  duration: 160,
  easing: "cubic-bezier(0.22, 0.72, 0.14, 1)",
};
</script>
