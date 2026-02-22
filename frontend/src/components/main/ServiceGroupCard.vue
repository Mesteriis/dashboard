<template>
  <article
    class="panel group-panel"
    :class="{ 'group-panel-inline': isInlineGroupLayout(group) }"
  >
    <header class="group-header">
      <div class="group-title-row">
        <component :is="resolveGroupIcon(group)" class="ui-icon group-icon" />
        <h2>{{ group.title }}</h2>
      </div>
      <p v-if="group.description" class="subtitle">{{ group.description }}</p>
    </header>

    <section
      v-for="subgroup in group.subgroups"
      :key="subgroup.id"
      class="subgroup"
    >
      <h3 class="subgroup-title">
        <component
          :is="resolveSubgroupIcon(subgroup)"
          class="ui-icon subgroup-icon"
        />
        <span>{{ subgroup.title }}</span>
      </h3>

      <VirtualizedItemGrid
        :items="subgroup.items"
        :group-key="group.key"
        :subgroup-id="subgroup.id"
      />
    </section>
  </article>
</template>

<script setup>
import VirtualizedItemGrid from "./VirtualizedItemGrid.vue";
import { useDashboardStore } from "../../stores/dashboardStore.js";

defineProps({
  group: {
    type: Object,
    required: true,
  },
});

const dashboard = useDashboardStore();
const { isInlineGroupLayout, resolveGroupIcon, resolveSubgroupIcon } =
  dashboard;
</script>
