<template>
  <section v-if="activeIndicatorWidget" class="panel indicator-tab-panel">
    <header class="indicator-tab-head">
      <div class="indicator-tab-title">
        <component
          :is="resolveWidgetIcon(activeIndicatorWidget)"
          class="ui-icon widget-icon"
        />
        <h2>{{ activeIndicatorWidget.title }}</h2>
      </div>
      <div class="indicator-tab-controls">
        <span class="item-type">{{ activeIndicatorWidget.type }}</span>
        <button
          class="ghost"
          type="button"
          @click="refreshWidget(activeIndicatorWidget.id)"
        >
          Обновить
        </button>
        <button class="ghost" type="button" @click="activeIndicatorViewId = ''">
          Закрыть вкладку
        </button>
      </div>
    </header>

    <div class="indicator-tab-content">
      <p
        v-if="widgetState(activeIndicatorWidget.id)?.error"
        class="widget-error"
      >
        {{ widgetState(activeIndicatorWidget.id)?.error }}
      </p>
      <p
        v-else-if="widgetState(activeIndicatorWidget.id)?.loading"
        class="widget-loading"
      >
        Обновление...
      </p>

      <template v-else-if="activeIndicatorWidget.type === 'stat_list'">
        <ul
          v-if="statListEntries(activeIndicatorWidget).length"
          class="widget-list"
        >
          <li
            v-for="entry in statListEntries(activeIndicatorWidget)"
            :key="entry.title + entry.value"
          >
            <span>{{ entry.title }}</span>
            <strong>{{ entry.value }}</strong>
          </li>
        </ul>
        <p v-else class="widget-empty">Нет данных</p>
      </template>

      <template v-else-if="activeIndicatorWidget.type === 'table'">
        <div
          v-if="tableRows(activeIndicatorWidget).length"
          class="widget-table-wrap"
        >
          <table class="widget-table">
            <thead>
              <tr>
                <th
                  v-for="column in activeIndicatorWidget.data.columns"
                  :key="column.key"
                >
                  {{ column.title }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(row, rowIndex) in tableRows(activeIndicatorWidget)"
                :key="rowIndex"
              >
                <td
                  v-for="column in activeIndicatorWidget.data.columns"
                  :key="column.key"
                >
                  {{ row?.[column.key] ?? "-" }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-else class="widget-empty">Нет данных</p>
      </template>
    </div>

    <div
      v-if="activeIndicatorWidget.data.actions?.length"
      class="widget-actions"
    >
      <button
        v-for="action in activeIndicatorWidget.data.actions"
        :key="action.id"
        class="ghost"
        type="button"
        :disabled="isActionBusy(activeIndicatorWidget.id, action.id)"
        @click="runWidgetAction(activeIndicatorWidget.id, action)"
      >
        {{ action.title }}
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { useDashboardStore } from "@/features/stores/dashboardStore";

const dashboard = useDashboardStore();

const {
  activeIndicatorWidget,
  activeIndicatorViewId,
  resolveWidgetIcon,
  refreshWidget,
  widgetState,
  statListEntries,
  tableRows,
  isActionBusy,
  runWidgetAction,
} = dashboard;
</script>
