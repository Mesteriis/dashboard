<template>
  <DashboardShellView />
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted } from "vue";
import DashboardShellView from "@/views/DashboardShellView.vue";
import { useDashboardStore } from "@/stores/dashboardStore";

const dashboard = useDashboardStore();
const { closeSettingsPanel, openSettingsPanel } = dashboard;

onMounted(() => {
  openSettingsPanel();
});

onBeforeUnmount(() => {
  closeSettingsPanel();
});
</script>
