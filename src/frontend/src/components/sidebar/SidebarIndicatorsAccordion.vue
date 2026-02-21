<template>
  <div class="sidebar-stats-accordion" aria-label="Индикаторы">
    <button class="sidebar-stats-toggle" type="button" aria-controls="sidebar-stats-panel" :aria-expanded="statsExpanded" @click="statsExpanded = !statsExpanded">
      <span class="sidebar-stats-toggle-text">Индикаторы</span>
      <span class="sidebar-stats-toggle-values">{{ sidebarIndicatorSummary }}</span>
      <span class="sidebar-stats-toggle-caret" :class="{ open: statsExpanded }">▴</span>
    </button>

    <div id="sidebar-stats-panel" class="sidebar-stats-panel" :class="{ open: statsExpanded }">
      <div v-if="sidebarIndicators.length" class="sidebar-indicators">
        <article
          v-for="widget in sidebarIndicators"
          :key="widget.id"
          class="sidebar-indicator"
          :class="{ interactive: isLargeIndicator(widget), active: activeIndicatorWidget?.id === widget.id }"
          @click="selectSidebarIndicator(widget)"
        >
          <header class="widget-head sidebar-indicator-head">
            <div class="widget-title">
              <component :is="resolveWidgetIcon(widget)" class="ui-icon widget-icon" />
              <h3>{{ widget.title }}</h3>
            </div>
            <span class="item-type">{{ widget.type }}</span>
          </header>

          <p v-if="widgetState(widget.id)?.error" class="widget-error">{{ widgetState(widget.id)?.error }}</p>
          <p v-else-if="widgetState(widget.id)?.loading" class="widget-loading">Обновление...</p>

          <template v-else-if="widget.type === 'stat_card'">
            <p class="widget-value sidebar-indicator-value">{{ statCardValue(widget) }}</p>
            <p class="widget-subtitle">{{ statCardSubtitle(widget) }}</p>
            <p v-if="statCardTrend(widget)" class="widget-trend">{{ statCardTrend(widget) }}</p>
          </template>

          <template v-else-if="widget.type === 'stat_list'">
            <ul v-if="indicatorPreviewEntries(widget).length" class="widget-list sidebar-list-preview">
              <li v-for="entry in indicatorPreviewEntries(widget)" :key="entry.title + entry.value">
                <span>{{ entry.title }}</span>
                <strong>{{ entry.value }}</strong>
              </li>
            </ul>
            <p v-else class="widget-empty">Нет данных</p>
            <p class="sidebar-indicator-hint">Нажмите, чтобы открыть во вкладке</p>
          </template>

          <template v-else-if="widget.type === 'table'">
            <p class="widget-subtitle">Строк: {{ tableRows(widget).length }}</p>
            <p class="sidebar-indicator-hint">Нажмите, чтобы открыть во вкладке</p>
          </template>

          <p v-else class="widget-empty">Неподдерживаемый тип виджета</p>

          <div v-if="widget.data.actions?.length || isLargeIndicator(widget)" class="widget-actions sidebar-indicator-actions">
            <button v-if="isLargeIndicator(widget)" class="ghost" type="button" @click.stop="openIndicatorView(widget.id)">Открыть вкладку</button>
            <button
              v-for="action in widget.data.actions || []"
              :key="action.id"
              class="ghost"
              type="button"
              :disabled="isActionBusy(widget.id, action.id)"
              @click.stop="runWidgetAction(widget.id, action)"
            >
              {{ action.title }}
            </button>
          </div>
        </article>
      </div>
      <p v-else class="widget-empty">Для выбранной страницы индикаторы не настроены.</p>
    </div>
  </div>
</template>

<script setup>
import { useDashboardStore } from '../../stores/dashboardStore.js'

const dashboard = useDashboardStore()

const {
  statsExpanded,
  sidebarIndicatorSummary,
  sidebarIndicators,
  isLargeIndicator,
  activeIndicatorWidget,
  selectSidebarIndicator,
  resolveWidgetIcon,
  widgetState,
  statCardValue,
  statCardSubtitle,
  statCardTrend,
  indicatorPreviewEntries,
  tableRows,
  openIndicatorView,
  isActionBusy,
  runWidgetAction,
} = dashboard
</script>
