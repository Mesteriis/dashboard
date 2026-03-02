import type { DashboardWidget } from "@/features/stores/dashboard/storeTypes";

interface ParsedDashboardIndicators {
  widgets: DashboardWidget[];
  alwaysVisibleWidgetIds: string[];
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function asString(value: unknown): string {
  return String(value || "").trim();
}

function asBoolean(value: unknown): boolean {
  return value === true;
}

function parseIndicatorWidget(
  value: unknown,
  fallbackId: string,
): DashboardWidget | null {
  const raw = asRecord(value);
  if (!raw) return null;

  const widgetId = asString(raw.id) || fallbackId;
  if (!widgetId) return null;

  return {
    ...raw,
    id: widgetId,
    title: asString(raw.title) || widgetId,
    type: asString(raw.type) || "stat_card",
  } as DashboardWidget;
}

export function extractDashboardIndicatorsFromPlugins(
  payload: unknown,
): ParsedDashboardIndicators {
  const root = asRecord(payload);
  const rawPlugins = Array.isArray(root?.plugins) ? root.plugins : [];

  const widgetsById = new Map<string, DashboardWidget>();
  const alwaysVisibleWidgetIds: string[] = [];

  for (const rawPlugin of rawPlugins) {
    const plugin = asRecord(rawPlugin);
    if (!plugin) continue;
    const pluginId = asString(plugin.id) || asString(plugin.name);
    const metadata = asRecord(plugin.metadata);
    const pageManifestEnvelope = asRecord(metadata?.page_manifest);
    const manifest = asRecord(pageManifestEnvelope?.manifest);
    const dashboard = asRecord(manifest?.dashboard);
    const rawIndicators = Array.isArray(dashboard?.indicators)
      ? dashboard.indicators
      : [];

    for (const rawIndicator of rawIndicators) {
      const indicator = asRecord(rawIndicator);
      if (!indicator) continue;
      const indicatorId = asString(indicator.id);
      const widget = parseIndicatorWidget(
        indicator.widget,
        `${pluginId}.${indicatorId || "indicator"}`,
      );
      if (!widget) continue;
      if (!widgetsById.has(widget.id)) {
        widgetsById.set(widget.id, {
          ...widget,
          plugin_id: pluginId,
        });
      }
      const alwaysVisible =
        asBoolean(indicator.alwaysVisible) ||
        asBoolean(indicator.always_visible);
      if (alwaysVisible) {
        alwaysVisibleWidgetIds.push(widget.id);
      }
    }
  }

  return {
    widgets: Array.from(widgetsById.values()),
    alwaysVisibleWidgetIds: Array.from(new Set(alwaysVisibleWidgetIds)),
  };
}
