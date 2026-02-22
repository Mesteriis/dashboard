<template>
  <section class="hero-layout">
    <header class="hero panel hero-title-panel">
      <div
        id="hero-title-particles"
        class="hero-panel-particles"
        aria-hidden="true"
      ></div>
      <div class="hero-title-content">
        <HeroPageTabs />
      </div>
    </header>

    <aside class="panel hero-control-panel service-hero-controls">
      <div
        id="hero-controls-particles"
        class="hero-panel-particles"
        aria-hidden="true"
      ></div>
      <div class="hero-controls-content">
        <button
          class="ghost"
          type="button"
          :title="lanScanButtonHint"
          :aria-label="lanScanButtonHint"
          :disabled="lanScanActionBusy"
          @click="runLanScanNow"
        >
          {{
            lanScanState?.running
              ? "Поставить в очередь"
              : lanScanActionBusy
                ? "Запуск..."
                : "Сканировать сейчас"
          }}
        </button>
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
      </div>
    </aside>
  </section>

  <LanScanPanel />

  <section
    v-if="lanEventPopup.open"
    class="lan-event-popup"
    role="status"
    aria-live="polite"
  >
    <header class="lan-event-popup-header">
      <strong>{{ lanEventPopup.title }}</strong>
      <button class="ghost" type="button" @click="closeLanEventPopup">
        Закрыть
      </button>
    </header>
    <p class="lan-event-popup-message">{{ lanEventPopup.message }}</p>
    <p v-if="lanEventPopup.details" class="lan-event-popup-details">
      {{ lanEventPopup.details }}
    </p>
  </section>
</template>

<script setup>
import { computed } from "vue";
import { FolderTree, SlidersHorizontal } from "lucide-vue-next";
import LanScanPanel from "./LanScanPanel.vue";
import HeroPageTabs from "./HeroPageTabs.vue";
import IconButton from "../primitives/IconButton.vue";
import { useDashboardStore } from "../../stores/dashboardStore.js";

const dashboard = useDashboardStore();
const {
  closeLanEventPopup,
  isSidebarDetailed,
  lanEventPopup,
  lanScanActionBusy,
  lanScanState,
  openSettingsPanel,
  runLanScanNow,
  sidebarViewToggleTitle,
  toggleSidebarView,
} = dashboard;

const lanScanButtonHint = computed(() => {
  if (lanScanActionBusy.value) {
    return "Запрос на запуск уже отправлен.";
  }
  if (lanScanState.value?.running) {
    return "Сканирование уже выполняется. Нажмите, чтобы поставить повторный запуск в очередь.";
  }
  return "Запустить сканирование LAN сейчас.";
});
</script>
