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

      <section class="settings-modal-section settings-modal-section-wide">
        <h4>Режим запуска проекта</h4>
        <div class="settings-state-group">
          <p class="settings-state-label">Deployment</p>
          <div class="settings-state-switcher" role="radiogroup" aria-label="Режим запуска проекта">
            <button
              v-for="option in deploymentModeOptions"
              :key="`deploy:${option.value}`"
              class="settings-state-btn"
              :class="{ active: deploymentModeDraft === option.value }"
              type="button"
              :disabled="option.value !== deploymentModeDraft"
              :aria-pressed="deploymentModeDraft === option.value"
            >
              {{ option.label }}
            </button>
          </div>
          <p class="settings-state-hint">Режим определяется средой запуска и доступен для чтения.</p>
        </div>

        <template v-if="deploymentModeDraft === 'app'">
          <div class="settings-state-group">
            <p class="settings-state-label">Режим клиента</p>
            <div class="settings-state-switcher" role="radiogroup" aria-label="Режим клиента приложения">
              <button
                v-for="option in appClientModeOptions"
                :key="`app-client:${option.value}`"
                class="settings-state-btn"
                :class="{ active: appClientModeDraft === option.value }"
                type="button"
                :disabled="runtimeApplying"
                :aria-pressed="appClientModeDraft === option.value"
                @click="appClientModeDraft = option.value"
              >
                {{ option.label }}
              </button>
            </div>
            <p class="settings-state-hint">{{ runtimeStatusHint }}</p>
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
              :disabled="runtimeApplying || appClientModeDraft !== 'thin'"
            />
          </div>

          <div class="settings-runtime-actions">
            <button class="settings-nav-action" type="button" :disabled="runtimeApplying || !runtimeChanged" @click="applyRuntimeMode">
              <span class="settings-nav-action-main">
                <Play class="ui-icon settings-nav-action-icon" />
                <span>{{ runtimeApplying ? 'Применяем...' : 'Применить режим клиента' }}</span>
              </span>
              <ChevronRight class="ui-icon settings-nav-action-caret" />
            </button>
          </div>

          <p v-if="runtimeError" class="settings-state-hint settings-state-error">{{ runtimeError }}</p>
        </template>
      </section>

      <section v-if="desktopRuntime.desktop" class="settings-modal-section settings-modal-section-wide">
        <h4>Desktop Runtime (macOS Apple Silicon)</h4>
        <div class="settings-state-group">
          <p class="settings-state-label">Текущий backend</p>
          <div class="settings-state-switcher">
            <button
              class="settings-state-btn"
              :class="{ active: desktopRuntime.mode === 'embedded' }"
              type="button"
              disabled
            >
              Embedded
            </button>
            <button
              class="settings-state-btn"
              :class="{ active: desktopRuntime.mode === 'remote' }"
              type="button"
              disabled
            >
              Remote
            </button>
          </div>
          <p class="settings-state-hint">
            {{ desktopRuntime.embeddedRunning ? 'Локальный backend запущен.' : 'Локальный backend остановлен.' }}
          </p>
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

      <section class="settings-modal-section">
        <h4>Backup конфигурации</h4>
        <div class="settings-modal-actions">
          <button class="settings-nav-action" type="button" :disabled="backupBusy" @click="downloadConfigBackup">
            <span class="settings-nav-action-main">
              <Download class="ui-icon settings-nav-action-icon" />
              <span>{{ backupBusy ? 'Готовим backup...' : 'Скачать backup (.yaml)' }}</span>
            </span>
            <ChevronRight class="ui-icon settings-nav-action-caret" />
          </button>
          <label class="settings-runtime-input settings-file-input">
            <Upload class="ui-icon settings-nav-action-icon" />
            <span>{{ restoreBusy ? 'Импортируем backup...' : 'Импортировать backup (.yaml)' }}</span>
            <input type="file" accept=".yaml,.yml,text/yaml" :disabled="restoreBusy" @change="restoreConfigBackup" />
          </label>
        </div>
        <p v-if="backupError" class="settings-state-hint settings-state-error">{{ backupError }}</p>
        <p v-else-if="backupSuccess" class="settings-state-hint">{{ backupSuccess }}</p>
      </section>
    </div>
  </BaseModal>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ChevronRight, Download, PanelLeft, Pencil, Play, Search, Upload } from 'lucide-vue-next'
