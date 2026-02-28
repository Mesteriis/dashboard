<template>
  <section class="settings-section">
    <header class="settings-section-header">
      <h2>Backup конфигурации</h2>
      <p>Экспорт и импорт конфигурации панели</p>
    </header>

    <div class="settings-section-content">
      <div class="settings-actions-list">
        <button
          class="settings-action-row"
          type="button"
          :disabled="backupBusy"
          @click="downloadConfigBackup"
        >
          <div class="settings-action-row-content">
            <Download class="ui-icon settings-action-icon" />
            <div class="settings-action-row-text">
              <span class="settings-action-row-title">
                {{ backupBusy ? "Готовим backup..." : "Скачать backup (.yaml)" }}
              </span>
              <span class="settings-action-row-desc">
                Экспорт текущей конфигурации
              </span>
            </div>
          </div>
          <ChevronRight class="ui-icon settings-action-caret" />
        </button>

        <label class="settings-action-row">
          <div class="settings-action-row-content">
            <Upload class="ui-icon settings-action-icon" />
            <div class="settings-action-row-text">
              <span class="settings-action-row-title">
                {{
                  restoreBusy
                    ? "Импортируем backup..."
                    : "Импортировать backup (.yaml)"
                }}
              </span>
              <span class="settings-action-row-desc">
                Импорт конфигурации из файла
              </span>
            </div>
          </div>
          <ChevronRight class="ui-icon settings-action-caret" />
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
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { ChevronRight, Download, Upload } from "lucide-vue-next";
import {
  fetchDashboardConfigBackup,
  restoreDashboardConfig,
} from "@/features/services/dashboardApi";
import { useDashboardStore } from "@/features/stores/dashboardStore";

const dashboard = useDashboardStore();
const { loadConfig } = dashboard;

const backupBusy = ref(false);
const restoreBusy = ref(false);
const backupError = ref("");
const backupSuccess = ref("");

function resolveErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? error.message : fallback;
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
  const input = event.target as HTMLInputElement;
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
</script>

<style scoped>
.settings-action-row input[type="file"] {
  display: none;
}
</style>
