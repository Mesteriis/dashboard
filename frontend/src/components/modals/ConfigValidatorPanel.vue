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

<script>
import {
  validateDashboardYaml,
  restoreDashboardConfig,
} from "../../services/dashboardApi.js";

export default {
  name: "ConfigValidatorPanel",
  emits: ["config-restored", "error"],
  data() {
    return {
      yamlInput: "",
      isValidating: false,
      validationResult: null,
      error: "",
    };
  },
  methods: {
    async handleValidate() {
      if (!this.yamlInput.trim()) {
        this.error = "Введите YAML для проверки";
        return;
      }

      this.isValidating = true;
      this.error = "";
      this.validationResult = null;

      try {
        const result = await validateDashboardYaml(this.yamlInput);
        this.validationResult = {
          valid: result.valid,
          issues: result.issues || [],
        };
      } catch (err) {
        this.error = err.message || "Ошибка валидации";
        this.$emit("error", this.error);
      } finally {
        this.isValidating = false;
      }
    },

    async handleRestore() {
      if (!this.validationResult?.valid) {
        return;
      }

      if (
        !confirm(
          "Вы уверены, что хотите восстановить конфигурацию? Текущие данные будут заменены.",
        )
      ) {
        return;
      }

      try {
        const result = await restoreDashboardConfig(this.yamlInput);
        this.$emit("config-restored", result);
        this.yamlInput = "";
        this.validationResult = null;
      } catch (err) {
        this.error = err.message || "Ошибка восстановления конфигурации";
        this.$emit("error", this.error);
      }
    },

    clear() {
      this.yamlInput = "";
      this.validationResult = null;
      this.error = "";
    },
  },
};
</script>

<style scoped>
.config-validator {
  background: var(--surface, rgba(255, 255, 255, 0.04));
  border: 1px solid var(--border, rgba(255, 255, 255, 0.08));
  border-radius: 12px;
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
  border-radius: 6px;
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
  border-radius: 8px;
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
  border-radius: 8px;
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
  border-radius: 6px;
  font-size: 13px;
}

.issue-type {
  padding: 2px 8px;
  border-radius: 4px;
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
  border-radius: 6px;
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
  border-radius: 8px;
}

.error-icon {
  font-size: 18px;
}

.error-message {
  color: #ef4444;
  font-size: 14px;
}
</style>
