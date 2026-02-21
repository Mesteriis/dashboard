<template>
  <section class="editor-section">
    <div class="editor-section-title">
      <span>Iframe-настройки</span>
    </div>

    <div class="editor-grid">
      <label class="editor-field">
        <span>Sandbox</span>
        <select v-model="itemEditor.form.iframeSandboxMode" :disabled="itemEditor.submitting">
          <option value="default">default</option>
          <option value="enabled">enabled</option>
          <option value="disabled">disabled</option>
        </select>
      </label>

      <label class="editor-field">
        <span>Allow (через запятую)</span>
        <input
          v-model.trim="itemEditor.form.iframeAllowInput"
          type="text"
          placeholder="fullscreen, clipboard-read"
          autocomplete="off"
          :disabled="itemEditor.submitting"
        />
      </label>

      <label class="editor-field">
        <span>Referrer policy</span>
        <input
          v-model.trim="itemEditor.form.iframeReferrerPolicy"
          type="text"
          placeholder="no-referrer"
          autocomplete="off"
          :disabled="itemEditor.submitting"
        />
      </label>

      <label class="editor-field">
        <span>Auth profile</span>
        <select v-model="itemEditor.form.authProfile" :disabled="itemEditor.submitting">
          <option value="">none</option>
          <option v-for="profile in authProfileOptions" :key="profile.id" :value="profile.id">{{ profile.id }} ({{ profile.type }})</option>
        </select>
      </label>
    </div>
  </section>
</template>

<script setup>
import { useDashboardStore } from '../../../stores/dashboardStore.js'

const dashboard = useDashboardStore()
const { itemEditor, authProfileOptions } = dashboard
</script>
