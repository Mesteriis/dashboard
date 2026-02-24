export function createDashboardIconsSection(ctx: any) {
  function clearItemFaviconFailures(): void {
    for (const key of Object.keys(ctx.itemFaviconFailures)) {
      delete ctx.itemFaviconFailures[key];
    }
  }

  function faviconOriginFromUrl(rawValue: unknown): string {
    return ctx.originFromHttpUrl(rawValue);
  }

  function itemFaviconKey(
    item: Record<string, unknown> | null | undefined,
  ): string {
    const origin = faviconOriginFromUrl(item?.url);
    if (!origin) return "";
    return origin;
  }

  function itemFaviconSrc(
    item: Record<string, unknown> | null | undefined,
  ): string {
    const origin = faviconOriginFromUrl(item?.url);
    if (!origin) return "";

    const key = itemFaviconKey(item);
    if (key && ctx.itemFaviconFailures[key]) return "";
    return ctx.resolveRequestUrl(
      `/api/v1/favicon?url=${encodeURIComponent(origin)}`,
    );
  }

  function markItemFaviconFailed(
    item: Record<string, unknown> | null | undefined,
  ): void {
    const key = itemFaviconKey(item);
    if (!key) return;
    ctx.itemFaviconFailures[key] = true;
  }

  function resolvePageIcon(page: any): unknown {
    return ctx.resolvePageIconSemantic(page);
  }

  function resolveGroupIcon(group: any): unknown {
    return ctx.resolveGroupIconSemantic(group);
  }

  function resolveSubgroupIcon(subgroup: any): unknown {
    return ctx.resolveSubgroupIconSemantic(subgroup);
  }

  function resolveItemIcon(item: any): unknown {
    return ctx.resolveItemIconSemantic(item);
  }

  function resolveWidgetIcon(widget: any): unknown {
    return ctx.resolveWidgetIconSemantic(widget);
  }

  return {
    clearItemFaviconFailures,
    faviconOriginFromUrl,
    itemFaviconKey,
    itemFaviconSrc,
    markItemFaviconFailed,
    resolveGroupIcon,
    resolveItemIcon,
    resolvePageIcon,
    resolveSubgroupIcon,
    resolveWidgetIcon,
  };
}
