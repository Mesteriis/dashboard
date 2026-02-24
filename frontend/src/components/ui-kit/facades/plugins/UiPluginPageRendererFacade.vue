<template>
  <UiPluginPageRenderer
    :plugin-id="pluginId"
    :manifest="manifest"
    @back="emit('back')"
  />
</template>

<script setup lang="ts">
import UiPluginPageRenderer from "@/components/ui-kit/composites/plugins/UiPluginPageRenderer.vue";
import type { PluginManifest } from "@/core/plugins/manifest";

defineProps<{
  pluginId: string;
  manifest: PluginManifest;
}>();

const emit = defineEmits<{
  back: [];
}>();
</script>
