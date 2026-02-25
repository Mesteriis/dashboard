<template>
  <UiPluginControlCenter
    :tab="tab"
    @close="emit('close')"
    @set-tab="(value) => emit('setTab', value)"
    @open-plugin="(pluginId) => emit('openPlugin', pluginId)"
  />
</template>

<script setup lang="ts">
import UiPluginControlCenter from "@/views/plugins/components/UiPluginControlCenter.vue";

type PluginsPanelTab = "installed" | "settings" | "store";

defineProps<{
  tab: PluginsPanelTab;
}>();

const emit = defineEmits<{
  close: [];
  setTab: [tab: PluginsPanelTab];
  openPlugin: [pluginId: string];
}>();
</script>
