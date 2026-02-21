<template>
  <section class="hero-layout">
    <header class="hero panel hero-title-panel">
      <div id="hero-title-particles" class="hero-panel-particles" aria-hidden="true"></div>
      <div class="hero-title-content">
        <h1>Локальная сеть</h1>
      </div>
    </header>

    <aside class="panel hero-control-panel">
      <div id="hero-controls-particles" class="hero-panel-particles" aria-hidden="true"></div>
      <div class="hero-controls-content">
        <button class="ghost" type="button" :disabled="lanScanActionBusy || Boolean(lanScanState?.running)" @click="runLanScanNow">
          {{ lanScanState?.running ? 'Сканирование...' : lanScanActionBusy ? 'Запуск...' : 'Сканировать сейчас' }}
        </button>
      </div>
    </aside>
  </section>

  <LanScanPanel />
</template>

<script setup>
import LanScanPanel from './LanScanPanel.vue'
import { useDashboardStore } from '../../stores/dashboardStore.js'

const dashboard = useDashboardStore()
const { lanScanActionBusy, lanScanState, runLanScanNow } = dashboard
</script>
