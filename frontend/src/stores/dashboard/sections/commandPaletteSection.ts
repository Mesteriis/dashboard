import type { CommandPaletteEntry } from "@/stores/dashboard/storeTypes";

export function createDashboardCommandPaletteSection(ctx: any) {
  function openCommandPalette(): void {
    ctx.commandPaletteQuery.value = "";
    ctx.commandPaletteActiveIndex.value = 0;
    ctx.commandPaletteOpen.value = true;
  }

  function closeCommandPalette(): void {
    ctx.commandPaletteOpen.value = false;
    ctx.commandPaletteQuery.value = "";
    ctx.commandPaletteActiveIndex.value = 0;
  }

  function toggleCommandPalette(): void {
    if (ctx.commandPaletteOpen.value) {
      closeCommandPalette();
      return;
    }
    openCommandPalette();
  }

  function setCommandPaletteQuery(value: unknown): void {
    ctx.commandPaletteQuery.value = String(value || "");
    ctx.commandPaletteActiveIndex.value = 0;
  }

  function setCommandPaletteActiveIndex(index: number): void {
    const lastIndex = ctx.commandPaletteResults.value.length - 1;
    if (lastIndex < 0) {
      ctx.commandPaletteActiveIndex.value = 0;
      return;
    }
    ctx.commandPaletteActiveIndex.value = Math.min(Math.max(index, 0), lastIndex);
  }

  function moveCommandPaletteSelection(step: number): void {
    const resultsCount = ctx.commandPaletteResults.value.length;
    if (!resultsCount) {
      ctx.commandPaletteActiveIndex.value = 0;
      return;
    }

    const start = ctx.commandPaletteActiveIndex.value;
    const next = (start + step + resultsCount) % resultsCount;
    ctx.commandPaletteActiveIndex.value = next;
  }

  function focusCommandPaletteEntry(
    entry: CommandPaletteEntry | null | undefined,
  ): void {
    if (!entry) return;
    if (!entry.item) return;
    if (entry.pageId) {
      ctx.activePageId.value = entry.pageId;
    }
    ctx.selectItemNode(entry.groupKey, entry.subgroupId, entry.item.id);
  }

  function activateCommandPaletteEntry(
    entry: CommandPaletteEntry | null | undefined,
  ): void {
    if (!entry) return;

    if (entry.type === "action" && entry.action === "open_settings_panel") {
      closeCommandPalette();
      void ctx.goSettings();
      return;
    }
    if (entry.type === "action" && entry.action === "open_plugin_panel") {
      closeCommandPalette();
      void ctx.goPluginsPanel();
      return;
    }

    if (!entry.item) return;
    focusCommandPaletteEntry(entry);
    ctx.openItem(entry.item);
    closeCommandPalette();
  }

  function activateCommandPaletteSelection(): void {
    activateCommandPaletteEntry(ctx.activeCommandPaletteEntry.value);
  }

  async function copyCommandPaletteEntryUrl(
    entry: CommandPaletteEntry | null | undefined,
  ): Promise<void> {
    if (entry?.type !== "item" || !entry?.item?.url) return;
    await ctx.copyUrl(entry.item.url);
  }

  return {
    activateCommandPaletteEntry,
    activateCommandPaletteSelection,
    closeCommandPalette,
    copyCommandPaletteEntryUrl,
    focusCommandPaletteEntry,
    moveCommandPaletteSelection,
    openCommandPalette,
    setCommandPaletteActiveIndex,
    setCommandPaletteQuery,
    toggleCommandPalette,
  };
}
