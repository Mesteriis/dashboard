<template>
  <DashboardShellView />
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted } from "vue";
import { useUiStore } from "@/stores/uiStore";
import DashboardShellView from "@/views/DashboardShellView.vue";

const uiStore = useUiStore();
const { closeSettingsPanel, openSettingsPanel } = uiStore;

onMounted(() => {
  openSettingsPanel();
});

onBeforeUnmount(() => {
  closeSettingsPanel();
});
</script>
