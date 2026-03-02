<template>
  <div class="sidebar-stats-accordion" aria-label="Индикаторы">
    <button
      class="sidebar-stats-toggle"
      type="button"
      aria-controls="sidebar-stats-panel"
      :aria-expanded="statsExpanded"
      @click="statsExpanded = !statsExpanded"
    >
      <span class="sidebar-stats-toggle-text">Индикаторы</span>
      <span class="sidebar-stats-toggle-values">{{
        sidebarIndicatorSummary
      }}</span>
      <span class="sidebar-stats-toggle-caret" :class="{ open: statsExpanded }"
        >▴</span
      >
    </button>

    <div
      id="sidebar-stats-panel"
      class="sidebar-stats-panel"
      :class="{ open: statsExpanded }"
    >
      <div v-if="sidebarIndicators.length" class="sidebar-indicators">
        <UiCollapsibleCard
          v-for="widget in sidebarIndicators"
          :key="widget.id"
          class="sidebar-indicator"
          :class="{ active: activeIndicatorWidget?.id === widget.id }"
          :model-value="isWidgetExpanded(widget.id)"
          @update:model-value="onWidgetExpandedChange(widget.id, $event)"
          accordion
          :accordion-group="INDICATORS_ACCORDION_GROUP"
          :background-mode="widgetBackgroundMode(widget)"
          :background-icon="widgetBackgroundIcon(widget)"
          :background-image-src="widgetBackgroundImage(widget)"
          :show-toggle="false"
          :expand-label="`Раскрыть ${widget.title || widget.id}`"
          :collapse-label="`Свернуть ${widget.title || widget.id}`"
        >
          <template #header>
            <div class="sidebar-indicator-card-header">
              <div
                class="sidebar-indicator-card-title-row"
                :class="{ compact: !isWidgetExpanded(widget.id) }"
              >
                <div class="widget-title">
                  <component
                    v-if="isWidgetExpanded(widget.id)"
                    :is="resolveWidgetIcon(widget)"
                    class="ui-icon widget-icon"
                  />
                  <h3
                    class="sidebar-indicator-head-main"
                    :title="
                      isWidgetExpanded(widget.id)
                        ? widget.title
                        : headerPrimaryValue(widget)
                    "
                  >
                    <span class="sidebar-indicator-head-main-track">
                      <span class="sidebar-indicator-head-main-copy">
                        {{
                          isWidgetExpanded(widget.id)
                            ? widget.title
                            : headerPrimaryValue(widget)
                        }}
                      </span>
                    </span>
                  </h3>
                </div>
                <div class="sidebar-indicator-head-actions">
                  <button
                    v-if="isLargeIndicator(widget)"
                    class="sidebar-indicator-icon-btn"
                    type="button"
                    title="Открыть вкладку"
                    @click.stop="openIndicatorView(widget.id)"
                  >
                    ↗
                  </button>
                </div>
              </div>
              <p
                v-if="isWidgetExpanded(widget.id)"
                class="sidebar-indicator-head-value"
                :title="headerPrimaryValue(widget)"
              >
                {{ headerPrimaryValueShort(widget) }}
              </p>
            </div>
          </template>

          <template #body>
            <p v-if="widgetState(widget.id)?.error" class="widget-error">
              {{ widgetState(widget.id)?.error }}
            </p>
            <p v-else-if="widgetState(widget.id)?.loading" class="widget-loading">
              Обновление...
            </p>

            <template v-else-if="widget.type === 'stat_card'">
              <div class="sidebar-indicator-current-row">
                <p
                  class="widget-value sidebar-indicator-value"
                  :class="{ 'widget-value-metric': isMetricValue(resolvePrimaryValue(widget)) }"
                >
                  {{ resolvePrimaryValue(widget) }}
                </p>
                <button
                  v-if="canCopyPrimaryValue(widget)"
                  class="sidebar-indicator-icon-btn compact"
                  type="button"
                  :title="isCopyDone(widget.id) ? 'Скопировано' : copyButtonTitle(widget)"
                  @click.stop="copyPrimaryValue(widget)"
                >
                  {{ isCopyDone(widget.id) ? "✓" : "⧉" }}
                </button>
              </div>
              <p class="widget-subtitle">{{ statCardSubtitle(widget) }}</p>
              <p v-if="statCardTrend(widget)" class="widget-trend">
                {{ statCardTrend(widget) }}
              </p>
            </template>

            <template v-else-if="widget.type === 'stat_list'">
              <nav
                v-if="indicatorTabs(widget).length > 1"
                class="sidebar-indicator-tabs"
                role="tablist"
                aria-label="Режим индикатора"
                @click.stop
              >
                <button
                  v-for="tab in indicatorTabs(widget)"
                  :key="`${widget.id}:${tab.id}`"
                  class="sidebar-indicator-tab-btn"
                  :class="{ active: activeIndicatorTabId(widget) === tab.id }"
                  type="button"
                  role="tab"
                  :aria-selected="activeIndicatorTabId(widget) === tab.id"
                  @click.stop="setIndicatorTab(widget, tab.id)"
                >
                  {{ tab.title }}
                </button>
              </nav>
              <UiFieldset
                v-if="hasStatListHeader(widget, resolveActiveTabMapping(widget))"
                class="sidebar-indicator-fieldset"
                :legend="fieldsetLegend(widget)"
              >
                <div class="sidebar-indicator-current-row">
                  <p
                    class="widget-value sidebar-indicator-value"
                    :class="{ 'widget-value-metric': isMetricValue(resolvePrimaryValue(widget)) }"
                  >
                    {{ resolvePrimaryValue(widget) }}
                  </p>
                  <button
                    v-if="canCopyPrimaryValue(widget)"
                    class="sidebar-indicator-icon-btn compact"
                    type="button"
                    :title="isCopyDone(widget.id) ? 'Скопировано' : copyButtonTitle(widget)"
                    @click.stop="copyPrimaryValue(widget)"
                  >
                    {{ isCopyDone(widget.id) ? "✓" : "⧉" }}
                  </button>
                </div>
                <p class="widget-subtitle">
                  {{ statCardSubtitleByMapping(widget, resolveActiveTabMapping(widget)) }}
                </p>
                <p
                  v-if="statCardTrendByMapping(widget, resolveActiveTabMapping(widget))"
                  class="widget-trend"
                >
                  {{ statCardTrendByMapping(widget, resolveActiveTabMapping(widget)) }}
                </p>
              </UiFieldset>
              <ul
                v-if="
                  indicatorPreviewEntriesByMapping(
                    widget,
                    resolveActiveTabMapping(widget),
                  ).length
                "
                class="widget-list sidebar-list-preview"
              >
                <li
                  v-for="
                    entry in indicatorPreviewEntriesByMapping(
                      widget,
                      resolveActiveTabMapping(widget),
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

            <template v-else-if="widget.type === 'table'">
              <p class="widget-subtitle">Строк: {{ tableRows(widget).length }}</p>
            </template>

            <p v-else class="widget-empty">Неподдерживаемый тип виджета</p>
          </template>

          <template v-if="widget.data.actions?.length" #footer>
            <div class="widget-actions sidebar-indicator-actions">
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
          </template>
        </UiCollapsibleCard>
      </div>
      <p v-else class="widget-empty">
        Для выбранной страницы индикаторы не настроены.
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useDashboardStore } from "@/features/stores/dashboardStore";
import type {
  DashboardWidget,
  DashboardWidgetMapping,
} from "@/features/stores/dashboard/storeTypes";
import UiCollapsibleCard from "@/ui/surfaces/UiCollapsibleCard.vue";
import UiFieldset from "@/ui/surfaces/UiFieldset.vue";

