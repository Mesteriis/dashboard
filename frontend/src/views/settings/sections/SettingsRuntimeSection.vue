<template>
  <section class="settings-section">
    <header class="settings-section-header">
      <h2>Режим запуска</h2>
      <p>Настройки deployment и runtime окружения</p>
    </header>

    <div class="settings-section-content">
      <div class="settings-group">
        <h3>Deployment</h3>
        <div
          class="settings-switcher"
          role="radiogroup"
          aria-label="Режим запуска проекта"
        >
          <button
            v-for="option in deploymentModeOptions"
            :key="`deploy:${option.value}`"
            class="settings-btn"
            :class="{ active: deploymentModeDraft === option.value }"
            type="button"
            :disabled="option.value !== deploymentModeDraft"
            :aria-pressed="deploymentModeDraft === option.value"
          >
            {{ option.label }}
          </button>
        </div>
        <p class="settings-hint">
          Режим определяется средой запуска и доступен для чтения.
        </p>
      </div>

      <template v-if="deploymentModeDraft === 'app'">
        <div class="settings-group">
          <h3>Режим клиента</h3>
          <div
            class="settings-switcher"
            role="radiogroup"
            aria-label="Режим клиента приложения"
          >
            <button
              v-for="option in appClientModeOptions"
              :key="`app-client:${option.value}`"
              class="settings-btn"
              :class="{ active: appClientModeDraft === option.value }"
              type="button"
              :disabled="runtimeApplying"
              :aria-pressed="appClientModeDraft === option.value"
              @click="appClientModeDraft = option.value"
            >
              {{ option.label }}
            </button>
          </div>
          <p class="settings-hint">{{ runtimeStatusHint }}</p>
        </div>

        <div class="settings-group">
          <h3>Remote URL</h3>
          <input
            v-model.trim="remoteBaseUrlDraft"
            class="settings-input"
            type="text"
            autocomplete="off"
            spellcheck="false"
            placeholder="http://127.0.0.1:8000"
            :disabled="runtimeApplying || appClientModeDraft !== 'thin'"
          />
        </div>

        <div class="settings-actions">
          <button
            class="settings-action-btn"
            type="button"
            :disabled="runtimeApplying || !runtimeChanged"
            @click="applyRuntimeMode"
          >
            <Play class="ui-icon" />
            <span>{{
              runtimeApplying ? "Применяем..." : "Применить режим клиента"
            }}</span>
          </button>
        </div>

        <p
          v-if="runtimeError"
          class="settings-hint settings-error"
        >
          {{ runtimeError }}
        </p>
      </template>

      <div
        v-if="desktopRuntime.desktop"
        class="settings-group"
      >
        <h3>Desktop Runtime (macOS Apple Silicon)</h3>
        <div class="settings-switcher">
          <button
            class="settings-btn"
            :class="{ active: desktopRuntime.mode === 'embedded' }"
            type="button"
            disabled
          >
            Embedded
          </button>
          <button
            class="settings-btn"
            :class="{ active: desktopRuntime.mode === 'remote' }"
            type="button"
            disabled
          >
            Remote
          </button>
        </div>
        <p class="settings-hint">
          {{
            desktopRuntime.embeddedRunning
              ? "Локальный backend запущен."
              : "Локальный backend остановлен."
          }}
        </p>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { Play } from "lucide-vue-next";
import {
  getRuntimeProfile,
  initDesktopRuntimeBridge,
  setDesktopRuntimeProfile,
} from "@/features/services/desktopRuntime";
import { EVENT_API_BASE_CHANGE, onOkoEvent } from "@/features/services/events";
import { useDashboardStore } from "@/features/stores/dashboardStore";

const dashboard = useDashboardStore();
const { loadConfig } = dashboard;

type AppClientModeDraft = "thin" | "thick";
type DeploymentMode = "docker" | "dev" | "app";

interface RuntimeProfile {
  desktop: boolean;
  mode: "embedded" | "remote";
  embeddedRunning: boolean;
  deploymentMode?: DeploymentMode;
  appClientMode?: AppClientModeDraft;
  remoteBaseUrl?: string;
}

