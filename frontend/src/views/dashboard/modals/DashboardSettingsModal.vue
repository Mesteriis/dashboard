<template>
  <BaseModal
    :open="settingsPanel.open"
    backdrop-class="settings-modal-backdrop"
    modal-class="settings-modal"
    @backdrop="closeSettingsPanel"
  >
    <header class="settings-modal-header">
      <div class="settings-modal-header__content">
        <h3 class="settings-modal-header__title">Настройки панели</h3>
        <p class="settings-modal-header__subtitle">
          Единая точка управления интерфейсом и режимами отображения.
        </p>
      </div>
      <UiButton variant="ghost" size="sm" @click="closeSettingsPanel">
        Закрыть
      </UiButton>
    </header>

    <div class="settings-modal-content">
      <!-- Левая колонка: Отображение -->
      <div class="settings-modal-sidebar">
        <UiCard title="Отображение">
          <UiFieldset legend="Тема" collapsible>
            <UiSelectButton
              v-model="themeMode"
              :options="themeModeOptions"
              label="Тема интерфейса"
            />
          </UiFieldset>

          <UiFieldset legend="Палитра" collapsible>
            <UiSelectButton
              v-model="themePalette"
              :options="themePaletteOptions"
              label="Цветовая палитра"
            />
          </UiFieldset>

          <UiFieldset legend="Вид" collapsible>
            <UiSelectButton
              v-model="serviceCardView"
              :options="servicePresentationOptions"
              label="Режим отображения сервисов"
            />
          </UiFieldset>

          <UiFieldset legend="Группировка" collapsible>
            <UiSelectButton
              v-model="serviceGroupingMode"
              :options="serviceGroupingOptions"
              :disabled="isSidebarHidden"
              label="Группировка сервисов"
            />
            <p v-if="isSidebarHidden" class="settings-hint">
              Группировка недоступна при скрытом меню.
            </p>
          </UiFieldset>

          <UiFieldset legend="Site" collapsible>
            <UiSelectButton
              v-model="siteFilter"
              :options="siteFilterOptions"
              label="Фильтр по площадке"
            />
          </UiFieldset>
        </UiCard>
      </div>

      <!-- Правая колонка: основной контент -->
      <div class="settings-modal-main">
        <!-- Режим запуска проекта -->
        <UiCard title="Режим запуска проекта" subtitle="Deployment">
          <div class="settings-form-group">
            <UiLabel>Режим запуска</UiLabel>
            <UiSelectButton
              v-model="deploymentModeDraft"
              :options="deploymentModeOptions"
              label="Режим запуска проекта"
            />
            <p class="settings-hint">
              Режим определяется средой запуска и доступен для чтения.
            </p>
          </div>

          <template v-if="deploymentModeDraft === 'app'">
            <div class="settings-form-group">
              <UiLabel>Режим клиента</UiLabel>
              <UiSelectButton
                v-model="appClientModeDraft"
                :options="appClientModeOptions"
                :disabled="runtimeApplying"
                label="Режим клиента приложения"
              />
              <p class="settings-hint">{{ runtimeStatusHint }}</p>
            </div>

            <div class="settings-form-group">
              <UiLabel for="remote-url">Remote URL</UiLabel>
              <input
                id="remote-url"
                v-model.trim="remoteBaseUrlDraft"
                class="ui-input"
                type="text"
                autocomplete="off"
                spellcheck="false"
                placeholder="http://127.0.0.1:8000"
                :disabled="runtimeApplying || appClientModeDraft !== 'thin'"
              />
            </div>

            <div class="settings-form-actions">
              <UiButton
                variant="primary"
                :disabled="runtimeApplying || !runtimeChanged"
                :loading="runtimeApplying"
                @click="applyRuntimeMode"
              >
                <Play class="ui-icon" />
                {{
                  runtimeApplying ? "Применяем..." : "Применить режим клиента"
                }}
              </UiButton>
            </div>

            <p v-if="runtimeError" class="settings-hint settings-error">
              {{ runtimeError }}
            </p>
          </template>
        </UiCard>

        <!-- Desktop Runtime -->
        <UiCard
          v-if="desktopRuntime.desktop"
          title="Desktop Runtime"
          subtitle="macOS Apple Silicon"
        >
          <div class="settings-form-group">
            <UiLabel>Текущий backend</UiLabel>
            <div class="settings-status-row">
              <UiButton
                variant="secondary"
                :class="{ active: desktopRuntime.mode === 'embedded' }"
                disabled
              >
                Embedded
              </UiButton>
              <UiButton
                variant="secondary"
                :class="{ active: desktopRuntime.mode === 'remote' }"
                disabled
              >
                Remote
              </UiButton>
            </div>
            <p class="settings-hint">
              {{
                desktopRuntime.embeddedRunning
                  ? "Локальный backend запущен."
                  : "Локальный backend остановлен."
              }}
            </p>
          </div>
        </UiCard>

        <!-- Быстрые действия и Backup -->
        <div class="settings-actions-grid">
          <UiCard title="Быстрые действия">
            <div class="settings-quick-actions">
              <button
                class="settings-action-btn"
                type="button"
                @click="toggleSidebarView"
              >
                <PanelLeft class="ui-icon" />
                <span>{{
                  isSidebarHidden ? "Показать меню" : "Скрыть меню"
                }}</span>
                <ChevronRight class="ui-icon settings-action-btn__caret" />
              </button>

              <button
                class="settings-action-btn"
                type="button"
                @click="toggleEditMode"
              >
                <Pencil class="ui-icon" />
                <span>{{
                  editMode ? "Выключить edit mode" : "Включить edit mode"
                }}</span>
                <ChevronRight class="ui-icon settings-action-btn__caret" />
              </button>

              <button
                class="settings-action-btn"
                type="button"
                @click="openSearchFromSettings"
              >
                <Search class="ui-icon" />
                <span>Открыть поиск</span>
                <kbd class="settings-kbd">Ctrl/Cmd+K</kbd>
                <ChevronRight class="ui-icon settings-action-btn__caret" />
              </button>
            </div>
          </UiCard>

          <UiCard title="Backup конфигурации">
            <div class="settings-backup-actions">
              <UiButton
                variant="primary"
                :disabled="backupBusy"
                :loading="backupBusy"
                block
                @click="downloadConfigBackup"
              >
                <template #icon>
                  <Download class="ui-icon" />
                </template>
                {{ backupBusy ? "Готовим backup..." : "Скачать backup (.yaml)" }}
              </UiButton>

              <label class="ui-button ui-button--primary ui-button--block">
                <Upload class="ui-icon" />
                <span>{{
                  restoreBusy
                    ? "Импортируем backup..."
                    : "Импортировать backup (.yaml)"
                }}</span>
                <input
                  type="file"
                  accept=".yaml,.yml,text/yaml"
                  :disabled="restoreBusy"
                  @change="restoreConfigBackup"
                />
              </label>
            </div>
            <p v-if="backupError" class="settings-hint settings-error">
              {{ backupError }}
            </p>
            <p v-else-if="backupSuccess" class="settings-hint">
              {{ backupSuccess }}
            </p>
          </UiCard>
        </div>

        <!-- Валидация конфигурации -->
        <UiCard title="Валидация конфигурации">
          <ConfigValidatorPanel
            @config-restored="handleConfigRestored"
            @error="handleValidatorError"
          />
        </UiCard>
      </div>
    </div>
  </BaseModal>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import {
  ChevronRight,
  Download,
  PanelLeft,
  Pencil,
  Play,
  Search,
  Upload,
} from "lucide-vue-next";
import BaseModal from "@/ui/overlays/BaseModal.vue";
import UiCard from "@/ui/surfaces/UiCard.vue";
import UiFieldset from "@/ui/surfaces/UiFieldset.vue";
import UiButton from "@/ui/actions/UiButton.vue";
import UiSelectButton from "@/ui/forms/UiSelectButton.vue";
import UiLabel from "@/ui/forms/UiLabel.vue";
import ConfigValidatorPanel from "@/views/dashboard/modals/ConfigValidatorPanel.vue";
import {
  fetchDashboardConfigBackup,
  restoreDashboardConfig,
} from "@/features/services/dashboardApi";
import {
  getRuntimeProfile,
  initDesktopRuntimeBridge,
  setDesktopRuntimeProfile,
  type AppClientMode,
  type DeploymentMode,
  type RuntimeMode,
  type RuntimeProfile,
} from "@/features/services/desktopRuntime";
import { EVENT_API_BASE_CHANGE, onOkoEvent } from "@/features/services/events";
import { useDashboardStore } from "@/features/stores/dashboardStore";

