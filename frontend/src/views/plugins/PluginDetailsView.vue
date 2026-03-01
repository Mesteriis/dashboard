<template>
  <UiBlankLayout
    :emblem-src="EMBLEM_SRC"
    layout-mode="no-sidebar"
    content-label="Plugin details"
  >
    <template #header-tabs>
      <nav
        class="hero-page-tabs"
        role="tablist"
        aria-label="Plugin details tabs"
      >
        <button
          id="plugin-details-tab"
          class="hero-page-tab-btn active"
          type="button"
          role="tab"
          aria-selected="true"
          tabindex="0"
          aria-controls="plugin-details-panel"
        >
          <Puzzle class="ui-icon hero-page-tab-icon" />
          <span class="hero-page-tab-label">
            {{
              manifestEnvelope?.manifest?.plugin_id || pluginId || "Plugin details"
            }}
          </span>
        </button>
      </nav>
    </template>

    <template #canvas-main>
      <section
        id="plugin-details-panel"
        role="tabpanel"
        aria-labelledby="plugin-details-tab"
        class="plugin-details-canvas"
      >
        <section v-if="loading" class="plugin-page-status panel">
          <h2>Loading plugin</h2>
          <p>
            Fetching manifest for <code>{{ pluginId }}</code
            >...
          </p>
        </section>

        <section v-else-if="errorState" class="plugin-page-status panel">
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

        <UiPluginPageRenderer
          v-else-if="manifestEnvelope"
          :plugin-id="pluginId"
          :manifest-envelope="manifestEnvelope"
          @back="handleBack"
        />
      </section>
    </template>
  </UiBlankLayout>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { Puzzle } from "lucide-vue-next";
import UiPluginPageRenderer from "@/views/plugins/components/UiPluginPageRenderer.vue";
import UiBlankLayout from "@/components/layout/UiBlankLayout.vue";
import { goPluginsPanel } from "@/app/navigation/nav";
import {
  PluginManifestNotFoundError,
  PluginManifestParseError,
  loadPluginManifest,
  type PluginManifestEnvelope,
} from "@/features/plugins/manifest";
import {
  EMBLEM_SRC,
} from "@/features/stores/ui/storeConstants";

interface ErrorState {
  title: string;
  message: string;
  detail?: string;
}

const route = useRoute();
const loading = ref(false);
const manifestEnvelope = ref<PluginManifestEnvelope | null>(null);
const errorState = ref<ErrorState | null>(null);

const pluginId = computed(() => {
  const params = route.params as Record<string, string | undefined>;
  return String(params.pluginId || "").trim();
});

async function loadManifest(): Promise<void> {
  if (!pluginId.value) {
    errorState.value = {
      title: "Invalid plugin id",
      message: "Route parameter pluginId is empty.",
    };
    manifestEnvelope.value = null;
    return;
  }

  loading.value = true;
  manifestEnvelope.value = null;
  errorState.value = null;

  try {
    manifestEnvelope.value = await loadPluginManifest(pluginId.value);
  } catch (error: unknown) {
    if (error instanceof PluginManifestNotFoundError) {
      errorState.value = {
        title: "Plugin not found",
        message: `Manifest for '${pluginId.value}' was not found.`,
      };
    } else if (error instanceof PluginManifestParseError) {
      errorState.value = {
        title: "Manifest parse error",
        message: `Failed to parse manifest for '${pluginId.value}'.`,
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
  () => void loadManifest(),
  { immediate: true },
);
</script>

<style scoped>
.plugin-details-canvas {
  min-height: 0;
  height: 100%;
  overflow: auto;
  scrollbar-gutter: stable;
}

.plugin-page-status {
  position: relative;
  z-index: 1;
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
