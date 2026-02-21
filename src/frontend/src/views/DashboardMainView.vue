<template>
  <main
    :key="activePage?.id || 'empty'"
    class="page"
    :class="{ 'indicator-open': Boolean(activeIndicatorWidget), 'page--lan': isLanPage && !activeIndicatorWidget }"
  >
    <section v-if="loadingConfig" class="panel status-panel">
      <h2>Загрузка конфигурации...</h2>
      <p class="subtitle">Получаем dashboard-модель из backend.</p>
    </section>

    <section v-else-if="configError" class="panel status-panel error-state">
      <h2>Ошибка загрузки конфигурации</h2>
      <p class="subtitle">{{ configError }}</p>
      <button class="ghost" type="button" @click="loadConfig">Повторить</button>
    </section>

    <template v-else-if="activePage">
      <IndicatorTabPanel v-if="activeIndicatorWidget" />

      <template v-else>
        <LanPageView v-if="isLanPage" />

        <template v-else>
          <ServicesHeroPanel />
          <ServicesGroupsPanel />
        </template>
      </template>
    </template>

    <section v-else class="panel status-panel">
      <h2>Нет доступных страниц</h2>
      <p class="subtitle">Проверьте `layout.pages` в `dashboard.yaml`.</p>
    </section>
  </main>
</template>

<script setup>
import IndicatorTabPanel from '../components/main/IndicatorTabPanel.vue'
import LanPageView from '../components/main/LanPageView.vue'
import ServicesGroupsPanel from '../components/main/ServicesGroupsPanel.vue'
import ServicesHeroPanel from '../components/main/ServicesHeroPanel.vue'
import { useDashboardStore } from '../stores/dashboardStore.js'

const dashboard = useDashboardStore()
const { activePage, activeIndicatorWidget, loadingConfig, configError, isLanPage, loadConfig } = dashboard
</script>
