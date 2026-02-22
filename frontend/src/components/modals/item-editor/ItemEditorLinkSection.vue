<template>
  <section class="editor-section">
    <div class="editor-section-title">
      <label class="editor-check">
        <input
          v-model="itemEditor.form.healthcheckEnabled"
          type="checkbox"
          :disabled="itemEditor.submitting"
        />
        <span>Healthcheck</span>
      </label>
    </div>

    <div v-if="itemEditor.form.healthcheckEnabled" class="editor-grid">
      <label class="editor-field">
        <span>Healthcheck URL</span>
        <input
          v-model.trim="itemEditor.form.healthcheckUrl"
          type="url"
          placeholder="https://service.example.com/health"
          autocomplete="off"
          :disabled="itemEditor.submitting"
        />
      </label>

      <label class="editor-field">
        <span>Интервал (sec)</span>
        <input
          v-model.number="itemEditor.form.healthcheckIntervalSec"
          type="number"
          min="1"
          max="3600"
          :disabled="itemEditor.submitting"
        />
      </label>

      <label class="editor-field">
        <span>Timeout (ms)</span>
        <input
          v-model.number="itemEditor.form.healthcheckTimeoutMs"
          type="number"
          min="100"
          max="120000"
          :disabled="itemEditor.submitting"
        />
      </label>
    </div>
  </section>
</template>

<script setup>
import { useDashboardStore } from "../../../stores/dashboardStore.js";

const dashboard = useDashboardStore();
const { itemEditor } = dashboard;
</script>
