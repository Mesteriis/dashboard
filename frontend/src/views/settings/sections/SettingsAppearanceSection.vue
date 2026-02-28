<template>
  <section class="settings-section">
    <header class="settings-section-header">
      <h2>Внешний вид</h2>
      <p>Настройки темы, палитры и режима отображения</p>
    </header>

    <div class="settings-section-content">
      <div class="settings-group">
        <h3>Тема</h3>
        <div
          class="settings-switcher"
          role="radiogroup"
          aria-label="Тема интерфейса"
        >
          <button
            v-for="option in themeModeOptions"
            :key="`theme:${option.value}`"
            class="settings-btn"
            :class="{ active: themeMode === option.value }"
            type="button"
            :aria-pressed="themeMode === option.value"
            @click="setThemeMode(option.value)"
          >
            {{ option.label }}
          </button>
        </div>
      </div>

      <div class="settings-group">
        <h3>Палитра</h3>
        <div
          class="settings-switcher"
          role="radiogroup"
          aria-label="Цветовая палитра"
        >
          <button
            v-for="option in themePaletteOptions"
            :key="`palette:${option.value}`"
            class="settings-btn"
            :class="{ active: themePalette === option.value }"
            type="button"
            :aria-pressed="themePalette === option.value"
            @click="setThemePalette(option.value)"
          >
            {{ option.label }}
          </button>
        </div>
      </div>

      <div class="settings-group">
        <h3>Вид</h3>
        <div
          class="settings-switcher"
          role="radiogroup"
          aria-label="Режим отображения сервисов"
        >
          <button
            v-for="option in servicePresentationOptions"
            :key="`view:${option.value}`"
            class="settings-btn"
            :class="{ active: serviceCardView === option.value }"
            type="button"
            :aria-pressed="serviceCardView === option.value"
            @click="serviceCardView = option.value"
          >
            {{ option.label }}
          </button>
        </div>
      </div>

      <div class="settings-group">
        <h3>Группировка</h3>
        <div
          class="settings-switcher"
          role="radiogroup"
          aria-label="Группировка сервисов"
        >
          <button
            v-for="option in serviceGroupingOptions"
            :key="`grouping:${option.value}`"
            class="settings-btn"
            :class="{ active: serviceGroupingMode === option.value }"
            type="button"
            :aria-pressed="serviceGroupingMode === option.value"
            :disabled="isSidebarHidden"
            @click="setGroupingMode(option.value)"
          >
            {{ option.label }}
          </button>
        </div>
        <p v-if="isSidebarHidden" class="settings-hint">
          Группировка недоступна при скрытом меню.
        </p>
      </div>

      <div class="settings-group">
        <h3>Site</h3>
        <div
          class="settings-switcher wrap"
          role="radiogroup"
          aria-label="Фильтр по площадке"
        >
          <button
            v-for="option in siteFilterOptions"
            :key="`site:${option.value}`"
            class="settings-btn"
            :class="{ active: siteFilter === option.value }"
            type="button"
            :aria-pressed="siteFilter === option.value"
            @click="setSiteFilter(option.value)"
          >
            {{ option.label }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { useDashboardStore } from "@/features/stores/dashboardStore";

const dashboard = useDashboardStore();

const {
  isSidebarHidden,
  serviceCardView,
  serviceGroupingMode,
  serviceGroupingOptions,
  servicePresentationOptions,
  siteFilter,
  siteFilterOptions,
  themeMode,
  themeModeOptions,
  themePalette,
  themePaletteOptions,
  setSiteFilter,
  setThemePalette,
  setThemeMode,
} = dashboard;

function setGroupingMode(value: string): void {
  if (isSidebarHidden.value) return;
  serviceGroupingMode.value = value;
}
</script>
