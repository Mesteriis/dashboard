<template>
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
import LanScanPanel from "./LanScanPanel.vue";
import { useDashboardStore } from "../../stores/dashboardStore.js";

const dashboard = useDashboardStore();
const {
  closeLanEventPopup,
  lanEventPopup,
} = dashboard;
</script>
