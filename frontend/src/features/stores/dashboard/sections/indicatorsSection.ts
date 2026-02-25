import type {
  DashboardLayoutBlock,
  DashboardWidget,
  DashboardWidgetResolved,
  WidgetStatListEntry,
} from "@/features/stores/dashboard/storeTypes";

export function createDashboardIndicatorsSection(ctx: any) {
  function isWidgetBlock(block: DashboardLayoutBlock): boolean {
    return block?.type === "widget_row" || block?.type === "widget_grid";
  }

  function resolveWidgets(
    widgetIds: readonly string[] = [],
  ): DashboardWidgetResolved[] {
    return widgetIds
      .map((widgetId) => ctx.widgetById.value.get(widgetId))
      .filter((widget): widget is DashboardWidgetResolved => Boolean(widget));
  }

  function isLargeIndicator(widget: DashboardWidget): boolean {
    return ctx.LARGE_INDICATOR_TYPES.has(String(widget?.type || ""));
  }

  function indicatorPreviewEntries(
    widget: DashboardWidget,
  ): WidgetStatListEntry[] {
    return ctx.statListEntries(widget).slice(0, 2);
  }

  function openIndicatorView(widgetId: string): void {
    const widget = ctx.sidebarIndicators.value.find(
      (entry: DashboardWidgetResolved) => entry.id === widgetId,
    );
    if (!widget || !isLargeIndicator(widget)) return;
    ctx.activeIndicatorViewId.value = widget.id;
  }

  function selectSidebarIndicator(widget: DashboardWidget): void {
    if (isLargeIndicator(widget)) {
      openIndicatorView(widget.id);
    }
  }

  return {
    indicatorPreviewEntries,
    isLargeIndicator,
    isWidgetBlock,
    openIndicatorView,
    resolveWidgets,
    selectSidebarIndicator,
  };
}
