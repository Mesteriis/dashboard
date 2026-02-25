<template>
  <UiPluginPageRenderer
    :plugin-id="pluginId"
    :manifest="manifest"
    @back="emit('back')"
  />
</template>

<script setup lang="ts">
import UiPluginPageRenderer from "@/views/plugins/components/UiPluginPageRenderer.vue";
import type { PluginManifest } from "@/features/plugins/manifest";

defineProps<{
  pluginId: string;
  manifest: PluginManifest;
}>();

const emit = defineEmits<{
  back: [];
}>();
</script>
