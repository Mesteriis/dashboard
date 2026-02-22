<template>
  <section class="panel lan-scan-panel">
    <p v-if="lanScanError" class="widget-error">{{ lanScanError }}</p>
    <p v-else-if="lanScanLoading && !lanScanState" class="widget-loading">
      Загрузка состояния сканера...
    </p>

    <template v-else>
      <section class="lan-summary-grid">
        <article class="lan-summary-card">
          <p>Статус</p>
          <strong>{{
            lanScanState?.running
              ? "Сканирование"
              : lanScanState?.queued
                ? "В очереди"
                : "Ожидание"
          }}</strong>
        </article>
        <article class="lan-summary-card">
          <p>Хостов найдено</p>
          <strong>{{ lanHosts.length }}</strong>
        </article>
        <article class="lan-summary-card">
          <p>Проверено IP</p>
          <strong>{{ lanScanState?.result?.scanned_hosts ?? 0 }}</strong>
        </article>
        <article class="lan-summary-card">
          <p>Проверено портов</p>
          <strong>{{ lanScanState?.result?.scanned_ports ?? 0 }}</strong>
        </article>
        <article class="lan-summary-card">
          <p>Длительность</p>
          <strong>{{
            formatLanDuration(lanScanState?.result?.duration_ms)
          }}</strong>
        </article>
        <article class="lan-summary-card">
          <p>Последний старт</p>
          <strong>{{ formatLanMoment(lanScanState?.last_started_at) }}</strong>
        </article>
        <article class="lan-summary-card">
          <p>Следующий запуск</p>
          <strong>{{ formatLanMoment(lanScanState?.next_run_at) }}</strong>
        </article>
      </section>

      <p class="subtitle lan-meta-line">Подсети: {{ lanCidrsLabel }}</p>
      <p class="subtitle lan-meta-line">
        Планировщик: {{ lanScanState?.scheduler || "asyncio" }} · интервал
        {{ lanScanState?.interval_sec || 1020 }} сек
      </p>
      <p class="subtitle lan-meta-line">
        Файл результата: {{ lanScanState?.result?.source_file || "не создан" }}
      </p>
      <p v-if="lanScanState?.last_error" class="widget-error">
        Ошибка сканирования: {{ lanScanState.last_error }}
      </p>

      <LanHostsTable />
    </template>
  </section>
</template>

<script setup>
import LanHostsTable from "./LanHostsTable.vue";
import { useDashboardStore } from "../../stores/dashboardStore.js";

const dashboard = useDashboardStore();

const {
  lanScanError,
  lanScanLoading,
  lanScanState,
  lanHosts,
  lanCidrsLabel,
  formatLanDuration,
  formatLanMoment,
} = dashboard;
</script>
