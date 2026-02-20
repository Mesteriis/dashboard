<template>
  <div class="shell">
    <img class="center-emblem" :src="EMBLEM_SRC" alt="" aria-hidden="true" />

    <div class="app-shell">
      <aside class="sidebar">
        <div id="sidebar-particles" class="sidebar-particles" aria-hidden="true"></div>
        <div class="sidebar-content">
          <div class="brand">
            <img :src="EMBLEM_SRC" alt="Oko" />
            <div>
              <p class="brand-title">Oko</p>
              <p class="brand-subtitle">Your Infrastructure in Sight</p>
            </div>
          </div>

          <nav class="tab-list" role="tablist" aria-label="Разделы">
            <button
              v-for="tab in tabs"
              :key="tab.id"
              class="tab-btn"
              :class="{ active: activeTab === tab.id }"
              type="button"
              role="tab"
              :aria-selected="activeTab === tab.id"
              @click="activeTab = tab.id"
            >
              <span class="tab-label">{{ tab.label }}</span>
              <span class="tab-hint">{{ tab.hint }}</span>
            </button>
          </nav>

          <div class="sidebar-stats" aria-label="Сводка">
            <article class="stat-card">
              <p class="label">Сервисы</p>
              <p class="value">{{ active.metrics.services }}</p>
            </article>
            <article class="stat-card">
              <p class="label">Состояние</p>
              <p class="value">{{ active.metrics.health }}</p>
            </article>
          </div>
        </div>
      </aside>

      <main :key="active.id" class="page">
        <header class="hero">
          <p class="eyebrow">{{ active.label }}</p>
          <h1>{{ active.title }}</h1>
          <p class="subtitle">{{ active.subtitle }}</p>
        </header>

        <section class="content-grid">
          <article class="panel">
            <h2>{{ active.primaryTitle }}</h2>
            <p>{{ active.primaryText }}</p>
            <ul>
              <li v-for="item in active.items" :key="item">{{ item }}</li>
            </ul>
          </article>

          <article class="panel">
            <h2>Статус</h2>
            <p>Текущее состояние выбранной вкладки.</p>
            <div class="status-grid">
              <div v-for="entry in active.status" :key="entry.name" class="status-item">
                <span>{{ entry.name }}</span>
                <strong>{{ entry.value }}</strong>
              </div>
            </div>
          </article>
        </section>
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'

const EMBLEM_SRC = '/static/img/emblem-mark.png'

const tabs = [
  {
    id: 'routes',
    label: 'Маршруты',
    hint: 'HTTP/L4',
    title: 'Управление маршрутами',
    subtitle: 'Базовая структура для проксирования доменов и внутренних сервисов.',
    primaryTitle: 'Список маршрутов',
    primaryText: 'Минимальный блок для сохранения общей структуры старого интерфейса.',
    items: [
      'api.example.com -> 10.0.0.10:8080',
      'admin.example.com -> 10.0.0.20:3000',
      'ssh.example.com -> 10.0.0.30:22',
    ],
    status: [
      { name: 'Активно', value: '24' },
      { name: 'Отключено', value: '3' },
      { name: 'Ошибки', value: '0' },
    ],
    metrics: {
      services: '27',
      health: 'Stable',
    },
  },
  {
    id: 'tunnels',
    label: 'Туннели',
    hint: 'Cloudflare',
    title: 'Cloudflare Tunnel',
    subtitle: 'Упрощенный экран для контроля публичных туннелей и hostnames.',
    primaryTitle: 'Туннели',
    primaryText: 'Здесь остается только демонстрационный каркас вкладки.',
    items: ['home.example.com', 'cdn.example.com', 'ssh.example.com'],
    status: [
      { name: 'Подключение', value: 'Online' },
      { name: 'Туннели', value: '3' },
      { name: 'Fallback', value: 'Enabled' },
    ],
    metrics: {
      services: '3',
      health: 'Online',
    },
  },
  {
    id: 'inbound',
    label: 'Входящие',
    hint: 'VPN / Edge',
    title: 'Входящие подключения',
    subtitle: 'Базовая вкладка для VPN и внешних точек входа.',
    primaryTitle: 'Источники входящего трафика',
    primaryText: 'Разметка оставлена для дальнейшего наполнения реальными данными.',
    items: ['WireGuard Server #1', 'WireGuard Server #2', 'Edge Gateway: Active'],
    status: [
      { name: 'VPN серверы', value: '2' },
      { name: 'Клиенты', value: '16' },
      { name: 'Peer links', value: '5' },
    ],
    metrics: {
      services: '23',
      health: 'Healthy',
    },
  },
  {
    id: 'settings',
    label: 'Настройки',
    hint: 'Runtime',
    title: 'Runtime настройки',
    subtitle: 'Минимальная секция с общей визуальной частью для системных настроек.',
    primaryTitle: 'Параметры системы',
    primaryText: 'Тут можно оставить глобальные флаги и конфиг в дальнейшем.',
    items: ['feature_tunnel_enabled = true', 'feature_vpn_enabled = true', 'dashboard_port = 8090'],
    status: [
      { name: 'Config file', value: 'Loaded' },
      { name: 'Version', value: '0.1.0' },
      { name: 'Mode', value: 'Production' },
    ],
    metrics: {
      services: 'Core',
      health: 'Ready',
    },
  },
]

const activeTab = ref('routes')

const active = computed(() => tabs.find((tab) => tab.id === activeTab.value) || tabs[0])

onMounted(() => {
  if (!window.particlesJS) return

  window.particlesJS('sidebar-particles', {
    particles: {
      number: { value: 44, density: { enable: true, value_area: 700 } },
      color: { value: '#44e3cf' },
      shape: { type: 'circle' },
      opacity: { value: 0.22, random: true },
      size: { value: 2.2, random: true },
      line_linked: {
        enable: true,
        distance: 120,
        color: '#2dd4bf',
        opacity: 0.14,
        width: 1,
      },
      move: { enable: true, speed: 0.6 },
    },
    interactivity: {
      events: { onhover: { enable: false }, onclick: { enable: false }, resize: true },
    },
    retina_detect: true,
  })
})
</script>