import BaseModal from '../primitives/BaseModal.vue'
import { fetchDashboardConfigBackup, restoreDashboardConfig } from '../../services/dashboardApi.js'
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
const deploymentModeDraft = ref(desktopRuntime.value.deploymentMode || 'docker')
const appClientModeDraft = ref(desktopRuntime.value.appClientMode || 'thin')
const remoteBaseUrlDraft = ref(desktopRuntime.value.remoteBaseUrl || 'http://127.0.0.1:8090')
const runtimeApplying = ref(false)
const runtimeError = ref('')
const backupBusy = ref(false)
const restoreBusy = ref(false)
const backupError = ref('')
const backupSuccess = ref('')
const deploymentModeOptions = [
  { value: 'docker', label: 'Docker' },
  { value: 'dev', label: 'Dev (Vite + backend)' },
  { value: 'app', label: 'App' },
]
const appClientModeOptions = [
  { value: 'thin', label: 'Тонкий клиент' },
  { value: 'thick', label: 'Толстый клиент' },
]

const desktopRuntimeModeDraft = computed(() => (appClientModeDraft.value === 'thick' ? 'embedded' : 'remote'))
const runtimeStatusHint = computed(() => {
  if (deploymentModeDraft.value !== 'app') {
    return 'Для web-режимов backend управляется внешним окружением.'
  }
  if (appClientModeDraft.value === 'thick') {
    return desktopRuntime.value.embeddedRunning
      ? 'Локальный backend уже запущен.'
      : 'Локальный backend будет запущен после применения.'
  }
  return desktopRuntime.value.embeddedRunning
    ? 'После применения локальный backend будет остановлен.'
    : 'Локальный backend отключен.'
})

const runtimeChanged = computed(() => {
  if (deploymentModeDraft.value !== 'app' || !desktopRuntime.value.desktop) return false
  const normalizedDraftUrl = String(remoteBaseUrlDraft.value || '').trim()
  const runtimeModeChanged = desktopRuntimeModeDraft.value !== desktopRuntime.value.mode
  if (desktopRuntimeModeDraft.value !== 'remote') {
    return runtimeModeChanged
  }
  return (
    runtimeModeChanged ||
    normalizedDraftUrl !== String(desktopRuntime.value.remoteBaseUrl || '').trim()
  )
})

function normalizeRuntimeDraft() {
  deploymentModeDraft.value = desktopRuntime.value.deploymentMode || (desktopRuntime.value.desktop ? 'app' : 'docker')
  appClientModeDraft.value = desktopRuntime.value.appClientMode || (desktopRuntime.value.mode === 'embedded' ? 'thick' : 'thin')
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
  if (!desktopRuntime.value.desktop || deploymentModeDraft.value !== 'app' || !runtimeChanged.value || runtimeApplying.value) return
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

async function downloadConfigBackup() {
  if (backupBusy.value) return
  backupBusy.value = true
  backupError.value = ''
  backupSuccess.value = ''

  try {
    const payload = await fetchDashboardConfigBackup()
    const blob = new Blob([payload.yaml], { type: 'application/x-yaml;charset=utf-8' })
    const blobUrl = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = blobUrl
    link.download = payload.filename || 'dashboard-backup.yaml'
    link.style.display = 'none'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(blobUrl)
    backupSuccess.value = `Backup сохранен: ${link.download}`
  } catch (error) {
    backupError.value = error?.message || 'Не удалось скачать backup'
  } finally {
    backupBusy.value = false
  }
}

async function restoreConfigBackup(event) {
  const input = /** @type {HTMLInputElement | null} */ (event?.target || null)
  const file = input?.files?.[0]
  if (!file || restoreBusy.value) return

  restoreBusy.value = true
  backupError.value = ''
  backupSuccess.value = ''

  try {
    const yamlText = await file.text()
    await restoreDashboardConfig(yamlText)
    await loadConfig()
    backupSuccess.value = `Backup импортирован: ${file.name}`
  } catch (error) {
    backupError.value = error?.message || 'Не удалось импортировать backup'
  } finally {
    restoreBusy.value = false
    if (input) {
      input.value = ''
    }
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
