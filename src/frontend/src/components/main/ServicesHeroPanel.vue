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
                title="Панель настроек"
                aria-label="Открыть панель настроек"
                @click="openSettingsPanel"
              >
                <SlidersHorizontal class="ui-icon hero-action-icon" />
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
import { ChevronLeft, Circle, FolderTree, Pencil, Plus, Search, SlidersHorizontal, Wrench } from 'lucide-vue-next'
import HeroPageTabs from './HeroPageTabs.vue'
import IconButton from '../primitives/IconButton.vue'
import { useDashboardStore } from '../../stores/dashboardStore.js'

const dashboard = useDashboardStore()
const HERO_CONTROLS_OPEN_STORAGE_KEY = 'oko:hero-controls-open:v1'
const controlsOpen = ref(false)

const {
  editMode,
  isSidebarDetailed,
  saveStatus,
  saveStatusLabel,
  saveError,
  sidebarViewToggleTitle,
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
