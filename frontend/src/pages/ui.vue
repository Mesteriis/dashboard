<template>
  <UiPrimitivesDemoView @close="handleClose" />
</template>

<script setup lang="ts">
import UiPrimitivesDemoView from "@/views/UiPrimitivesDemoView.vue";
import { goDashboard } from "@/core/navigation/nav";

function handleClose(): void {
  void goDashboard();
}
</script>
