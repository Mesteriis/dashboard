<template>
  <UiBootstrapDashboardModal
    :open="open"
    :creating="creating"
    :importing="importing"
    :error="error"
    @create="emit('create')"
    @import-yaml="(payload) => emit('importYaml', payload)"
  />
</template>

<script setup lang="ts">
import UiBootstrapDashboardModal from "@/views/dashboard/components/UiBootstrapDashboardModal.vue";

defineProps<{
  open: boolean;
  creating: boolean;
  importing: boolean;
  error: string;
}>();

const emit = defineEmits<{
  create: [];
  importYaml: [{ name: string; yaml: string }];
}>();
</script>