const desktopRuntime = ref<RuntimeProfile>(getRuntimeProfile());
const deploymentModeDraft = ref<DeploymentMode>(
  desktopRuntime.value.deploymentMode || "docker",
);
const appClientModeDraft = ref<AppClientModeDraft>(
  desktopRuntime.value.appClientMode === "thick" ? "thick" : "thin",
);
const remoteBaseUrlDraft = ref(
  desktopRuntime.value.remoteBaseUrl || "http://127.0.0.1:8000",
);
const runtimeApplying = ref(false);
const runtimeError = ref("");

const deploymentModeOptions = [
  { value: "docker" as DeploymentMode, label: "Docker" },
  { value: "dev" as DeploymentMode, label: "Dev (Vite + backend)" },
  { value: "app" as DeploymentMode, label: "App" },
];

const appClientModeOptions = [
  { value: "thin" as AppClientModeDraft, label: "Тонкий клиент" },
  { value: "thick" as AppClientModeDraft, label: "Толстый клиент" },
];

let removeApiBaseListener: () => void = () => {};

const runtimeStatusHint = computed(() => {
  if (deploymentModeDraft.value !== "app") {
    return "Для web-режимов backend управляется внешним окружением.";
  }
  if (appClientModeDraft.value === "thick") {
    return desktopRuntime.value.embeddedRunning
      ? "Локальный backend уже запущен."
      : "Локальный backend будет запущен после применения.";
  }
  return desktopRuntime.value.embeddedRunning
    ? "После применения локальный backend будет остановлен."
    : "Локальный backend отключен.";
});

const runtimeChanged = computed(() => {
  if (deploymentModeDraft.value !== "app" || !desktopRuntime.value.desktop)
    return false;
  const normalizedDraftUrl = String(remoteBaseUrlDraft.value || "").trim();
  const runtimeModeChanged =
    (appClientModeDraft.value === "thick" ? "embedded" : "remote") !==
    desktopRuntime.value.mode;
  if (appClientModeDraft.value !== "thick") {
    return (
      runtimeModeChanged ||
      normalizedDraftUrl !==
        String(desktopRuntime.value.remoteBaseUrl || "").trim()
    );
  }
  return runtimeModeChanged;
});

function resolveErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback;
}

function normalizeRuntimeDraft(): void {
  deploymentModeDraft.value =
    desktopRuntime.value.deploymentMode ||
    (desktopRuntime.value.desktop ? "app" : "docker");
  appClientModeDraft.value =
    desktopRuntime.value.appClientMode ||
    (desktopRuntime.value.mode === "embedded" ? "thick" : "thin");
  remoteBaseUrlDraft.value =
    desktopRuntime.value.remoteBaseUrl || "http://127.0.0.1:8000";
}

async function applyRuntimeMode(): Promise<void> {
  if (
    !desktopRuntime.value.desktop ||
    deploymentModeDraft.value !== "app" ||
    !runtimeChanged.value ||
    runtimeApplying.value
  )
    return;
  runtimeApplying.value = true;
  runtimeError.value = "";

  try {
    const updated = await setDesktopRuntimeProfile({
      mode: appClientModeDraft.value === "thick" ? "embedded" : "remote",
      remoteBaseUrl: remoteBaseUrlDraft.value,
    });
    desktopRuntime.value = updated;
    normalizeRuntimeDraft();
    await loadConfig();
  } catch (error: unknown) {
    runtimeError.value = resolveErrorMessage(
      error,
      "Не удалось применить desktop runtime",
    );
  } finally {
    runtimeApplying.value = false;
  }
}

onMounted(async () => {
  const profile = await initDesktopRuntimeBridge();
  desktopRuntime.value = profile;
  normalizeRuntimeDraft();
  removeApiBaseListener = onOkoEvent(
    EVENT_API_BASE_CHANGE,
    syncDesktopRuntimeFromBridge,
  );
});

onBeforeUnmount(() => {
  removeApiBaseListener();
  removeApiBaseListener = () => {};
});

function syncDesktopRuntimeFromBridge(): void {
  desktopRuntime.value = getRuntimeProfile();
  normalizeRuntimeDraft();
}
</script>
