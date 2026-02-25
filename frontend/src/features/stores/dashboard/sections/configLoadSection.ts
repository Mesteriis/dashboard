import type { DashboardConfig } from "@/features/stores/dashboard/storeTypes";

export function createDashboardConfigLoadSection(ctx: any) {
  async function loadConfig(): Promise<void> {
    ctx.loadingConfig.value = true;
    ctx.configError.value = "";
    ctx.saveStatus.value = "idle";
    ctx.saveError.value = "";
    try {
      const data = (await ctx.fetchDashboardConfig()) as DashboardConfig;
      ctx.config.value = data;

      if (
        !ctx.activePageId.value ||
        !ctx.pages.value.some(
          (page: any) =>
            String(page?.id || "") === String(ctx.activePageId.value || ""),
        )
      ) {
        ctx.activePageId.value = String(ctx.pages.value[0]?.id || "");
      }

      ctx.syncTreeGroupsState();
      ctx.applyTheme(data?.ui?.theme);
      ctx.applyGrid(data?.ui?.grid);
      await ctx.initWidgetPolling();
      await ctx.startHealthPolling();
      if (!ctx.isDocumentVisible.value) {
        ctx.pauseBackgroundPolling();
      }
    } catch (error: unknown) {
      ctx.configError.value = ctx.errorMessage(
        error,
        "Не удалось загрузить dashboard-конфигурацию",
      );
      ctx.config.value = null;
      ctx.resetWidgetPolling();
      ctx.stopHealthPolling();
    } finally {
      ctx.loadingConfig.value = false;
    }
  }

  return {
    loadConfig,
  };
}
