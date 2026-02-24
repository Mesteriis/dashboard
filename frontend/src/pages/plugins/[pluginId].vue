<template>
  <section
    v-if="loading"
    class="plugin-page-status panel"
  >
    <h2>Loading plugin</h2>
    <p>Fetching manifest for <code>{{ pluginId }}</code>...</p>
  </section>

  <section
    v-else-if="errorState"
    class="plugin-page-status panel"
  >
    <h2>{{ errorState.title }}</h2>
    <p>{{ errorState.message }}</p>
    <p v-if="errorState.detail" class="plugin-page-error-detail">
      {{ errorState.detail }}
    </p>
    <div class="plugin-page-error-actions">
      <button class="ghost" type="button" @click="handleBack">
        Back to Plugins
      </button>
      <button class="ghost" type="button" @click="loadManifest">
        Retry
      </button>
    </div>
  </section>

  <PluginPageRenderer
    v-else-if="manifest"
    :plugin-id="pluginId"
    :manifest="manifest"
    @back="handleBack"
  />
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import PluginPageRenderer from "@/components/plugins/PluginPageRenderer.vue";
import { goPluginsPanel } from "@/core/navigation/nav";
import {
  PluginManifestNotFoundError,
  PluginManifestParseError,
  loadPluginManifest,
  type PluginManifest,
} from "@/core/plugins/manifest";

interface ErrorState {
  title: string;
  message: string;
  detail?: string;
}

const route = useRoute("/plugins/[pluginId]");
const loading = ref(false);
const manifest = ref<PluginManifest | null>(null);
const errorState = ref<ErrorState | null>(null);

const pluginId = computed(() => String(route.params.pluginId || "").trim());

async function loadManifest(): Promise<void> {
  if (!pluginId.value) {
    errorState.value = {
      title: "Invalid plugin id",
      message: "Route parameter pluginId is empty.",
    };
    manifest.value = null;
    return;
  }

  loading.value = true;
  manifest.value = null;
  errorState.value = null;

  try {
    manifest.value = await loadPluginManifest(pluginId.value);
  } catch (error: unknown) {
    if (error instanceof PluginManifestNotFoundError) {
      errorState.value = {
        title: "Plugin not found",
        message: `Manifest for '${pluginId.value}' was not found.`,
        detail: error.candidates.slice(0, 2).join(" | "),
      };
    } else if (error instanceof PluginManifestParseError) {
      errorState.value = {
        title: "Manifest parse error",
        message: `Failed to parse manifest for '${pluginId.value}'.`,
        detail: error.sourcePath,
      };
    } else {
      errorState.value = {
        title: "Failed to load plugin",
        message:
          error instanceof Error
            ? error.message
            : "Unknown error while loading plugin manifest.",
      };
    }
  } finally {
    loading.value = false;
  }
}

function handleBack(): void {
  void goPluginsPanel();
}

watch(
  () => pluginId.value,
  () => {
    void loadManifest();
  },
  { immediate: true },
);
</script>

<style scoped>
.plugin-page-status {
  position: relative;
  z-index: 1;
  margin: 24px;
  min-height: calc(100vh - 48px);
  padding: 18px;
}

.plugin-page-error-actions {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.plugin-page-error-detail {
  color: rgba(196, 214, 236, 0.82);
  font-size: 13px;
}
</style>
