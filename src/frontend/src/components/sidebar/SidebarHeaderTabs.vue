<template>
  <div class="brand">
    <div>
      <p class="brand-title">{{ appTitle }}</p>
      <p class="brand-subtitle">{{ appTagline }}</p>
    </div>
  </div>
</template>

<script setup>
import { useDashboardStore } from '../../stores/dashboardStore.js'

const dashboard = useDashboardStore()
const { appTitle, appTagline } = dashboard
</script>
