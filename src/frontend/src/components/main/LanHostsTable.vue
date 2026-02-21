<template>
  <div class="lan-table-wrap">
    <table class="lan-table">
      <thead>
        <tr>
          <th>IP</th>
          <th>Имя</th>
          <th>MAC</th>
          <th>Вендор</th>
          <th>Тип устройства</th>
          <th>Открытые порты</th>
          <th>Сервисы dashboard</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="host in lanHosts" :key="host.ip" class="lan-host-row" @click="openLanHostModal(host)">
          <td>{{ host.ip }}</td>
          <td>{{ host.hostname || '—' }}</td>
          <td>{{ host.mac_address || '—' }}</td>
          <td>{{ host.mac_vendor || '—' }}</td>
          <td>{{ host.device_type || '—' }}</td>
          <td>{{ lanPortsLabel(host) }}</td>
          <td>
            <div v-if="host.dashboard_items?.length" class="lan-service-links">
              <a
                v-for="service in host.dashboard_items"
                :key="service.id"
                class="lan-service-link"
                :href="service.url"
                target="_blank"
                rel="noopener noreferrer"
                @click.stop
              >
                {{ service.title }}
              </a>
            </div>
            <span v-else>—</span>
          </td>
        </tr>
        <tr v-if="!lanHosts.length">
          <td colspan="7" class="lan-empty">Хосты не обнаружены. Запустите сканирование вручную.</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { useDashboardStore } from '../../stores/dashboardStore.js'

const dashboard = useDashboardStore()
const { lanHosts, lanPortsLabel, openLanHostModal } = dashboard
</script>
