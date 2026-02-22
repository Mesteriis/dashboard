<template>
  <div class="brand">
    <img :src="EMBLEM_SRC" alt="Oko" />
    <div>
      <p class="brand-title">{{ appTitle }}</p>
      <p class="brand-subtitle">{{ appTagline }}</p>
    </div>
  </div>
</template>

<script setup>
import { useDashboardStore } from "../../stores/dashboardStore.js";

const dashboard = useDashboardStore();
const { EMBLEM_SRC, appTitle, appTagline } = dashboard;
</script>
