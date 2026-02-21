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
          <button class="settings-nav-action" type="button" @click="toggleSidebarView">
            <span class="settings-nav-action-main">
              <PanelLeft class="ui-icon settings-nav-action-icon" />
              <span>{{ isSidebarHidden ? 'Показать меню' : 'Скрыть меню' }}</span>
            </span>
            <ChevronRight class="ui-icon settings-nav-action-caret" />
          </button>
          <button class="settings-nav-action" type="button" @click="toggleEditMode">
            <span class="settings-nav-action-main">
              <Pencil class="ui-icon settings-nav-action-icon" />
              <span>{{ editMode ? 'Выключить edit mode' : 'Включить edit mode' }}</span>
            </span>
            <ChevronRight class="ui-icon settings-nav-action-caret" />
          </button>
          <button class="settings-nav-action" type="button" @click="openSearchFromSettings">
            <span class="settings-nav-action-main">
              <Search class="ui-icon settings-nav-action-icon" />
              <span>Открыть поиск (Ctrl/Cmd+K)</span>
            </span>
            <ChevronRight class="ui-icon settings-nav-action-caret" />
          </button>
        </div>
      </section>
    </div>
  </BaseModal>
</template>

<script setup>
import { ChevronRight, PanelLeft, Pencil, Search } from 'lucide-vue-next'
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
