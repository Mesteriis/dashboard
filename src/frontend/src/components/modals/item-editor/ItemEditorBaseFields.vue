<template>
  <div class="editor-grid">
    <label class="editor-field">
      <span>ID</span>
      <input v-model.trim="itemEditor.form.id" type="text" placeholder="auto (из названия)" autocomplete="off" :disabled="itemEditor.submitting" />
    </label>

    <label class="editor-field">
      <span>Название</span>
      <input
        v-model.trim="itemEditor.form.title"
        type="text"
        placeholder="Например: Grafana"
        autocomplete="off"
        :disabled="itemEditor.submitting"
        required
      />
    </label>

    <label class="editor-field">
      <span>Тип</span>
      <select v-model="itemEditor.form.type" :disabled="itemEditor.submitting">
        <option value="link">link</option>
        <option value="iframe">iframe</option>
      </select>
    </label>

    <label class="editor-field">
      <span>URL</span>
      <input
        v-model.trim="itemEditor.form.url"
        type="url"
        placeholder="https://service.example.com"
        autocomplete="off"
        :disabled="itemEditor.submitting"
        required
      />
    </label>

    <label class="editor-field">
      <span>Иконка</span>
      <input
        v-model.trim="itemEditor.form.icon"
        type="text"
        placeholder="proxmox, grafana..."
        autocomplete="off"
        :disabled="itemEditor.submitting"
      />
    </label>

    <label class="editor-field">
      <span>Открытие</span>
      <select v-model="itemEditor.form.open" :disabled="itemEditor.submitting">
        <option value="new_tab">new_tab</option>
        <option value="same_tab">same_tab</option>
      </select>
    </label>
  </div>

  <label class="editor-field">
    <span>Теги (через запятую)</span>
    <input
      v-model.trim="itemEditor.form.tagsInput"
      type="text"
      placeholder="infra, monitoring"
      autocomplete="off"
      :disabled="itemEditor.submitting"
    />
  </label>
</template>

<script setup>
import { useDashboardStore } from '../../../stores/dashboardStore.js'

const dashboard = useDashboardStore()
const { itemEditor } = dashboard
</script>
