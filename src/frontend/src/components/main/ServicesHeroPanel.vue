<template>
  <section class="hero-layout">
    <header class="hero panel hero-title-panel">
      <div id="hero-title-particles" class="hero-panel-particles" aria-hidden="true"></div>
      <div class="hero-title-content">
        <h1>{{ activePage.title }}</h1>
      </div>
    </header>

    <aside class="panel hero-control-panel service-hero-controls" :class="{ active: editMode }">
      <div id="hero-controls-particles" class="hero-panel-particles" aria-hidden="true"></div>
      <div class="hero-controls-content">
        <IconButton
          button-class="hero-icon-btn editor-toggle"
          :active="editMode"
          :title="editMode ? 'Выключить режим редактирования' : 'Включить режим редактирования'"
          :aria-label="editMode ? 'Выключить режим редактирования' : 'Включить режим редактирования'"
          @click="toggleEditMode"
        >
          <Pencil class="ui-icon hero-action-icon" />
        </IconButton>

        <IconButton v-if="editMode" button-class="hero-icon-btn" title="Добавить группу" aria-label="Добавить группу" @click="addGroup">
          <Plus class="ui-icon hero-action-icon" />
        </IconButton>

        <IconButton
          button-class="hero-icon-btn"
          :active="isIconCardView"
          :title="isIconCardView ? 'Переключить на карточки' : 'Переключить на иконки'"
          :aria-label="isIconCardView ? 'Переключить на карточки' : 'Переключить на иконки'"
          @click="toggleServiceCardView"
        >
          <Layers class="ui-icon hero-action-icon" />
        </IconButton>

        <IconButton
          button-class="hero-icon-btn"
          :active="isSidebarIconOnly"
          :title="isSidebarIconOnly ? 'Показать полную боковую панель' : 'Показать только иконки в боковой панели'"
          :aria-label="isSidebarIconOnly ? 'Показать полную боковую панель' : 'Показать только иконки в боковой панели'"
          @click="toggleSidebarView"
        >
          <FolderTree class="ui-icon hero-action-icon" />
        </IconButton>

        <span v-if="editMode" class="hero-save-indicator" :class="saveStatus" role="status" :title="saveStatusLabel" :aria-label="saveStatusLabel">
          <Circle class="ui-icon hero-save-icon" />
        </span>

        <p v-if="editMode && saveError" class="editor-error hero-editor-error">{{ saveError }}</p>
      </div>
    </aside>
  </section>
</template>

<script setup>
import { Circle, FolderTree, Layers, Pencil, Plus } from 'lucide-vue-next'
import IconButton from '../primitives/IconButton.vue'
import { useDashboardStore } from '../../stores/dashboardStore.js'

const dashboard = useDashboardStore()

const {
  activePage,
  editMode,
  isIconCardView,
  isSidebarIconOnly,
  saveStatus,
  saveStatusLabel,
  saveError,
  toggleEditMode,
  addGroup,
  toggleServiceCardView,
  toggleSidebarView,
} = dashboard
</script>
