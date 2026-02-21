<template>
  <article class="panel group-panel" :class="{ 'group-panel-inline': isInlineGroupLayout(group) }">
    <header class="group-header">
      <div class="group-title-row">
        <component :is="resolveGroupIcon(group)" class="ui-icon group-icon" />
        <h2>{{ group.title }}</h2>
      </div>
      <p v-if="group.description" class="subtitle">{{ group.description }}</p>
    </header>

    <section v-for="subgroup in group.subgroups" :key="subgroup.id" class="subgroup">
      <h3 class="subgroup-title">
        <component :is="resolveSubgroupIcon(subgroup)" class="ui-icon subgroup-icon" />
        <span>{{ subgroup.title }}</span>
      </h3>

      <TransitionGroup
        name="item-grid-transition"
        tag="div"
        class="item-grid"
        :class="{ 'icon-card-grid': isIconCardView, 'tile-card-grid': isTileCardView }"
      >
        <ServiceItemCard
          v-for="item in subgroup.items"
          :key="item.id"
          :group-key="item.__originGroupKey || group.key"
          :subgroup-id="item.__originSubgroupId || subgroup.id"
          :item="item"
        />
      </TransitionGroup>
    </section>
  </article>
</template>

<script setup>
import ServiceItemCard from './ServiceItemCard.vue'
import { useDashboardStore } from '../../stores/dashboardStore.js'

defineProps({
  group: {
    type: Object,
    required: true,
  },
})

const dashboard = useDashboardStore()
const { isInlineGroupLayout, resolveGroupIcon, resolveSubgroupIcon, isIconCardView, isTileCardView } = dashboard
</script>