const dashboard = useDashboardStore();
const {
  closeSettingsPanel,
  editMode,
  isSidebarHidden,
  openCommandPalette,
  serviceCardView,
  serviceGroupingMode,
  serviceGroupingOptions,
  servicePresentationOptions,
  settingsPanel,
  siteFilter,
  siteFilterOptions,
  themeMode,
  themeModeOptions,
  themePalette,
  themePaletteOptions,
  toggleEditMode,
  toggleSidebarView,
  loadConfig,
} = dashboard;

type AppClientModeDraft = Exclude<AppClientMode, null>;
type Option<T extends string> = {
  value: T;
  label: string;
};

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
const backupBusy = ref(false);
const restoreBusy = ref(false);
const backupError = ref("");
const backupSuccess = ref("");
const deploymentModeOptions: ReadonlyArray<Option<DeploymentMode>> = [
  { value: "docker", label: "Docker" },
  { value: "dev", label: "Dev (Vite + backend)" },
  { value: "app", label: "App" },
];
const appClientModeOptions: ReadonlyArray<Option<AppClientModeDraft>> = [
  { value: "thin", label: "Тонкий клиент" },
  { value: "thick", label: "Толстый клиент" },
];
let removeApiBaseListener: () => void = () => {};

const desktopRuntimeModeDraft = computed<
  Extract<RuntimeMode, "embedded" | "remote">
