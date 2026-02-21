<template>
  <BaseModal
    :open="lanHostModal.open"
    backdrop-class="lan-host-modal-backdrop"
    modal-class="lan-host-modal"
    @backdrop="closeLanHostModal"
  >
    <header class="lan-host-modal-header">
      <h3>{{ lanHostModal.host?.hostname || lanHostModal.host?.ip || 'Устройство LAN' }}</h3>
      <button class="ghost" type="button" @click="closeLanHostModal">Закрыть</button>
    </header>

    <div v-if="lanHostModal.host" class="lan-host-modal-body">
      <section class="lan-host-overview">
        <article class="lan-host-meta-card">
          <p>IP</p>
          <strong>{{ lanHostModal.host.ip }}</strong>
        </article>
        <article class="lan-host-meta-card">
          <p>Hostname</p>
          <strong>{{ lanHostModal.host.hostname || '—' }}</strong>
        </article>
        <article class="lan-host-meta-card">
          <p>MAC</p>
          <strong>{{ lanHostModal.host.mac_address || '—' }}</strong>
        </article>
        <article class="lan-host-meta-card">
          <p>Вендор</p>
          <strong>{{ lanHostModal.host.mac_vendor || '—' }}</strong>
        </article>
        <article class="lan-host-meta-card">
          <p>Тип устройства</p>
          <strong>{{ lanHostModal.host.device_type || '—' }}</strong>
        </article>
      </section>

      <section class="lan-host-section">
        <h4>Открытые порты</h4>
        <div v-if="lanHostModal.host.open_ports?.length" class="lan-port-chips">
          <span v-for="port in lanHostModal.host.open_ports" :key="port.port" class="lan-port-chip">
            {{ port.port }}
            <small v-if="port.service">{{ port.service }}</small>
          </span>
        </div>
        <p v-else class="widget-empty">Открытые порты не обнаружены.</p>
      </section>

      <section class="lan-host-section">
        <h4>HTTP/HTTPS профили</h4>
        <div v-if="lanHostModal.host.http_services?.length" class="lan-http-grid">
          <article
            v-for="endpoint in lanHostModal.host.http_services"
            :key="`${endpoint.scheme}:${endpoint.port}:${endpoint.url}`"
            class="lan-http-card"
            :class="{ error: Boolean(endpoint.error) }"
          >
            <header class="lan-http-head">
              <strong>{{ endpoint.scheme.toUpperCase() }}:{{ endpoint.port }}</strong>
              <span>{{ formatLanHttpStatus(endpoint) }}</span>
            </header>
            <a class="lan-http-url" :href="endpoint.url" target="_blank" rel="noopener noreferrer" @click.stop>
              {{ endpoint.url }}
            </a>
            <p class="lan-http-title">{{ endpoint.title || 'Title не найден' }}</p>
            <p class="lan-http-description">{{ endpoint.description || 'Описание не найдено' }}</p>
            <p v-if="endpoint.server" class="lan-http-server">Server: {{ endpoint.server }}</p>
            <p v-if="endpoint.error" class="widget-error">{{ endpoint.error }}</p>
          </article>
        </div>
        <p v-else class="widget-empty">HTTP/HTTPS endpoint не обнаружен.</p>
      </section>

      <section class="lan-host-section">
        <h4>Сервисы из dashboard</h4>
        <div v-if="lanHostModal.host.dashboard_items?.length" class="lan-service-links">
          <a
            v-for="service in lanHostModal.host.dashboard_items"
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
        <p v-else class="widget-empty">Связанные сервисы не найдены.</p>
      </section>
    </div>
  </BaseModal>
</template>

<script setup>
import BaseModal from '../primitives/BaseModal.vue'
import { useDashboardStore } from '../../stores/dashboardStore.js'

const dashboard = useDashboardStore()
const { lanHostModal, closeLanHostModal, formatLanHttpStatus } = dashboard
</script>
