import type {
  DashboardWidget,
  DashboardWidgetAction,
  DashboardWidgetMapping,
  WidgetRuntimeState,
  WidgetStatListEntry,
} from "@/features/stores/dashboard/storeTypes";

export function createDashboardWidgetRuntimeSection(ctx: any) {
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

  function statCardValue(widget: DashboardWidget): unknown {
    const payload = widgetState(widget.id)?.payload;
    const value = resolveExpression(payload, widget.data?.mapping?.value);
    return value ?? "—";
  }

  function statCardSubtitle(widget: DashboardWidget): unknown {
    const payload = widgetState(widget.id)?.payload;
    const subtitle = resolveExpression(payload, widget.data?.mapping?.subtitle);
    return subtitle ?? "";
  }

  function statCardTrend(widget: DashboardWidget): unknown {
    const payload = widgetState(widget.id)?.payload;
    const trend = resolveExpression(payload, widget.data?.mapping?.trend);
    return trend ?? "";
  }

  function statListEntries(widget: DashboardWidget): WidgetStatListEntry[] {
    const payload = widgetState(widget.id)?.payload;
    const mapping: DashboardWidgetMapping = widget.data?.mapping || {};
    const items = resolveExpression(payload, mapping.items);

    if (!Array.isArray(items)) return [];

    return items.map((entry) => {
      const title = String(resolveExpression(entry, mapping.item_title) ?? "-");
      const value = String(resolveExpression(entry, mapping.item_value) ?? "-");
      return { title, value };
    });
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
      state.payload = await ctx.requestJson(endpoint);
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
      const intervalMs = Math.max(1, Number(widget.data?.refresh_sec || 0)) * 1000;

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
    statCardTrend,
    statCardValue,
    statListEntries,
    tableRows,
    widgetState,
  };
}
