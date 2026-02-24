import type { DashboardItem, IframeReferrerPolicy } from "@/stores/dashboard/storeTypes";

export function createDashboardItemActionsSection(ctx: any) {
  async function openIframeItem(item: DashboardItem): Promise<void> {
    const defaultSandbox = Boolean(
      ctx.config.value?.security?.iframe?.default_sandbox ?? true,
    );
    const sandboxValue = item?.iframe?.sandbox;
    const rawAllowValues = Array.isArray(item?.iframe?.allow)
      ? item.iframe.allow
          .map((value) => String(value || "").trim())
          .filter(Boolean)
      : [];
    const sandboxTokens = rawAllowValues.filter((value) =>
      value.startsWith("allow-"),
    );
    const allowValues = rawAllowValues.filter(
      (value) => !value.startsWith("allow-"),
    );

    ctx.iframeModal.open = true;
    ctx.iframeModal.title = String(item.title || "");
    ctx.iframeModal.src = "";
    ctx.iframeModal.error = "";
    ctx.iframeModal.loading = true;
    ctx.iframeModal.sandbox =
      sandboxValue == null ? defaultSandbox : Boolean(sandboxValue);
    ctx.iframeModal.sandboxAttribute = sandboxTokens.join(" ");
    ctx.iframeModal.allow = allowValues.join("; ");
    ctx.iframeModal.referrerPolicy = (item?.iframe?.referrer_policy ||
      "") as IframeReferrerPolicy;
    ctx.iframeModal.src = String(item.url || "");
    ctx.iframeModal.loading = false;
  }

  function closeIframeModal(): void {
    ctx.iframeModal.open = false;
    ctx.iframeModal.title = "";
    ctx.iframeModal.src = "";
    ctx.iframeModal.error = "";
    ctx.iframeModal.loading = false;
    ctx.iframeModal.sandbox = false;
    ctx.iframeModal.sandboxAttribute = "";
    ctx.iframeModal.allow = "";
    ctx.iframeModal.referrerPolicy = "";
  }

  function openLinkItem(item: { open?: unknown; url?: unknown }): void {
    if (item.open === "same_tab") {
      window.location.assign(String(item.url || ""));
      return;
    }
    window.open(String(item.url || ""), "_blank", "noopener,noreferrer");
  }

  function openItemInNewTab(item: { url?: unknown } | null | undefined): void {
    if (!item?.url) return;
    window.open(String(item.url || ""), "_blank", "noopener,noreferrer");
  }

  function openItem(item: DashboardItem | Record<string, unknown>): void {
    if (item.type === "iframe") {
      openIframeItem(item as DashboardItem);
      return;
    }

    openLinkItem(item);
  }

  function itemIp(itemId: unknown): string {
    return ctx.itemIpById.value.get(String(itemId || "")) || "";
  }

  async function copyText(value: unknown): Promise<void> {
    const text = String(value || "");
    if (!text) return;
    if (!navigator.clipboard?.writeText) return;

    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // ignore clipboard errors
    }
  }

  async function copyUrl(url: unknown): Promise<void> {
    await copyText(url);
  }

  async function copyItemIp(itemId: unknown): Promise<void> {
    const ip = itemIp(itemId);
    if (!ip) return;
    await copyText(ip);
  }

  async function copyItemSshShortcut(itemId: unknown): Promise<void> {
    const ip = itemIp(itemId);
    if (!ip) return;
    await copyText(`ssh ${ip}`);
  }

  async function recheckItem(itemId: string): Promise<void> {
    if (!itemId) return;
    await ctx.refreshHealth([itemId]);
  }

  function pauseBackgroundPolling(): void {
    ctx.stopHealthPolling();
    ctx.resetWidgetPolling();
  }

  async function resumeBackgroundPolling(): Promise<void> {
    if (!ctx.config.value || ctx.loadingConfig.value) return;
    await ctx.initWidgetPolling();
    await ctx.startHealthPolling();
  }

  async function syncPollingWithVisibility(): Promise<void> {
    if (ctx.visibilitySyncInFlight) return;
    ctx.visibilitySyncInFlight = true;

    try {
      if (ctx.isDocumentVisible.value) {
        await resumeBackgroundPolling();
      } else {
        pauseBackgroundPolling();
      }
    } finally {
      ctx.visibilitySyncInFlight = false;
    }
  }

  function handleDocumentVisibilityChange(): void {
    ctx.isDocumentVisible.value = document.visibilityState !== "hidden";
    syncPollingWithVisibility();
  }

  return {
    closeIframeModal,
    copyItemIp,
    copyItemSshShortcut,
    copyText,
    copyUrl,
    handleDocumentVisibilityChange,
    itemIp,
    openIframeItem,
    openItem,
    openItemInNewTab,
    openLinkItem,
    pauseBackgroundPolling,
    recheckItem,
    resumeBackgroundPolling,
    syncPollingWithVisibility,
  };
}
