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
        <span
          class="item-type indicator-type-icon"
          :title="widgetTypeMeta(activeIndicatorWidget).label"
        >
          {{ widgetTypeMeta(activeIndicatorWidget).icon }}
        </span>
        <button
          v-if="canCopyActiveIndicator(activeIndicatorWidget)"
          class="ghost indicator-tab-icon-btn"
          type="button"
          :title="isCopied ? 'Скопировано' : copyButtonTitle(activeIndicatorWidget)"
          @click="copyActiveIndicatorValue"
        >
          {{ isCopied ? "✓" : "⧉" }}
        </button>
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
        <nav
          v-if="indicatorTabs(activeIndicatorWidget).length > 1"
          class="indicator-tab-mode-switch"
          role="tablist"
          aria-label="Режим индикатора"
        >
          <button
            v-for="tab in indicatorTabs(activeIndicatorWidget)"
            :key="`${activeIndicatorWidget.id}:${tab.id}`"
            class="indicator-tab-mode-btn"
            :class="{ active: activeIndicatorTabId(activeIndicatorWidget) === tab.id }"
            type="button"
            role="tab"
            :aria-selected="activeIndicatorTabId(activeIndicatorWidget) === tab.id"
            @click="setIndicatorTab(activeIndicatorWidget, tab.id)"
          >
            {{ tab.title }}
          </button>
        </nav>
        <UiFieldset
          v-if="
            hasStatListHeader(
              activeIndicatorWidget,
              resolveActiveTabMapping(activeIndicatorWidget),
            )
          "
          :legend="fieldsetLegend(activeIndicatorWidget)"
        >
          <p
            class="widget-value"
            :class="{ 'widget-value-metric': isMetricValue(resolveActivePrimaryValue(activeIndicatorWidget)) }"
          >
            {{ resolveActivePrimaryValue(activeIndicatorWidget) }}
          </p>
          <p class="widget-subtitle">
            {{
              statCardSubtitleByMapping(
                activeIndicatorWidget,
                resolveActiveTabMapping(activeIndicatorWidget),
              )
            }}
          </p>
          <p
            v-if="
              statCardTrendByMapping(
                activeIndicatorWidget,
                resolveActiveTabMapping(activeIndicatorWidget),
              )
            "
            class="widget-trend"
          >
            {{
              statCardTrendByMapping(
                activeIndicatorWidget,
                resolveActiveTabMapping(activeIndicatorWidget),
              )
            }}
          </p>
        </UiFieldset>
        <ul
          v-if="
            statListEntriesByMapping(
              activeIndicatorWidget,
              resolveActiveTabMapping(activeIndicatorWidget),
            ).length
          "
          class="widget-list"
        >
          <li
            v-for="
              entry in statListEntriesByMapping(
                activeIndicatorWidget,
                resolveActiveTabMapping(activeIndicatorWidget),
              )
            "
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
import { computed, ref } from "vue";
import { useDashboardStore } from "@/features/stores/dashboardStore";
import type { DashboardWidget } from "@/features/stores/dashboard/storeTypes";
import UiFieldset from "@/ui/surfaces/UiFieldset.vue";

const dashboard = useDashboardStore();

const {
  activeIndicatorWidget,
  activeIndicatorViewId,
  resolveWidgetIcon,
  refreshWidget,
  widgetState,
  statCardValueByMapping,
  statCardSubtitleByMapping,
  statCardTrendByMapping,
  statListEntriesByMapping,
  tableRows,
  isActionBusy,
  runWidgetAction,
} = dashboard;

interface IndicatorTabConfig {
  id: string;
  title: string;
  mapping?: Record<string, unknown>;
}

interface WidgetTypeMeta {
  icon: string;
  label: string;
}

const activeTabsByWidget = ref<Record<string, string>>({});
const copiedUntil = ref(0);

