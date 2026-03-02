import type {
  DashboardWidget,
  DashboardWidgetAction,
  DashboardWidgetMapping,
  WidgetRuntimeState,
  WidgetStatListEntry,
} from "@/features/stores/dashboard/storeTypes";
import { runClientProbeScript } from "@/features/plugins/clientProbeSandbox";

interface WidgetClientProbeConfig {
  enabled: boolean;
  script: string;
  timeoutMs: number;
  cacheSec: number;
}

interface WidgetClientProbeCacheEntry {
  expiresAt: number;
  payload: unknown;
  error: string;
}

export function createDashboardWidgetRuntimeSection(ctx: any) {
  function asRecord(value: unknown): Record<string, unknown> | null {
    if (!value || typeof value !== "object" || Array.isArray(value)) return null;
    return value as Record<string, unknown>;
  }

  function asNumber(value: unknown, fallback: number): number {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) return fallback;
    return parsed;
  }

  function widgetState(widgetId: string): WidgetRuntimeState | null {
    return ctx.widgetStates[widgetId] || null;
  }

  function actionKey(widgetId: string, actionId: string): string {
    return `${widgetId}:${actionId}`;
  }

  function isActionBusy(widgetId: string, actionId: string): boolean {
    return Boolean(ctx.actionBusy[actionKey(widgetId, actionId)]);
  }

  function resolveExpression(payload: unknown, expression: unknown): unknown {
    if (!expression || typeof expression !== "string") return null;
    if (expression === "$") return payload;
    if (!expression.startsWith("$.")) return null;

    let current = payload;
    const parts = expression.slice(2).split(".");

    for (const part of parts) {
      if (current == null) return null;

      const arrayMatch = part.match(/^(.*)\[\*\]$/);
      if (arrayMatch) {
        const key = arrayMatch[1];
        const value = key
          ? (current as Record<string, unknown>)?.[key]
          : current;
        return Array.isArray(value) ? value : [];
      }

      current = (current as Record<string, unknown>)?.[part];
    }

    return current;
  }

  function resolveMapping(
    widget: DashboardWidget,
    override?: DashboardWidgetMapping,
  ): DashboardWidgetMapping {
    if (override && typeof override === "object") return override;
    return widget.data?.mapping || {};
  }

  function statCardValueByMapping(
    widget: DashboardWidget,
    mappingOverride?: DashboardWidgetMapping,
  ): unknown {
    const payload = widgetState(widget.id)?.payload;
    const mapping = resolveMapping(widget, mappingOverride);
    const value = resolveExpression(payload, mapping.value);
    return value ?? "—";
  }

  function statCardValue(widget: DashboardWidget): unknown {
    return statCardValueByMapping(widget);
  }

  function statCardSubtitleByMapping(
    widget: DashboardWidget,
    mappingOverride?: DashboardWidgetMapping,
  ): unknown {
    const payload = widgetState(widget.id)?.payload;
    const mapping = resolveMapping(widget, mappingOverride);
    const subtitle = resolveExpression(payload, mapping.subtitle);
    return subtitle ?? "";
  }

  function statCardSubtitle(widget: DashboardWidget): unknown {
    return statCardSubtitleByMapping(widget);
  }

  function statCardTrendByMapping(
    widget: DashboardWidget,
    mappingOverride?: DashboardWidgetMapping,
  ): unknown {
    const payload = widgetState(widget.id)?.payload;
    const mapping = resolveMapping(widget, mappingOverride);
    const trend = resolveExpression(payload, mapping.trend);
    return trend ?? "";
  }

  function statCardTrend(widget: DashboardWidget): unknown {
    return statCardTrendByMapping(widget);
  }

  function statListEntriesByMapping(
    widget: DashboardWidget,
    mappingOverride?: DashboardWidgetMapping,
  ): WidgetStatListEntry[] {
    const payload = widgetState(widget.id)?.payload;
    const mapping = resolveMapping(widget, mappingOverride);
    const items = resolveExpression(payload, mapping.items);

    if (!Array.isArray(items)) return [];

    return items.map((entry) => {
      const title = String(resolveExpression(entry, mapping.item_title) ?? "-");
      const value = String(resolveExpression(entry, mapping.item_value) ?? "-");
      return { title, value };
    });
  }

  function statListEntries(widget: DashboardWidget): WidgetStatListEntry[] {
    return statListEntriesByMapping(widget);
  }

  function resolveClientProbeConfig(
    widget: DashboardWidget,
  ): WidgetClientProbeConfig | null {
    const raw =
      asRecord(widget.data?.clientProbe) || asRecord(widget.data?.client_probe);
    if (!raw) return null;
    const script = String(raw.script || "").trim();
    if (!script) return null;
    return {
      enabled: raw.enabled !== false,
      script,
      timeoutMs: Math.max(1000, asNumber(raw.timeoutMs ?? raw.timeout_ms, 5000)),
      cacheSec: Math.max(5, asNumber(raw.cacheSec ?? raw.cache_sec, 120)),
    };
  }

  function mergeClientProbePayload(
    payload: unknown,
    clientPayload: unknown,
    clientError: string,
  ): Record<string, unknown> {
    const base = asRecord(payload)
      ? { ...(payload as Record<string, unknown>) }
      : { payload };

    return {
      ...base,
      client: asRecord(clientPayload)
        ? (clientPayload as Record<string, unknown>)
        : {
            value: clientPayload,
          },
      client_probe: {
        ok: !clientError,
        error: clientError || null,
        updated_at: new Date().toISOString(),
      },
    };
  }

  async function resolvePayloadWithClientProbe(
    widget: DashboardWidget,
    payload: unknown,
  ): Promise<unknown> {
    const probeConfig = resolveClientProbeConfig(widget);
    if (!probeConfig || !probeConfig.enabled) return payload;

    const cached = ctx.widgetClientProbeCache[widget.id] as
      | WidgetClientProbeCacheEntry
      | undefined;
    if (
      cached &&
      typeof cached.expiresAt === "number" &&
      cached.expiresAt > Date.now()
    ) {
      return mergeClientProbePayload(payload, cached.payload, cached.error || "");
    }

    try {
      const clientPayload = await runClientProbeScript({
        script: probeConfig.script,
        timeoutMs: probeConfig.timeoutMs,
        context: {
          pluginId: String(widget.plugin_id || ""),
          widgetId: widget.id,
          serverPayload: payload,
        },
      });
      ctx.widgetClientProbeCache[widget.id] = {
        expiresAt: Date.now() + probeConfig.cacheSec * 1000,
        payload: clientPayload,
        error: "",
      };
      return mergeClientProbePayload(payload, clientPayload, "");
    } catch (error: unknown) {
      const message = ctx.errorMessage(error, "Client probe failed");
      ctx.widgetClientProbeCache[widget.id] = {
        expiresAt: Date.now() + Math.min(probeConfig.cacheSec, 30) * 1000,
        payload: null,
        error: message,
      };
      return mergeClientProbePayload(payload, null, message);
    }
  }

  function tableRows(widget: DashboardWidget): Array<Record<string, unknown>> {
    const payload = widgetState(widget.id)?.payload;
    const rowsExpression = widget.data?.mapping?.rows;
    const fromExpression = resolveExpression(payload, rowsExpression);

    if (Array.isArray(fromExpression)) {
      return fromExpression as Array<Record<string, unknown>>;
    }
    if (Array.isArray(payload)) {
      return payload as Array<Record<string, unknown>>;
    }
    if (
      payload &&
      typeof payload === "object" &&
      Array.isArray((payload as { items?: unknown[] }).items)
    ) {
      return (payload as { items: Array<Record<string, unknown>> }).items;
    }
    return [];
  }

  function normalizeEndpoint(endpoint: unknown): string {
    const normalized = String(endpoint || "").trim();
    if (!normalized) return "";
    if (normalized.startsWith("http://") || normalized.startsWith("https://")) {
      return normalized;
    }
    if (normalized.startsWith("/")) return normalized;
    return `/${normalized}`;
  }

  function resetWidgetPolling(): void {
    for (const timer of ctx.widgetIntervals.values()) {
      clearInterval(timer);
    }
    ctx.widgetIntervals.clear();
  }

  async function refreshWidget(widgetId: string): Promise<void> {
    const widget = ctx.widgetById.value.get(widgetId);
    if (!widget) return;

    const endpoint = normalizeEndpoint(widget.data?.endpoint);
    if (!endpoint) return;

    if (!ctx.widgetStates[widgetId]) {
      ctx.widgetStates[widgetId] = {
        loading: false,
        error: "",
        payload: null,
        lastUpdated: 0,
      };
    }

    const state = ctx.widgetStates[widgetId];
    state.loading = true;
    state.error = "";

    try {
      const payload = await ctx.requestJson(endpoint);
      state.payload = await resolvePayloadWithClientProbe(widget, payload);
      state.lastUpdated = Date.now();
    } catch (error: unknown) {
      state.error = ctx.errorMessage(error, "Ошибка загрузки виджета");
    } finally {
      state.loading = false;
    }
  }

  async function initWidgetPolling(): Promise<void> {
    resetWidgetPolling();

    const initialLoads: Array<Promise<void>> = [];

    for (const widget of ctx.widgets.value) {
      initialLoads.push(refreshWidget(widget.id));

      if (!normalizeEndpoint(widget.data?.endpoint)) continue;
      const intervalMs =
        Math.max(1, Number(widget.data?.refresh_sec || 0)) * 1000;

      const timer = window.setInterval(() => {
        refreshWidget(widget.id);
      }, intervalMs);

      ctx.widgetIntervals.set(widget.id, timer);
    }

    await Promise.all(initialLoads);
  }

  async function runWidgetAction(
    widgetId: string,
    action: DashboardWidgetAction,
  ): Promise<void> {
    const key = actionKey(widgetId, action.id);
    const endpoint = normalizeEndpoint(action.endpoint);
    if (!endpoint) return;

    ctx.actionBusy[key] = true;

    try {
      await ctx.requestJson(endpoint, {
        method: String(action.method || "GET").toUpperCase(),
      });
      await refreshWidget(widgetId);
    } catch (error: unknown) {
      if (!ctx.widgetStates[widgetId]) {
        ctx.widgetStates[widgetId] = {
          loading: false,
          error: "",
          payload: null,
          lastUpdated: 0,
        };
      }
      ctx.widgetStates[widgetId].error = ctx.errorMessage(
        error,
        "Не удалось выполнить действие",
      );
    } finally {
      ctx.actionBusy[key] = false;
    }
  }

  return {
    actionKey,
    initWidgetPolling,
    isActionBusy,
    normalizeEndpoint,
    refreshWidget,
    resetWidgetPolling,
    resolveExpression,
    runWidgetAction,
    statCardSubtitle,
    statCardSubtitleByMapping,
    statCardTrend,
    statCardTrendByMapping,
    statCardValue,
    statCardValueByMapping,
    statListEntries,
    statListEntriesByMapping,
    tableRows,
    widgetState,
  };
}
