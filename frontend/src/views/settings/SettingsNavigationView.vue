<template>
  <nav class="settings-nav" aria-label="Разделы настроек">
    <ul class="settings-nav-list">
      <li class="settings-nav-item">
        <button
          class="settings-nav-link"
          :class="{ active: activeSection === 'appearance' }"
          type="button"
          @click="$emit('update:activeSection', 'appearance')"
        >
          <Palette class="ui-icon settings-nav-icon" />
          <span>Внешний вид</span>
        </button>
      </li>
      <li class="settings-nav-item">
        <button
          class="settings-nav-link"
          :class="{ active: activeSection === 'runtime' }"
          type="button"
          @click="$emit('update:activeSection', 'runtime')"
        >
          <Play class="ui-icon settings-nav-icon" />
          <span>Режим запуска</span>
        </button>
      </li>
      <li class="settings-nav-item">
        <button
          class="settings-nav-link"
          :class="{ active: activeSection === 'actions' }"
          type="button"
          @click="$emit('update:activeSection', 'actions')"
        >
          <Zap class="ui-icon settings-nav-icon" />
          <span>Быстрые действия</span>
        </button>
      </li>
      <li class="settings-nav-item">
        <button
          class="settings-nav-link"
          :class="{ active: activeSection === 'backup' }"
          type="button"
          @click="$emit('update:activeSection', 'backup')"
        >
          <Download class="ui-icon settings-nav-icon" />
          <span>Backup конфигурации</span>
        </button>
      </li>
      <li class="settings-nav-item">
        <button
          class="settings-nav-link"
          :class="{ active: activeSection === 'validation' }"
          type="button"
          @click="$emit('update:activeSection', 'validation')"
        >
          <ShieldCheck class="ui-icon settings-nav-icon" />
          <span>Валидация</span>
        </button>
      </li>
    </ul>
  </nav>
</template>

<script setup lang="ts">
import {
  Download,
  Palette,
  Play,
  ShieldCheck,
  Zap,
} from "lucide-vue-next";

defineProps<{
  activeSection: string;
}>();

defineEmits<{
  "update:activeSection": [value: string];
}>();
</script>
