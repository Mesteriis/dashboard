<template>
  <section class="hero-layout">
    <header class="hero panel hero-title-panel">
      <div
        id="hero-title-particles"
        class="hero-panel-particles"
        aria-hidden="true"
      ></div>
      <div class="hero-title-content">
        <HeroPageTabs variant="home" />
      </div>
    </header>

    <aside class="panel hero-control-panel service-hero-controls">
      <div
        id="hero-controls-particles"
        class="hero-panel-particles"
        aria-hidden="true"
      ></div>
      <div class="hero-controls-content">
        <div class="hero-controls-drawer">
          <IconButton
            button-class="hero-icon-btn hero-accordion-action hero-lan-scan-btn"
            :active="Boolean(lanScanState?.running)"
            :title="lanScanButtonHint"
            :aria-label="lanScanButtonHint"
            :disabled="lanScanActionBusy"
            @click="runLanScanNow"
          >
            <Radar class="ui-icon hero-action-icon" />
          </IconButton>

          <IconButton
            button-class="hero-icon-btn hero-accordion-action"
            title="Открыть Pleiad"
            aria-label="Открыть Pleiad"
            @click="openPleiad"
          >
            <Orbit class="ui-icon hero-action-icon" />
          </IconButton>
        </div>
      </div>
    </aside>
  </section>
</template>

<script setup>
import { computed } from "vue";
import { Orbit, Radar } from "lucide-vue-next";
import HeroPageTabs from "./HeroPageTabs.vue";
import IconButton from "../primitives/IconButton.vue";
import { dispatchOpenPleiad } from "../../services/pleiadNavigation.js";
import { useDashboardStore } from "../../stores/dashboardStore.js";

const dashboard = useDashboardStore();
const {
  lanScanActionBusy,
  lanScanState,
  runLanScanNow,
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

function openPleiad() {
  dispatchOpenPleiad();
}
</script>
