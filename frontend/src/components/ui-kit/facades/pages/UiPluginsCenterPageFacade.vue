<template>
  <UiPluginControlCenterCore
    :tab="tab"
    @close="emit('close')"
    @set-tab="(value) => emit('setTab', value)"
    @open-plugin="(pluginId) => emit('openPlugin', pluginId)"
  />
</template>

<script setup lang="ts">
import UiPluginControlCenterCore from "@/components/ui-kit/facades/plugins/UiPluginControlCenterCore.vue";

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
