<template>
  <section class="settings-section">
    <header class="settings-section-header">
      <h2>Быстрые действия</h2>
      <p>Действия для быстрого управления интерфейсом</p>
    </header>

    <div class="settings-section-content">
      <div class="settings-actions-list">
        <button
          class="settings-action-row"
          type="button"
          @click="handleToggleSidebar"
        >
          <div class="settings-action-row-content">
            <PanelLeft class="ui-icon settings-action-icon" />
            <div class="settings-action-row-text">
              <span class="settings-action-row-title">
                {{ isSidebarHidden ? "Показать меню" : "Скрыть меню" }}
              </span>
              <span class="settings-action-row-desc">
                Переключение видимости боковой панели
              </span>
            </div>
          </div>
          <ChevronRight class="ui-icon settings-action-caret" />
        </button>

        <button
          class="settings-action-row"
          type="button"
          @click="handleToggleEditMode"
        >
          <div class="settings-action-row-content">
            <Pencil class="ui-icon settings-action-icon" />
            <div class="settings-action-row-text">
              <span class="settings-action-row-title">
                {{ editMode ? "Выключить edit mode" : "Включить edit mode" }}
              </span>
              <span class="settings-action-row-desc">
                Режим редактирования панели
              </span>
            </div>
          </div>
          <ChevronRight class="ui-icon settings-action-caret" />
        </button>

        <button
          class="settings-action-row"
          type="button"
          @click="handleOpenSearch"
        >
          <div class="settings-action-row-content">
            <Search class="ui-icon settings-action-icon" />
            <div class="settings-action-row-text">
              <span class="settings-action-row-title">
                Открыть поиск
              </span>
              <span class="settings-action-row-desc">
                Ctrl/Cmd + K
              </span>
            </div>
          </div>
          <ChevronRight class="ui-icon settings-action-caret" />
        </button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ChevronRight, PanelLeft, Pencil, Search } from "lucide-vue-next";
import { useDashboardStore } from "@/features/stores/dashboardStore";

const dashboard = useDashboardStore();
const {
  editMode,
  isSidebarHidden,
  openCommandPalette,
  toggleEditMode,
  toggleSidebarView,
} = dashboard;

function handleToggleSidebar(): void {
  toggleSidebarView();
}

function handleToggleEditMode(): void {
  toggleEditMode();
}

function handleOpenSearch(): void {
  openCommandPalette();
}
</script>
