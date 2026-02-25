import type { DashboardConfig } from "@/features/stores/dashboard/storeTypes";

export function createDashboardConfigMutationSection(ctx: any) {
  function cloneConfig<T>(value: T): T {
    return JSON.parse(JSON.stringify(value)) as T;
  }

  function ensureAbsoluteUrl(rawValue: unknown): string {
    return ctx.ensureAbsoluteHttpUrl(rawValue);
  }

  async function persistConfig(): Promise<void> {
    if (!ctx.config.value) return;

    ctx.saveStatus.value = "saving";
    ctx.saveError.value = "";

    try {
      const response = await ctx.updateDashboardConfig(ctx.config.value);
      const nextConfig =
        response &&
        typeof response === "object" &&
        (response as any).config &&
        typeof (response as any).config === "object"
          ? ((response as any).config as DashboardConfig)
          : ctx.config.value;
      ctx.config.value = nextConfig;

      if (
        !ctx.activePageId.value ||
        !ctx.pages.value.some(
          (page: any) =>
            String(page?.id || "") === String(ctx.activePageId.value || ""),
        )
      ) {
        ctx.activePageId.value = String(ctx.pages.value[0]?.id || "");
      }

      ctx.saveStatus.value = "saved";
      if (ctx.saveStatusTimer) {
        clearTimeout(ctx.saveStatusTimer);
      }

      ctx.saveStatusTimer = window.setTimeout(() => {
        if (ctx.saveStatus.value === "saved") {
          ctx.saveStatus.value = "idle";
        }
      }, 1400);
    } catch (error: unknown) {
      ctx.saveStatus.value = "error";
      ctx.saveError.value = ctx.errorMessage(error, "Ошибка сохранения YAML");
      throw error;
    }
  }

  async function applyConfigMutation(
    mutator: (cfg: DashboardConfig) => boolean | void | Promise<boolean | void>,
  ): Promise<boolean> {
    if (!ctx.config.value) return false;

    const snapshot = cloneConfig(ctx.config.value);

    try {
      const result = mutator(ctx.config.value);
      if (result === false) return false;

      ctx.normalizeLayoutBlocksInConfig(ctx.config.value);
      ctx.syncTreeGroupsState();
      await persistConfig();
      return true;
    } catch (error: unknown) {
      ctx.config.value = snapshot;
      ctx.saveStatus.value = "error";
      ctx.saveError.value = ctx.errorMessage(error, "Не удалось применить изменения");
      return false;
    }
  }

  return {
    applyConfigMutation,
    cloneConfig,
    ensureAbsoluteUrl,
    persistConfig,
  };
}
