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
        <div class="settings-modal-dropdowns">
          <HeroDropdown
            v-model="serviceCardView"
            label="Вид"
            aria-label="Режим отображения сервисов"
            :options="servicePresentationOptions"
          />
          <HeroDropdown
            v-model="serviceGroupingMode"
            label="Группировка"
            aria-label="Группировка сервисов"
            :options="serviceGroupingOptions"
            :disabled="isSidebarHidden"
          >
            <template #prefix>
              <GitBranch class="ui-icon hero-dropdown-prefix-icon" aria-hidden="true" />
            </template>
          </HeroDropdown>
          <HeroDropdown v-model="siteFilter" label="Site" aria-label="Фильтр по площадке" :options="siteFilterOptions">
            <template #prefix>
              <MapPin class="ui-icon hero-dropdown-prefix-icon" aria-hidden="true" />
            </template>
          </HeroDropdown>
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
import { GitBranch, MapPin } from 'lucide-vue-next'
import BaseModal from '../primitives/BaseModal.vue'
import HeroDropdown from '../primitives/HeroDropdown.vue'
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
  toggleEditMode,
  toggleSidebarView,
} = dashboard

function openSearchFromSettings() {
  closeSettingsPanel()
  openCommandPalette()
}
</script>
