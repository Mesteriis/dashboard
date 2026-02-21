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

      <section v-if="desktopRuntime.desktop" class="settings-modal-section settings-modal-section-wide">
        <h4>Desktop Runtime (macOS Apple Silicon)</h4>
        <div class="settings-state-group">
          <p class="settings-state-label">Режим backend</p>
          <div class="settings-state-switcher" role="radiogroup" aria-label="Режим backend">
            <button
              class="settings-state-btn"
              :class="{ active: desktopRuntimeModeDraft === 'embedded' }"
              type="button"
              :disabled="runtimeApplying"
              :aria-pressed="desktopRuntimeModeDraft === 'embedded'"
              @click="desktopRuntimeModeDraft = 'embedded'"
            >
              Embedded (inside app)
            </button>
            <button
              class="settings-state-btn"
              :class="{ active: desktopRuntimeModeDraft === 'remote' }"
              type="button"
              :disabled="runtimeApplying"
              :aria-pressed="desktopRuntimeModeDraft === 'remote'"
              @click="desktopRuntimeModeDraft = 'remote'"
            >
              Remote (external server)
            </button>
          </div>
        </div>

        <div class="settings-state-group">
          <p class="settings-state-label">Remote URL</p>
          <input
            v-model.trim="remoteBaseUrlDraft"
            class="settings-runtime-input"
            type="text"
            autocomplete="off"
            spellcheck="false"
            placeholder="http://127.0.0.1:8090"
            :disabled="runtimeApplying || desktopRuntimeModeDraft !== 'remote'"
          />
        </div>

        <div class="settings-runtime-actions">
          <button class="settings-nav-action" type="button" :disabled="runtimeApplying || !runtimeChanged" @click="applyRuntimeMode">
            <span class="settings-nav-action-main">
              <Play class="ui-icon settings-nav-action-icon" />
              <span>{{ runtimeApplying ? 'Применяем...' : 'Применить runtime' }}</span>
            </span>
            <ChevronRight class="ui-icon settings-nav-action-caret" />
          </button>
        </div>

        <p v-if="runtimeError" class="settings-state-hint settings-state-error">{{ runtimeError }}</p>
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
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ChevronRight, PanelLeft, Pencil, Play, Search } from 'lucide-vue-next'
import BaseModal from '../primitives/BaseModal.vue'
import { getRuntimeProfile, initDesktopRuntimeBridge, setDesktopRuntimeProfile } from '../../services/desktopRuntime.js'
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
  loadConfig,
} = dashboard

const desktopRuntime = ref(getRuntimeProfile())
const desktopRuntimeModeDraft = ref(desktopRuntime.value.mode === 'web' ? 'embedded' : desktopRuntime.value.mode)
const remoteBaseUrlDraft = ref(desktopRuntime.value.remoteBaseUrl || 'http://127.0.0.1:8090')
const runtimeApplying = ref(false)
const runtimeError = ref('')

const runtimeChanged = computed(() => {
  if (!desktopRuntime.value.desktop) return false
  const normalizedDraftUrl = String(remoteBaseUrlDraft.value || '').trim()
  return (
    desktopRuntimeModeDraft.value !== desktopRuntime.value.mode ||
    normalizedDraftUrl !== String(desktopRuntime.value.remoteBaseUrl || '').trim()
  )
})

function normalizeRuntimeDraft() {
  desktopRuntimeModeDraft.value = desktopRuntime.value.mode === 'web' ? 'embedded' : desktopRuntime.value.mode
  remoteBaseUrlDraft.value = desktopRuntime.value.remoteBaseUrl || 'http://127.0.0.1:8090'
}

function setGroupingMode(value) {
  if (isSidebarHidden.value) return
  serviceGroupingMode.value = value
}

function openSearchFromSettings() {
  closeSettingsPanel()
  openCommandPalette()
}

async function applyRuntimeMode() {
  if (!desktopRuntime.value.desktop || !runtimeChanged.value || runtimeApplying.value) return
  runtimeApplying.value = true
  runtimeError.value = ''

  try {
    const updated = await setDesktopRuntimeProfile({
      mode: desktopRuntimeModeDraft.value,
      remoteBaseUrl: remoteBaseUrlDraft.value,
    })
    desktopRuntime.value = updated
    normalizeRuntimeDraft()
    await loadConfig()
  } catch (error) {
    runtimeError.value = error?.message || 'Не удалось применить desktop runtime'
  } finally {
    runtimeApplying.value = false
  }
}

onMounted(async () => {
  const profile = await initDesktopRuntimeBridge()
  desktopRuntime.value = profile
  normalizeRuntimeDraft()
  window.addEventListener('oko:api-base-change', syncDesktopRuntimeFromBridge)
})

onBeforeUnmount(() => {
  window.removeEventListener('oko:api-base-change', syncDesktopRuntimeFromBridge)
})

function syncDesktopRuntimeFromBridge() {
  desktopRuntime.value = getRuntimeProfile()
  normalizeRuntimeDraft()
}
</script>
