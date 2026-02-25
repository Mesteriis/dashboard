<template>
  <UiPluginControlCenterCore
    :tab="activeTab"
    @close="handleClose"
    @set-tab="handleSetTab"
    @open-plugin="handleOpenPlugin"
  />
</template>

<script setup lang="ts">
import { computed, watch } from "vue";
import { useRoute } from "vue-router";
import UiPluginControlCenterCore from "@/components/ui-kit/facades/plugins/UiPluginControlCenterCore.vue";
import {
  goDashboard,
  goPlugin,
  replaceQuery,
  type PluginsPanelTab,
} from "@/core/navigation/nav";

const route = useRoute();

function normalizeTab(rawTab: unknown): PluginsPanelTab {
  const normalized = String(rawTab || "").trim().toLowerCase();
  if (
    normalized === "installed" ||
    normalized === "settings" ||
    normalized === "store"
  ) {
    return normalized;
  }
  return "store";
}

const activeTab = computed<PluginsPanelTab>(() => normalizeTab(route.query.tab));

watch(
  () => route.query.tab,
  (rawTab) => {
    const normalized = normalizeTab(rawTab);
    if (String(rawTab || "") === normalized) return;
    void replaceQuery({ tab: normalized });
  },
  { immediate: true },
);

function handleClose(): void {
  void goDashboard();
}

function handleSetTab(tab: PluginsPanelTab): void {
  if (tab === activeTab.value) return;
  void replaceQuery({ tab });
}

function handleOpenPlugin(pluginId: string): void {
  void goPlugin(pluginId);
}
</script>