const dashboard = useDashboardStore();

const {
  statsExpanded,
  sidebarIndicatorSummary,
  sidebarIndicators,
  isLargeIndicator,
  activeIndicatorWidget,
  resolveWidgetIcon,
  widgetState,
  statCardValue,
  statCardValueByMapping,
  statCardSubtitle,
  statCardSubtitleByMapping,
  statCardTrend,
  statCardTrendByMapping,
  indicatorPreviewEntriesByMapping,
  tableRows,
  openIndicatorView,
  isActionBusy,
  runWidgetAction,
} = dashboard;

interface IndicatorTabConfig {
  id: string;
  title: string;
  mapping?: DashboardWidgetMapping;
}

const activeTabsByWidget = ref<Record<string, string>>({});
const copiedUntilByWidget = ref<Record<string, number>>({});
const INDICATORS_ACCORDION_GROUP = "sidebar-indicators-collapsible-group";
const PLUGIN_BACKGROUND_GLYPH: Record<string, string> = {
  external_ip: "◎",
  internet_speed: "⇅",
  dns_trace: "⌖",
  autodiscover: "⌘",
};
const TOKEN_BACKGROUND_GLYPH: Array<[string, string]> = [
  ["ip", "◎"],
  ["dns", "⌖"],
  ["trace", "⌖"],
  ["speed", "⇅"],
  ["network", "◌"],
  ["table", "▦"],
  ["list", "☰"],
];
const IPV4_RE =
  /\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b/;
