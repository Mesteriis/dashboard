<template>
  <section class="hero-layout">
    <header class="hero panel hero-title-panel">
      <div id="hero-title-particles" class="hero-panel-particles" aria-hidden="true"></div>
      <div class="hero-title-content">
        <HeroPageTabs />
      </div>
    </header>

    <aside class="panel hero-control-panel service-hero-controls" :class="{ active: editMode }">
      <div id="hero-controls-particles" class="hero-panel-particles" aria-hidden="true"></div>
      <div class="hero-controls-content">
        <button
          class="hero-settings-secret-btn"
          type="button"
          title="Панель настроек"
          aria-label="Открыть панель настроек"
          @click="openSettingsPanel"
        >
          <SlidersHorizontal class="ui-icon hero-action-icon" />
        </button>

        <div class="hero-controls-accordion" :class="{ open: controlsOpen }">
          <Transition name="hero-controls-drawer-transition">
            <div v-if="controlsOpen" id="hero-controls-drawer" class="hero-controls-drawer">
              <IconButton
                button-class="hero-icon-btn hero-accordion-action editor-toggle"
                :active="editMode"
                :title="editMode ? 'Выключить режим редактирования' : 'Включить режим редактирования'"
                :aria-label="editMode ? 'Выключить режим редактирования' : 'Включить режим редактирования'"
                @click="toggleEditMode"
              >
                <Pencil class="ui-icon hero-action-icon" />
              </IconButton>

              <IconButton
                v-if="editMode"
                button-class="hero-icon-btn hero-accordion-action"
                title="Добавить группу"
                aria-label="Добавить группу"
                @click="addGroup"
              >
                <Plus class="ui-icon hero-action-icon" />
              </IconButton>

              <div class="hero-display-controls">
                <HeroDropdown
                  v-model="serviceCardView"
                  label="Вид"
                  aria-label="Режим отображения сервисов"
                  :options="servicePresentationOptions"
                />
                <HeroDropdown
                  v-model="serviceGroupingMode"
                  label=""
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

              <IconButton
                button-class="hero-icon-btn hero-accordion-action"
                title="Быстрый поиск сервисов (Ctrl/Cmd+K)"
                aria-label="Быстрый поиск сервисов"
                @click="openCommandPalette"
              >
                <Search class="ui-icon hero-action-icon" />
              </IconButton>

              <IconButton
                button-class="hero-icon-btn hero-accordion-action"
                :active="!isSidebarDetailed"
                :title="sidebarViewToggleTitle"
                :aria-label="sidebarViewToggleTitle"
                @click="toggleSidebarView"
              >
                <FolderTree class="ui-icon hero-action-icon" />
              </IconButton>

              <span
                v-if="editMode"
                class="hero-save-indicator hero-accordion-status"
                :class="saveStatus"
                role="status"
                :title="saveStatusLabel"
                :aria-label="saveStatusLabel"
              >
                <Circle class="ui-icon hero-save-icon" />
              </span>
            </div>
          </Transition>

          <button
            class="hero-controls-trigger"
            type="button"
            :aria-expanded="controlsOpen"
            aria-controls="hero-controls-drawer"
            :title="controlsOpen ? 'Скрыть панель действий' : 'Показать панель действий'"
            @click="controlsOpen = !controlsOpen"
          >
            <Wrench class="ui-icon hero-action-icon" />
            <ChevronLeft class="ui-icon hero-accordion-caret" :class="{ open: controlsOpen }" />
          </button>
        </div>

        <p v-if="editMode && saveError" class="editor-error hero-editor-error">{{ saveError }}</p>
      </div>
    </aside>
  </section>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { ChevronLeft, Circle, FolderTree, GitBranch, MapPin, Pencil, Plus, Search, SlidersHorizontal, Wrench } from 'lucide-vue-next'
import HeroDropdown from '../primitives/HeroDropdown.vue'
import HeroPageTabs from './HeroPageTabs.vue'
import IconButton from '../primitives/IconButton.vue'
import { useDashboardStore } from '../../stores/dashboardStore.js'

const dashboard = useDashboardStore()
const HERO_CONTROLS_OPEN_STORAGE_KEY = 'oko:hero-controls-open:v1'
const controlsOpen = ref(false)

const {
  editMode,
  isSidebarDetailed,
  isSidebarHidden,
  saveStatus,
  saveStatusLabel,
  saveError,
  sidebarViewToggleTitle,
  serviceCardView,
  serviceGroupingMode,
  serviceGroupingOptions,
  servicePresentationOptions,
  siteFilter,
  siteFilterOptions,
  toggleEditMode,
  addGroup,
  openCommandPalette,
  openSettingsPanel,
  toggleSidebarView,
} = dashboard

onMounted(() => {
  if (!window.localStorage) return
  const raw = window.localStorage.getItem(HERO_CONTROLS_OPEN_STORAGE_KEY)
  controlsOpen.value = raw === '1'
})

watch(
  () => controlsOpen.value,
  (value) => {
    if (!window.localStorage) return
    window.localStorage.setItem(HERO_CONTROLS_OPEN_STORAGE_KEY, value ? '1' : '0')
  }
)
</script>