>(() => (appClientModeDraft.value === "thick" ? "embedded" : "remote"));
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
    desktopRuntimeModeDraft.value !== desktopRuntime.value.mode;
  if (desktopRuntimeModeDraft.value !== "remote") {
    return runtimeModeChanged;
  }
  return (
    runtimeModeChanged ||
    normalizedDraftUrl !==
      String(desktopRuntime.value.remoteBaseUrl || "").trim()
  );
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

function openSearchFromSettings(): void {
  closeSettingsPanel();
  openCommandPalette();
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
      mode: desktopRuntimeModeDraft.value,
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

async function downloadConfigBackup(): Promise<void> {
  if (backupBusy.value) return;
  backupBusy.value = true;
  backupError.value = "";
  backupSuccess.value = "";

  try {
    const payload = await fetchDashboardConfigBackup();
    const blob = new Blob([payload.yaml], {
      type: "application/x-yaml;charset=utf-8",
    });
    const blobUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = blobUrl;
    link.download = payload.filename || "dashboard-backup.yaml";
    link.style.display = "none";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(blobUrl);
    backupSuccess.value = `Backup сохранен: ${link.download}`;
  } catch (error: unknown) {
    backupError.value = resolveErrorMessage(error, "Не удалось скачать backup");
  } finally {
    backupBusy.value = false;
  }
}

async function restoreConfigBackup(event: Event): Promise<void> {
  if (!(event.target instanceof HTMLInputElement)) return;
  const input = event.target;
  const file = input.files?.[0];
  if (!file || restoreBusy.value) return;

  restoreBusy.value = true;
  backupError.value = "";
  backupSuccess.value = "";

  try {
    const yamlText = await file.text();
    await restoreDashboardConfig(yamlText);
    await loadConfig();
    backupSuccess.value = `Backup импортирован: ${file.name}`;
  } catch (error: unknown) {
    backupError.value = resolveErrorMessage(
      error,
      "Не удалось импортировать backup",
    );
  } finally {
    restoreBusy.value = false;
    input.value = "";
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

function handleConfigRestored(): void {
  backupSuccess.value = "Конфигурация успешно восстановлена";
  backupError.value = "";
  void loadConfig();
}

function handleValidatorError(error: string): void {
  backupError.value = error;
}
</script>
