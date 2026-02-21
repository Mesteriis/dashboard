<template>
  <section class="page-stack">
    <section v-for="(block, index) in activePageGroupBlocks" :key="`${activePage.id}:${index}:groups`" class="block-wrap">
      <section class="groups-grid">
        <ServiceGroupCard v-for="group in filteredBlockGroups(block.group_ids)" :key="group.key" :group="group" />

        <article v-if="!filteredBlockGroups(block.group_ids).length" class="panel group-panel group-empty">
          <h2>Нет данных для выбранного узла</h2>
          <p class="subtitle">Выберите другую ветку в боковом дереве.</p>
        </article>
      </section>
    </section>

    <article v-if="!activePageGroupBlocks.length" class="panel group-panel group-empty">
      <h2>Для этой страницы нет групп</h2>
      <p class="subtitle">Откройте нужный индикатор в аккордеоне слева.</p>
    </article>
  </section>
</template>

<script setup>
import ServiceGroupCard from './ServiceGroupCard.vue'
import { useDashboardStore } from '../../stores/dashboardStore.js'

const dashboard = useDashboardStore()
const { activePage, activePageGroupBlocks, filteredBlockGroups } = dashboard
</script>
