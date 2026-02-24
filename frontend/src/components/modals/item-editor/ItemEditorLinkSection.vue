<template>
  <section class="editor-section">
    <div class="editor-section-title">
      <BaseSwitch
        v-model="itemEditor.form.healthcheckEnabled"
        :disabled="itemEditor.submitting"
        label="Healthcheck"
      />
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

      <section class="editor-field editor-field--wide">
        <span>TLS</span>
        <div class="editor-switch-list">
          <BaseSwitch
            v-model="itemEditor.form.healthcheckTlsVerify"
            :disabled="itemEditor.submitting"
            label="Проверять TLS сертификат"
          />
        </div>
      </section>

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

      <label class="editor-field">
        <span>Interval (sec)</span>
        <input
          v-model.number="itemEditor.form.healthcheckIntervalSec"
          type="number"
          min="5"
          max="86400"
          :disabled="itemEditor.submitting"
        />
      </label>
    </div>
  </section>
</template>

<script setup lang="ts">
import BaseSwitch from "@/components/primitives/BaseSwitch.vue";
import { useDashboardStore } from "@/stores/dashboardStore";

const dashboard = useDashboardStore();
const { itemEditor } = dashboard;
</script>
