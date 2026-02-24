<template>
  <UiKitShowcasePageFacade @close="handleClose" />
</template>

<script setup lang="ts">
import UiKitShowcasePageFacade from "@/components/ui-kit/facades/pages/UiKitShowcasePageFacade.vue";
import { goDashboard } from "@/core/navigation/nav";

function handleClose(): void {
  void goDashboard();
}
</script>