const WIDGET_TYPE_META: Record<string, WidgetTypeMeta> = {
  stat_card: { icon: "◉", label: "stat_card" },
  stat_list: { icon: "☰", label: "stat_list" },
  table: { icon: "▦", label: "table" },
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function indicatorTabs(widget: DashboardWidget): IndicatorTabConfig[] {
  const rawTabs = Array.isArray(widget?.data?.tabs) ? widget.data.tabs : [];
  const parsed: IndicatorTabConfig[] = [];
  for (const rawTab of rawTabs) {
    const tab = asRecord(rawTab);
    if (!tab) continue;
    const id = String(tab.id || "").trim();
    if (!id) continue;
    const title = String(tab.title || id).trim();
    const mapping = asRecord(tab.mapping) || undefined;
    parsed.push({
      id,
      title,
      ...(mapping ? { mapping } : {}),
    });
  }
  return parsed;
}

function widgetTypeMeta(widget: DashboardWidget): WidgetTypeMeta {
  const type = String(widget?.type || "").trim();
  return WIDGET_TYPE_META[type] || {
    icon: "•",
    label: type || "widget",
  };
}

function activeIndicatorTabId(widget: DashboardWidget): string {
  const tabs = indicatorTabs(widget);
  if (!tabs.length) return "";
  const current = String(activeTabsByWidget.value[widget.id] || "").trim();
  if (tabs.some((tab) => tab.id === current)) return current;
  return tabs[0].id;
}

function setIndicatorTab(widget: DashboardWidget, tabId: string): void {
  activeTabsByWidget.value = {
    ...activeTabsByWidget.value,
    [widget.id]: tabId,
  };
}

function resolveActiveTabMapping(widget: DashboardWidget): Record<string, unknown> {
  const tabs = indicatorTabs(widget);
  const activeTabId = activeIndicatorTabId(widget);
  const activeTab = tabs.find((tab) => tab.id === activeTabId);
  if (activeTab?.mapping) return activeTab.mapping;
  return (widget?.data?.mapping || {}) as Record<string, unknown>;
}

function hasStatListHeader(
  widget: DashboardWidget,
  mappingOverride?: Record<string, unknown>,
): boolean {
  const mapping = mappingOverride || (widget?.data?.mapping as Record<string, unknown> | undefined);
  if (!mapping || typeof mapping !== "object") return false;
  return Boolean(mapping.value || mapping.subtitle || mapping.trend);
}

function canCopyActiveIndicator(widget: DashboardWidget): boolean {
  const type = String(widget?.type || "").trim();
  return type === "stat_card" || type === "stat_list";
}

function copyButtonTitle(widget: DashboardWidget): string {
  const custom = String(widget?.data?.copyTitle || "").trim();
  return custom || "Копировать значение";
}

function fieldsetLegend(widget: DashboardWidget): string {
  const custom = String(widget?.data?.fieldsetLegend || "").trim();
  return custom || "Текущий egress IP";
}

const isCopied = computed<boolean>(() => copiedUntil.value > Date.now());

function resolveActivePrimaryValue(widget: DashboardWidget): unknown {
  const type = String(widget?.type || "").trim();
  if (type === "stat_list") {
    return statCardValueByMapping(widget, resolveActiveTabMapping(widget));
  }
  return statCardValueByMapping(widget, widget?.data?.mapping || {});
}

function isMetricValue(value: unknown): boolean {
  const token = String(value ?? "").toLowerCase();
  if (!token || token === "—") return false;
  return token.includes("mbps") || token.includes(" ms");
}

async function copyActiveIndicatorValue(): Promise<void> {
  if (!activeIndicatorWidget.value) return;
  if (!canCopyActiveIndicator(activeIndicatorWidget.value)) return;
  if (typeof navigator === "undefined" || !navigator.clipboard?.writeText) return;
  const value = String(resolveActivePrimaryValue(activeIndicatorWidget.value) ?? "").trim();
  if (!value || value === "—") return;
  try {
    await navigator.clipboard.writeText(value);
    copiedUntil.value = Date.now() + 1400;
  } catch {
    return;
  }
}
</script>
