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
          :disabled="lanScanActionBusy || Boolean(lanScanState?.running)"
          @click="runLanScanNow"
        >
          {{
            lanScanState?.running
              ? "Сканирование..."
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
</template>

<script setup>
import { FolderTree, SlidersHorizontal } from "lucide-vue-next";
import LanScanPanel from "./LanScanPanel.vue";
import HeroPageTabs from "./HeroPageTabs.vue";
import IconButton from "../primitives/IconButton.vue";
import { useDashboardStore } from "../../stores/dashboardStore.js";

const dashboard = useDashboardStore();
const {
  isSidebarDetailed,
  lanScanActionBusy,
  lanScanState,
  openSettingsPanel,
  runLanScanNow,
  sidebarViewToggleTitle,
  toggleSidebarView,
} = dashboard;
</script>
