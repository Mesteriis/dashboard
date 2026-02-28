<template>
  <section class="settings-section">
    <header class="settings-section-header">
      <h2>Валидация конфигурации</h2>
      <p>Проверка конфигурации на ошибки</p>
    </header>

    <div class="settings-section-content">
      <ConfigValidatorPanel
        @config-restored="handleConfigRestored"
        @error="handleValidatorError"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import ConfigValidatorPanel from "@/views/dashboard/modals/ConfigValidatorPanel.vue";
import { useDashboardStore } from "@/features/stores/dashboardStore";

const dashboard = useDashboardStore();
const { loadConfig } = dashboard;

function handleConfigRestored(): void {
  void loadConfig();
}

function handleValidatorError(error: string): void {
  // Обработка ошибки валидации
  console.error("Validator error:", error);
}
</script>
