<template>
  <div class="config-validator">
    <div class="validator-header">
      <h3>Валидация конфигурации</h3>
      <button
        class="btn-validate"
        @click="handleValidate"
        :disabled="isValidating"
      >
        {{ isValidating ? "Проверка..." : "Проверить YAML" }}
      </button>
    </div>

    <div class="validator-content">
      <textarea
        v-model="yamlInput"
        class="yaml-input"
        placeholder="Вставьте YAML конфигурацию для проверки..."
        spellcheck="false"
      ></textarea>

      <div
        v-if="validationResult"
        class="validation-result"
        :class="validationResult.valid ? 'valid' : 'invalid'"
      >
        <div class="result-header">
          <span class="result-icon">{{
            validationResult.valid ? "✓" : "✗"
          }}</span>
          <span class="result-text">
            {{
              validationResult.valid
                ? "Конфигурация валидна"
                : `Найдено ошибок: ${validationResult.issues.length}`
            }}
          </span>
        </div>

        <ul
          v-if="!validationResult.valid && validationResult.issues.length"
          class="issues-list"
        >
          <li
            v-for="(issue, index) in validationResult.issues"
            :key="index"
            class="issue-item"
          >
            <span class="issue-type" :class="issue.type">{{ issue.type }}</span>
            <span class="issue-message">{{ issue.message }}</span>
            <span v-if="issue.location" class="issue-location">
              (строка {{ issue.location.line }}, столбец
              {{ issue.location.column }})
            </span>
          </li>
        </ul>

        <div v-if="validationResult.valid" class="valid-actions">
          <button class="btn-restore" @click="handleRestore">
            Восстановить из этой конфигурации
          </button>
        </div>
      </div>

      <div v-if="error" class="validation-error">
        <span class="error-icon">⚠</span>
        <span class="error-message">{{ error }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import {
  type DashboardConfigBackup,
  type DashboardValidationResult,
  restoreDashboardConfig,
  validateDashboardYaml,
} from "@/features/services/dashboardApi";

const emit = defineEmits<{
  "config-restored": [payload: DashboardConfigBackup];
  error: [message: string];
}>();

const yamlInput = ref("");
const isValidating = ref(false);
const validationResult = ref<DashboardValidationResult | null>(null);
const error = ref("");

function resolveErrorMessage(err: unknown, fallback: string): string {
  return err instanceof Error && err.message ? err.message : fallback;
}

async function handleValidate(): Promise<void> {
  if (!yamlInput.value.trim()) {
    error.value = "Введите YAML для проверки";
    return;
  }

  isValidating.value = true;
  error.value = "";
  validationResult.value = null;

  try {
    const result = await validateDashboardYaml(yamlInput.value);
    validationResult.value = {
      valid: Boolean(result.valid),
      issues: Array.isArray(result.issues) ? result.issues : [],
    };
  } catch (err) {
    error.value = resolveErrorMessage(err, "Ошибка валидации");
    emit("error", error.value);
  } finally {
    isValidating.value = false;
  }
}

async function handleRestore(): Promise<void> {
  if (!validationResult.value?.valid) return;

  if (
    !globalThis.confirm(
      "Вы уверены, что хотите восстановить конфигурацию? Текущие данные будут заменены.",
    )
  ) {
    return;
  }

  try {
    const result = await restoreDashboardConfig(yamlInput.value);
    emit("config-restored", result);
    yamlInput.value = "";
    validationResult.value = null;
  } catch (err) {
    error.value = resolveErrorMessage(err, "Ошибка восстановления конфигурации");
    emit("error", error.value);
  }
}

function clear(): void {
  yamlInput.value = "";
  validationResult.value = null;
  error.value = "";
}

defineExpose({ clear });
</script>

<style scoped>
.config-validator {
  background: var(--surface, rgba(255, 255, 255, 0.04));
  border: 1px solid var(--border, rgba(255, 255, 255, 0.08));
  border-radius: var(--ui-radius);
  padding: 20px;
  margin-bottom: 20px;
}

.validator-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.validator-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary, #e5e7eb);
}

.btn-validate {
  padding: 8px 16px;
  background: var(--accent, #2dd4bf);
  color: #000;
  border: none;
  border-radius: var(--ui-radius);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-validate:hover:not(:disabled) {
  opacity: 0.9;
}

.btn-validate:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.validator-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.yaml-input {
  width: 100%;
  min-height: 200px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--border, rgba(255, 255, 255, 0.08));
  border-radius: var(--ui-radius);
  color: var(--text-primary, #e5e7eb);
  font-family: "Monaco", "Menlo", "Ubuntu Mono", monospace;
  font-size: 13px;
  line-height: 1.5;
  resize: vertical;
}

.yaml-input:focus {
  outline: none;
  border-color: var(--accent, #2dd4bf);
}

.validation-result {
  padding: 16px;
  border-radius: var(--ui-radius);
  border: 1px solid;
}

.validation-result.valid {
  background: rgba(34, 197, 94, 0.1);
  border-color: rgba(34, 197, 94, 0.3);
}

.validation-result.invalid {
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.3);
}

.result-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.result-icon {
  font-size: 20px;
  font-weight: bold;
}

.validation-result.valid .result-icon {
  color: #22c55e;
}

.validation-result.invalid .result-icon {
  color: #ef4444;
}

.result-text {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #e5e7eb);
}

.issues-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.issue-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: var(--ui-radius);
  font-size: 13px;
}

.issue-type {
  padding: 2px 8px;
  border-radius: var(--ui-radius);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  white-space: nowrap;
}

.issue-type.error {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.issue-type.warning {
  background: rgba(251, 191, 36, 0.2);
  color: #fbbf24;
}

.issue-message {
  flex: 1;
  color: var(--text-secondary, #9ca3af);
}

.issue-location {
  color: var(--text-muted, #6b7280);
  font-size: 12px;
}

.valid-actions {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.btn-restore {
  padding: 8px 16px;
  background: var(--accent, #2dd4bf);
  color: #000;
  border: none;
  border-radius: var(--ui-radius);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-restore:hover {
  opacity: 0.9;
}

.validation-error {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: var(--ui-radius);
}

.error-icon {
  font-size: 18px;
}

.error-message {
  color: #ef4444;
  font-size: 14px;
}
</style>