const IPV6_RE = /\b(?:[a-fA-F0-9]{1,4}:){2,7}[a-fA-F0-9]{1,4}\b/;

const expandedWidgetId = ref("");

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
      ...(mapping ? { mapping: mapping as DashboardWidgetMapping } : {}),
    });
  }
  return parsed;
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

function resolveActiveTabMapping(widget: DashboardWidget): DashboardWidgetMapping {
  const tabs = indicatorTabs(widget);
  const activeTabId = activeIndicatorTabId(widget);
  const activeTab = tabs.find((tab) => tab.id === activeTabId);
  if (activeTab?.mapping) return activeTab.mapping;
  return (widget?.data?.mapping || {}) as DashboardWidgetMapping;
}

function hasStatListHeader(
  widget: DashboardWidget,
  mappingOverride?: DashboardWidgetMapping,
): boolean {
  const mapping =
    (mappingOverride as Record<string, unknown> | undefined) ||
    (widget?.data?.mapping as Record<string, unknown> | undefined);
  if (!mapping || typeof mapping !== "object") return false;
  return Boolean(mapping.value || mapping.subtitle || mapping.trend);
}

function canCopyPrimaryValue(widget: DashboardWidget): boolean {
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

function isCopyDone(widgetId: string): boolean {
  return Number(copiedUntilByWidget.value[widgetId] || 0) > Date.now();
}

function resolvePrimaryValue(widget: DashboardWidget): unknown {
  const type = String(widget?.type || "").trim();
  if (type === "stat_list") {
    return statCardValueByMapping(widget, resolveActiveTabMapping(widget));
  }
  return statCardValue(widget);
}

function normalizeHeaderValue(value: unknown): string {
  if (value == null) return "—";
  const token = String(value).replace(/\s+/g, " ").trim();
  return token || "—";
}

function truncateHeaderValue(value: string, maxLen = 46): string {
  const token = String(value || "").trim();
  if (token.length <= maxLen) return token;
  return `${token.slice(0, maxLen - 1)}…`;
}

function extractIpFromText(value: string): string {
  const token = String(value || "").trim();
  if (!token) return "";
  const ipv4 = token.match(IPV4_RE);
  if (ipv4) return String(ipv4[0]);
  const ipv6 = token.match(IPV6_RE);
  if (ipv6) return String(ipv6[0]);
  return "";
}

function extractIpFromUnknown(value: unknown): string {
  if (value == null) return "";
  if (typeof value === "string") {
    const token = value.trim();
    if (!token) return "";
    if (token.startsWith("{") || token.startsWith("[")) {
      try {
        return extractIpFromUnknown(JSON.parse(token));
      } catch {
        return extractIpFromText(token);
      }
    }
    return extractIpFromText(token);
  }
  if (Array.isArray(value)) {
    for (const entry of value) {
      const ip = extractIpFromUnknown(entry);
      if (ip) return ip;
    }
    return "";
  }
  const record = asRecord(value);
  if (!record) return "";
  for (const key of [
    "ip",
    "primary_ip",
    "query",
    "address",
    "ip_addr",
    "ipAddress",
  ]) {
    const ip = extractIpFromUnknown(record[key]);
    if (ip) return ip;
  }
  return extractIpFromText(JSON.stringify(record));
}

function isIpWidget(widget: DashboardWidget): boolean {
  const id = String(widget?.id || "").toLowerCase();
  const title = String(widget?.title || "").toLowerCase();
  const pluginId = String(widget?.plugin_id || "").toLowerCase();
  return id.includes("ip") || title.includes("ip") || pluginId.includes("ip");
}

function preferredIpValue(widget: DashboardWidget): string {
  if (!isIpWidget(widget)) return "";
  const payload = asRecord(widgetState(widget.id)?.payload);
  const summary = asRecord(payload?.summary);
  const client = asRecord(payload?.client);

  const candidates: unknown[] = [
    resolvePrimaryValue(widget),
    payload?.ip,
    summary?.primary_ip,
    client?.ip,
    summary?.unique_ips,
    payload?.segments,
    client?.samples,
  ];

  for (const candidate of candidates) {
    const ip = extractIpFromUnknown(candidate);
    if (ip) return ip;
  }
  return "";
}

function headerPrimaryValue(widget: DashboardWidget): string {
  const state = widgetState(widget.id);
  if (state?.error) return "Ошибка обновления";
  if (state?.loading) return "Обновление...";

  const type = String(widget?.type || "").trim();
  if (type === "table") {
    return `Строк: ${tableRows(widget).length}`;
  }
  if (type === "stat_card" || type === "stat_list") {
    const ip = preferredIpValue(widget);
    if (ip) return ip;
    return normalizeHeaderValue(resolvePrimaryValue(widget));
  }
  return "—";
}

function headerPrimaryValueShort(widget: DashboardWidget): string {
  return truncateHeaderValue(headerPrimaryValue(widget));
}

function normalizeBackgroundGlyph(value: unknown): string {
  const token = String(value || "").trim();
  if (!token) return "";
  if (/^[^\w\s]$/.test(token)) return token;
  if (/^[\u{1F300}-\u{1FAFF}]$/u.test(token)) return token;
  const normalized = token.toLowerCase();
  if (PLUGIN_BACKGROUND_GLYPH[normalized]) {
    return PLUGIN_BACKGROUND_GLYPH[normalized];
  }
  for (const [pattern, glyph] of TOKEN_BACKGROUND_GLYPH) {
    if (normalized.includes(pattern)) return glyph;
  }
  return "";
}

function widgetBackgroundIcon(widget: DashboardWidget): string {
  const directIcon = normalizeBackgroundGlyph(
    asRecord(widget?.data)?.backgroundIcon || widget?.icon,
  );
  if (directIcon) return directIcon;

  const pluginIcon = normalizeBackgroundGlyph(
    widget?.plugin_icon || widget?.plugin_id,
  );
  if (pluginIcon) return pluginIcon;

  return "";
}

function widgetBackgroundMode(widget: DashboardWidget): "icon" | "image" {
  return widgetBackgroundIcon(widget) ? "icon" : "image";
}

function widgetBackgroundImage(widget: DashboardWidget): string {
  const custom =
    String(asRecord(widget?.data)?.backgroundImage || widget?.background_image || "")
      .trim();
  if (custom) return custom;
  return "/static/img/emblem-mark.png";
}

function isWidgetExpanded(widgetId: string): boolean {
  return expandedWidgetId.value === widgetId;
}

function onWidgetExpandedChange(widgetId: string, nextValue: boolean): void {
  if (nextValue) {
    expandedWidgetId.value = widgetId;
    return;
  }
  if (expandedWidgetId.value === widgetId) {
    expandedWidgetId.value = "";
  }
}

function isMetricValue(value: unknown): boolean {
  const token = String(value ?? "").toLowerCase();
  if (!token || token === "—") return false;
  return token.includes("mbps") || token.includes(" ms");
}

async function copyPrimaryValue(widget: DashboardWidget): Promise<void> {
  if (!canCopyPrimaryValue(widget)) return;
  if (typeof navigator === "undefined" || !navigator.clipboard?.writeText) return;
  const value = String(resolvePrimaryValue(widget) ?? "").trim();
  if (!value || value === "—") return;
  try {
    await navigator.clipboard.writeText(value);
    copiedUntilByWidget.value = {
      ...copiedUntilByWidget.value,
      [widget.id]: Date.now() + 1400,
    };
  } catch {
    return;
  }
}
</script>
