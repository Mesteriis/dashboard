<template>
  <BaseModal
    :open="settingsPanel.open"
    backdrop-class="settings-modal-backdrop"
    modal-class="settings-modal"
    @backdrop="closeSettingsPanel"
  >
    <header class="settings-modal-header">
      <div>
        <h3>Настройки панели</h3>
        <p>Единая точка управления интерфейсом и режимами отображения.</p>
      </div>
      <button class="ghost" type="button" @click="closeSettingsPanel">Закрыть</button>
    </header>

    <div class="settings-modal-grid">
      <section class="settings-modal-section">
        <h4>Отображение</h4>
        <div class="settings-state-group">
          <p class="settings-state-label">Вид</p>
          <div class="settings-state-switcher" role="radiogroup" aria-label="Режим отображения сервисов">
            <button
              v-for="option in servicePresentationOptions"
              :key="`view:${option.value}`"
              class="settings-state-btn"
              :class="{ active: serviceCardView === option.value }"
              type="button"
              :aria-pressed="serviceCardView === option.value"
              @click="serviceCardView = option.value"
            >
              {{ option.label }}
            </button>
          </div>
        </div>

        <div class="settings-state-group">
          <p class="settings-state-label">Группировка</p>
          <div class="settings-state-switcher" role="radiogroup" aria-label="Группировка сервисов">
            <button
              v-for="option in serviceGroupingOptions"
              :key="`grouping:${option.value}`"
              class="settings-state-btn"
              :class="{ active: serviceGroupingMode === option.value }"
              type="button"
              :aria-pressed="serviceGroupingMode === option.value"
              :disabled="isSidebarHidden"
              @click="setGroupingMode(option.value)"
            >
              {{ option.label }}
            </button>
          </div>
          <p v-if="isSidebarHidden" class="settings-state-hint">Группировка недоступна при скрытом меню.</p>
        </div>

        <div class="settings-state-group">
          <p class="settings-state-label">Site</p>
          <div class="settings-state-switcher wrap" role="radiogroup" aria-label="Фильтр по площадке">
            <button
              v-for="option in siteFilterOptions"
              :key="`site:${option.value}`"
              class="settings-state-btn"
              :class="{ active: siteFilter === option.value }"
              type="button"
              :aria-pressed="siteFilter === option.value"
              @click="setSiteFilter(option.value)"
            >
              {{ option.label }}
            </button>
          </div>
        </div>
      </section>

      <section class="settings-modal-section">
        <h4>Быстрые действия</h4>
        <div class="settings-modal-actions">
          <button class="ghost" type="button" @click="toggleSidebarView">
            {{ isSidebarHidden ? 'Показать меню' : 'Скрыть меню' }}
          </button>
          <button class="ghost" type="button" @click="toggleEditMode">
            {{ editMode ? 'Выключить edit mode' : 'Включить edit mode' }}
          </button>
          <button class="ghost" type="button" @click="openSearchFromSettings">Открыть поиск (Ctrl/Cmd+K)</button>
        </div>
      </section>
    </div>
  </BaseModal>
</template>

<script setup>
import BaseModal from '../primitives/BaseModal.vue'
import { useDashboardStore } from '../../stores/dashboardStore.js'

const dashboard = useDashboardStore()
const {
  closeSettingsPanel,
  editMode,
  isSidebarHidden,
  openCommandPalette,
  serviceCardView,
  serviceGroupingMode,
  serviceGroupingOptions,
  servicePresentationOptions,
  settingsPanel,
  siteFilter,
  siteFilterOptions,
  setSiteFilter,
  toggleEditMode,
  toggleSidebarView,
} = dashboard

function setGroupingMode(value) {
  if (isSidebarHidden.value) return
  serviceGroupingMode.value = value
}

function openSearchFromSettings() {
  closeSettingsPanel()
  openCommandPalette()
}
</script>
