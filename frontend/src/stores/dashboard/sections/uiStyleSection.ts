import type { DashboardGrid, DashboardTheme } from "@/stores/dashboard/storeTypes";

export function createDashboardUiStyleSection(ctx: any) {
  function applyTheme(theme: DashboardTheme | undefined): void {
    if (!theme) return;
    const root = document.documentElement;

    if (theme.accent) {
      root.style.setProperty("--accent", theme.accent);
      root.style.setProperty("--accent-soft", theme.accent);
    }
    if (theme.background) {
      root.style.setProperty("--bg", theme.background);
    }
    if (theme.border) {
      root.style.setProperty("--border", theme.border);
    }
    if (theme.card) {
      root.style.setProperty("--surface", theme.card);
      root.style.setProperty("--surface-strong", theme.card);
    }

    root.style.setProperty("--glow-enabled", theme.glow === false ? "0" : "1");
  }

  function applyGrid(grid: DashboardGrid | undefined): void {
    if (!grid) return;
    const root = document.documentElement;

    if (grid.gap != null) {
      root.style.setProperty("--grid-gap", `${Number(grid.gap)}px`);
    }
    if (grid.card_radius != null) {
      root.style.setProperty("--card-radius", `${Number(grid.card_radius)}px`);
    }
    if (grid.columns != null) {
      root.style.setProperty("--layout-columns", String(Number(grid.columns)));
    }
  }

  function toggleEditMode(): void {
    ctx.editMode.value = !ctx.editMode.value;
    ctx.saveError.value = "";
    if (!ctx.editMode.value) {
      ctx.preserveTreeSelectionOnPageSwitch = false;
      ctx.clearSelectedNode();
      ctx.clearDragState();
      ctx.closeCreateChooser();
      ctx.closeCreateEntityEditor(true);
    }
  }

  function toggleServiceCardView(): void {
    if (ctx.serviceCardView.value === "detailed") {
      ctx.serviceCardView.value = "tile";
      return;
    }

    if (ctx.serviceCardView.value === "tile") {
      ctx.serviceCardView.value = "icon";
      return;
    }

    ctx.serviceCardView.value = "detailed";
  }

  function toggleSidebarView(): void {
    if (ctx.sidebarView.value !== "detailed" && ctx.sidebarView.value !== "hidden") {
      ctx.sidebarView.value = "detailed";
    }
    const currentIndex = ctx.SIDEBAR_VIEW_SEQUENCE.indexOf(ctx.sidebarView.value);
    const safeIndex = currentIndex >= 0 ? currentIndex : 0;
    const nextIndex = (safeIndex + 1) % ctx.SIDEBAR_VIEW_SEQUENCE.length;
    ctx.sidebarView.value = ctx.SIDEBAR_VIEW_SEQUENCE[nextIndex];

    if (!ctx.isSidebarDetailed.value) {
      ctx.treeFilter.value = "";
      ctx.clearSelectedNode();
    }

    if (ctx.isSidebarHidden.value) {
      ctx.serviceGroupingMode.value = "flat";
    }
  }

  function openSettingsPanel(): void {
    ctx.settingsPanel.open = true;
  }

  function closeSettingsPanel(): void {
    ctx.settingsPanel.open = false;
  }

  function toggleSettingsPanel(): void {
    ctx.settingsPanel.open = !ctx.settingsPanel.open;
  }

  return {
    applyGrid,
    applyTheme,
    closeSettingsPanel,
    openSettingsPanel,
    toggleEditMode,
    toggleServiceCardView,
    toggleSettingsPanel,
    toggleSidebarView,
  };
}
