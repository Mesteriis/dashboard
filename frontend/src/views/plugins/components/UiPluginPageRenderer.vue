<template>
  <section class="plugin-page">
    <header class="plugin-page-head">
      <button class="ghost" type="button" @click="emit('back')">
        Back to Plugins
      </button>
      <div>
        <p class="plugin-page-kicker">{{ pluginId }}</p>
        <h1>{{ manifest.plugin_id }}</h1>
        <p class="plugin-page-version">Version {{ manifest.version }}</p>
        <p v-if="manifestEnvelope.negotiation.fallback_used" class="plugin-page-notice">
          Fallback manifest is used:
          <code>{{ manifestEnvelope.negotiation.reason || "unknown reason" }}</code>
        </p>
      </div>
    </header>

    <section v-if="!manifest.page.enabled" class="plugin-page-status">
      <h3>Plugin page is disabled</h3>
      <p>Manifest marks this page as disabled (`page.enabled = false`).</p>
    </section>

    <section v-else-if="missingCapabilities.length" class="plugin-page-status">
      <h3>Access denied</h3>
      <p>Missing capabilities for this plugin page:</p>
      <ul>
        <li v-for="cap in missingCapabilities" :key="cap">
          <code>{{ cap }}</code>
        </li>
      </ul>
    </section>

    <UiPluginLayoutShell v-else :layout="manifest.page.layout">
      <template #sidebar>
        <p class="plugin-layout-meta">
          Renderer: <code>{{ manifest.frontend.renderer }}</code>
        </p>
        <p class="plugin-layout-meta">
          Layout: <code>{{ manifest.page.layout }}</code>
        </p>
      </template>

      <UiPluginBundleSandbox
        v-if="useCustomBundle"
        :plugin-id="pluginId"
        :manifest="manifest"
        :entry="customBundleEntry"
        :sandbox-enabled="manifest.frontend.customBundle.sandbox"
        @failed="onBundleFailed"
      />

      <UiPluginUniversalRenderer v-else :manifest="manifest" />
    </UiPluginLayoutShell>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import UiPluginBundleSandbox from "@/views/plugins/components/UiPluginBundleSandbox.vue";
import UiPluginLayoutShell from "@/views/plugins/components/UiPluginLayoutShell.vue";
import UiPluginUniversalRenderer from "@/views/plugins/components/UiPluginUniversalRenderer.vue";
import {
  getMissingManifestCapabilities,
  type PluginManifestEnvelope,
} from "@/features/plugins/manifest";

const props = defineProps<{
  pluginId: string;
  manifestEnvelope: PluginManifestEnvelope;
}>();

const emit = defineEmits<{
  back: [];
}>();

const customBundleFailed = ref(false);
const manifest = computed(() => props.manifestEnvelope.manifest);
const missingCapabilities = computed(() => getMissingManifestCapabilities(manifest.value));

const killSwitchEnabled = computed(() => {
  const key = manifest.value.frontend.customBundle.killSwitchKey;
  const runtimeKillSwitch =
    typeof window !== "undefined" &&
    Boolean((window as Window & { __OKO_PLUGIN_BUNDLE_KILL_SWITCH__?: boolean }).__OKO_PLUGIN_BUNDLE_KILL_SWITCH__);
  const storageKillSwitch =
    typeof window !== "undefined" && window.localStorage.getItem(key) === "1";
  return runtimeKillSwitch || storageKillSwitch;
});

const customBundleEntry = computed(() =>
  String(manifest.value.frontend.customBundle.entry || "").trim(),
);

const useCustomBundle = computed(() => {
  if (customBundleFailed.value) return false;
  if (killSwitchEnabled.value) return false;
  if (manifest.value.frontend.renderer !== "custom") return false;
  if (!manifest.value.frontend.customBundle.enabled) return false;
  if (!customBundleEntry.value) return false;
  return true;
});

function onBundleFailed(): void {
  customBundleFailed.value = true;
}
</script>

<style scoped>
.plugin-page {
  position: relative;
  z-index: 1;
  min-height: 0;
  height: 100%;
  margin: 0;
  display: grid;
  gap: 12px;
  overflow: auto;
  scrollbar-gutter: stable;
  padding-right: 2px;
}

.plugin-page-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 16px;
  padding: 4px 2px 10px;
}

.plugin-page-kicker {
  margin: 0 0 4px;
  font-size: 12px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: rgba(189, 207, 228, 0.86);
}

.plugin-page-head h1 {
  margin: 0;
}

.plugin-page-version {
  margin: 8px 0 0;
  color: rgba(170, 192, 215, 0.82);
  font-size: 13px;
}

.plugin-page-notice {
  margin: 8px 0 0;
  padding: 8px 10px;
  border-radius: var(--ui-radius);
  border: 1px solid rgba(124, 154, 188, 0.34);
  background: rgba(10, 21, 34, 0.74);
}

.plugin-page-status {
  padding: 8px 2px;
}

.plugin-page-status h3 {
  margin: 0 0 8px;
}

.plugin-page-status p {
  margin: 0 0 8px;
}

.plugin-page-status ul {
  margin: 0;
  padding-left: 18px;
}

.plugin-layout-meta {
  margin: 0 0 8px;
  color: rgba(187, 207, 230, 0.84);
}
</style>
