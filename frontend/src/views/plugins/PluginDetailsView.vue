<template>
  <UiBlankLayout
    :emblem-src="EMBLEM_SRC"
    :sidebar-hidden="isSidebarHidden"
    :sidebar-particles-id="SIDEBAR_PARTICLES_ID"
    canvas-aria-label="Plugin details"
  >
    <template v-slot:[SLOT_APP_SIDEBAR_TOP]>
      <header class="brand">
        <img :src="EMBLEM_SRC" alt="" aria-hidden="true" />
        <div>
          <p class="brand-title">Plugin Runtime</p>
          <p class="brand-subtitle">{{ pluginId || "Unknown plugin" }}</p>
        </div>
      </header>
    </template>

    <template v-slot:[SLOT_APP_SIDEBAR_MIDDLE]>
      <button
        class="ghost plugin-sidebar-back"
        type="button"
        title="Back to Plugins"
        aria-label="Back to Plugins"
        @click="handleBack"
      >
        <ArrowLeft class="ui-icon" />
        <span>Back to Plugins</span>
      </button>
    </template>

    <template v-slot:[SLOT_APP_HEADER_TABS]>
      <nav class="hero-page-tabs" role="tablist" aria-label="Plugin details tabs">
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
            {{ manifest?.title || pluginId || "Plugin details" }}
          </span>
        </button>
      </nav>
    </template>

    <template v-slot:[SLOT_PAGE_CANVAS_MAIN]>
      <section
        id="plugin-details-panel"
        role="tabpanel"
        aria-labelledby="plugin-details-tab"
        class="plugin-details-canvas"
      >
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

        <UiPluginPageRendererFacade
          v-else-if="manifest"
          :plugin-id="pluginId"
          :manifest="manifest"
          @back="handleBack"
        />
      </section>
    </template>
  </UiBlankLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { ArrowLeft, Puzzle } from "lucide-vue-next";
import UiPluginPageRendererFacade from "@/views/plugins/facades/UiPluginPageRendererFacade.vue";
import UiBlankLayout from "@/components/layout/UiBlankLayout.vue";
import { goPluginsPanel } from "@/app/navigation/nav";
import {
  PluginManifestNotFoundError,
  PluginManifestParseError,
  loadPluginManifest,
  type PluginManifest,
} from "@/features/plugins/manifest";
import { EMBLEM_SRC, SIDEBAR_PARTICLES_ID } from "@/features/stores/ui/storeConstants";
import { useUiStore } from "@/features/stores/uiStore";

interface ErrorState {
  title: string;
  message: string;
  detail?: string;
}

const SLOT_APP_SIDEBAR_TOP = "app.sidebar.top";
const SLOT_APP_SIDEBAR_MIDDLE = "app.sidebar.middle";
const SLOT_APP_HEADER_TABS = "app.header.tabs";
const SLOT_PAGE_CANVAS_MAIN = "page.canvas.main";

const route = useRoute();
const loading = ref(false);
const manifest = ref<PluginManifest | null>(null);
const errorState = ref<ErrorState | null>(null);
const uiStore = useUiStore();

const pluginId = computed(() => {
  const params = route.params as Record<string, string | undefined>;
  return String(params.pluginId || "").trim();
});
const isSidebarHidden = computed(() => uiStore.sidebarView.value === "hidden");

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

onMounted(() => {
  void uiStore.initSidebarParticles();
});

watch(
  () => pluginId.value,
  () => {
    void loadManifest();
  },
  { immediate: true },
);

watch(
  () => isSidebarHidden.value,
  (hidden) => {
    if (hidden) return;
    void uiStore.initSidebarParticles();
  },
);
</script>

<style scoped>
.plugin-details-canvas {
  min-height: 100%;
}

.plugin-sidebar-back {
  width: 100%;
  justify-content: flex-start;
  gap: 8px;
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
