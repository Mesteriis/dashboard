<template>
  <UiServicesHeroPanel :segment="segment" />
</template>

<script setup lang="ts">
import UiServicesHeroPanel from "@/views/dashboard/components/UiServicesHeroPanel.vue";

withDefaults(
  defineProps<{
    segment?:
      | "full"
      | "tabs"
      | "panel.drawer"
      | "panel.actions"
      | "panel.menu"
      | "panel.footer";
  }>(),
  {
    segment: "full",
  },
);
</script>
