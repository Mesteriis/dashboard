<template>
  <section class="plugin-page panel">
    <header class="plugin-page-head">
      <button class="ghost" type="button" @click="emit('back')">
        Back to Plugins
      </button>
      <div>
        <p class="plugin-page-kicker">{{ manifest.id }}</p>
        <h1>{{ manifest.title }}</h1>
        <p v-if="manifest.description" class="plugin-page-description">
          {{ manifest.description }}
        </p>
        <p class="plugin-page-version">
          {{
            manifest.version
              ? `Version ${manifest.version}`
              : "Version not specified"
          }}
        </p>
      </div>
    </header>

    <p v-if="showRemoteFallbackNotice" class="plugin-page-notice">
      Remote renderer
      <code>{{ manifest.renderer.component }}</code>
      is not registered. Built-in renderer is used.
    </p>

    <component
      :is="resolvedRemoteRenderer"
      v-if="resolvedRemoteRenderer"
      :manifest="manifest"
      :plugin-id="pluginId"
    />

    <template v-else>
      <section v-if="!manifest.sections.length" class="plugins-empty-state">
        <h3>No manifest sections</h3>
        <p>This plugin manifest has no renderable sections yet.</p>
      </section>

      <section
        v-for="(section, index) in manifest.sections"
        :key="`${section.kind}:${index}`"
        class="plugin-manifest-section"
      >
        <header v-if="section.title" class="plugin-manifest-section-head">
          <h3>{{ section.title }}</h3>
        </header>

        <div v-if="section.kind === 'cards'" class="plugin-manifest-cards">
          <article
            v-for="card in section.cards"
            :key="card.title"
            class="plugin-manifest-card"
          >
            <h4>{{ card.title }}</h4>
            <p v-if="card.text">{{ card.text }}</p>
          </article>
        </div>

        <div v-else-if="section.kind === 'links'" class="plugin-manifest-links">
          <a
            v-for="item in section.items"
            :key="`${item.label}:${item.url}`"
            class="ghost plugin-manifest-link"
            :href="item.url"
            :target="item.open || '_blank'"
            rel="noopener noreferrer"
          >
            <span>{{ item.label }}</span>
            <small v-if="item.description">{{ item.description }}</small>
          </a>
        </div>

        <div
          v-else-if="section.kind === 'iframe'"
          class="plugin-manifest-iframe"
        >
          <iframe
            :src="section.src"
            :style="{ height: `${section.height || 360}px` }"
            :sandbox="
              section.sandbox || 'allow-same-origin allow-scripts allow-forms'
            "
            loading="lazy"
            title="Plugin iframe section"
          ></iframe>
        </div>

        <pre
          v-else-if="section.kind === 'settings'"
          class="plugin-manifest-settings"
        ><code>{{ JSON.stringify(section.schema, null, 2) }}</code></pre>
      </section>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, type Component } from "vue";
import type { PluginManifest } from "@/features/plugins/manifest";

const props = defineProps<{
  pluginId: string;
  manifest: PluginManifest;
}>();

const emit = defineEmits<{
  back: [];
}>();

const remoteRenderers: Record<string, Component> = {};

const resolvedRemoteRenderer = computed<Component | null>(() => {
  if (props.manifest.renderer.type !== "remote") {
    return null;
  }
  const key = String(props.manifest.renderer.component || "").trim();
  if (!key) return null;
  return remoteRenderers[key] || null;
});

const showRemoteFallbackNotice = computed(() => {
  if (props.manifest.renderer.type !== "remote") return false;
  const componentKey = String(props.manifest.renderer.component || "").trim();
  if (!componentKey) return false;
  return !resolvedRemoteRenderer.value;
});
</script>

<style scoped>
.plugin-page {
  position: relative;
  z-index: 1;
  min-height: calc(100vh - 48px);
  margin: 24px;
  padding: 18px;
  overflow: auto;
}

.plugin-page-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 16px;
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

.plugin-page-description {
  margin: 8px 0 0;
  color: rgba(219, 230, 246, 0.86);
}

.plugin-page-version {
  margin: 8px 0 0;
  color: rgba(170, 192, 215, 0.82);
  font-size: 13px;
}

.plugin-page-notice {
  margin: 0 0 18px;
  padding: 10px 12px;
  border-radius: var(--ui-radius);
  border: 1px solid rgba(124, 154, 188, 0.34);
  background: rgba(10, 21, 34, 0.74);
}

.plugin-manifest-section {
  border: 1px solid rgba(96, 136, 170, 0.32);
  background: rgba(8, 16, 28, 0.64);
  border-radius: var(--ui-radius);
  padding: 14px;
  margin-bottom: 12px;
}

.plugin-manifest-section-head h3 {
  margin: 0 0 12px;
}

.plugin-manifest-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 10px;
}

.plugin-manifest-card {
  border: 1px solid rgba(123, 157, 194, 0.28);
  border-radius: var(--ui-radius);
  background: rgba(10, 20, 31, 0.72);
  padding: 12px;
}

.plugin-manifest-card h4 {
  margin: 0 0 6px;
}

.plugin-manifest-card p {
  margin: 0;
  color: rgba(199, 216, 236, 0.88);
}

.plugin-manifest-links {
  display: grid;
  gap: 8px;
}

.plugin-manifest-link {
  display: grid;
  gap: 4px;
  text-decoration: none;
}

.plugin-manifest-link small {
  color: rgba(180, 202, 227, 0.82);
}

.plugin-manifest-iframe iframe {
  width: 100%;
  border: 1px solid rgba(103, 142, 182, 0.35);
  border-radius: var(--ui-radius);
  background: #0b1220;
}

.plugin-manifest-settings {
  margin: 0;
  border: 1px solid rgba(116, 146, 176, 0.34);
  border-radius: var(--ui-radius);
  padding: 10px 12px;
  background: rgba(9, 17, 30, 0.8);
  overflow-x: auto;
}
</style>
