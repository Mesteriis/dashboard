import type {
  DashboardConfig,
  DashboardItem,
  DashboardItemHealthcheck,
  ItemOpenMode,
  ItemType,
} from "@/features/stores/dashboard/storeTypes";

export function createDashboardCrudItemSubmit(ctx: any) {
  const {
    DEFAULT_ITEM_URL,
    allItemIdsInConfig,
    applyConfigMutation,
    authProfileOptions,
    config,
    editMode,
    ensureAbsoluteUrl,
    findSubgroupInConfig,
    itemEditor,
    makeUniqueId,
    normalizeId,
  } = ctx as any;

  async function addItem(groupId: string, subgroupId: string): Promise<void> {
    if (!editMode.value || !config.value) return;
    ctx.openCreateItemEditor(groupId, subgroupId);
  }

  function buildItemFromEditorForm(
    cfg: DashboardConfig,
    sourceItem: DashboardItem | null = null,
  ): DashboardItem {
    const form = itemEditor.form;
    const targetSubgroupId = String(
      form.parentSubgroupId || itemEditor.subgroupId || "",
    ).trim();
    const title = String(form.title || "").trim();
    if (!title) {
      throw new Error("Название сервиса обязательно");
    }

    const normalizedType = String(form.type || "")
      .trim()
      .toLowerCase();
    if (!["link", "iframe"].includes(normalizedType)) {
      throw new Error("Тип сервиса должен быть 'link' или 'iframe'");
    }

    const openMode = String(form.open || "new_tab");
    if (!["new_tab", "same_tab"].includes(openMode)) {
      throw new Error("Параметр open должен быть 'new_tab' или 'same_tab'");
    }

    const url = ensureAbsoluteUrl(form.url || DEFAULT_ITEM_URL);
    const itemIds = allItemIdsInConfig(cfg);
    if (itemEditor.mode === "edit") {
      itemIds.delete(itemEditor.originalItemId);
    }

    const rawId = String(form.id || "").trim();
    const generatedBase = `${targetSubgroupId || itemEditor.subgroupId}-${title}`;
    const normalizedId = normalizeId(rawId || generatedBase, "service");
    const nextId = rawId ? normalizedId : makeUniqueId(normalizedId, itemIds);

    if (rawId && itemIds.has(nextId)) {
      throw new Error(`ID '${nextId}' уже существует`);
    }

    const baseItem: DashboardItem = {
      ...(sourceItem ? { ...sourceItem } : {}),
      id: nextId,
      type: normalizedType as ItemType,
      title,
      url,
      icon: String(form.icon || "").trim() || null,
      site: String(form.siteInput || "").trim() || null,
      tags: ctx.normalizeStringList(form.tagsInput),
      open: openMode as ItemOpenMode,
    };
    const healthcheckEnabled = Boolean(form.healthcheckEnabled);
    const healthcheckUrl = ensureAbsoluteUrl(form.healthcheckUrl || url);
    const healthcheckConfig: DashboardItemHealthcheck = {
      type: "http",
      url: healthcheckUrl,
      interval_sec: ctx.clampNumber(form.healthcheckIntervalSec, 30, 5, 86400),
      timeout_ms: ctx.clampNumber(form.healthcheckTimeoutMs, 1500, 100, 120000),
      tls_verify: Boolean(form.healthcheckTlsVerify),
    };

    function applyHealthConfig(targetItem: DashboardItem): void {
      targetItem.monitor_health = healthcheckEnabled;

      if (healthcheckEnabled) {
        targetItem.check_url = healthcheckUrl;
        targetItem.healthcheck = healthcheckConfig;
        return;
      }

      targetItem.check_url = "";
      delete targetItem.healthcheck;
    }

    if (normalizedType === "link") {
      const linkItem: DashboardItem = { ...baseItem, type: "link" };
      delete linkItem.iframe;
      delete linkItem.auth_profile;
      applyHealthConfig(linkItem);

      return linkItem;
    }

    const sandboxMode = String(form.iframeSandboxMode || "default");
    let sandboxValue = null;
    if (
      sandboxMode === "enabled" ||
      sandboxMode === "enabled_same_origin" ||
      sandboxMode === "enabled_scripts" ||
      sandboxMode === "enabled_scripts_same_origin"
    ) {
      sandboxValue = true;
    }
    if (sandboxMode === "disabled") sandboxValue = false;

    const authProfile = String(form.authProfile || "").trim();
    if (
      authProfile &&
      !authProfileOptions.value.some(
        (profile: any) => profile.id === authProfile,
      )
    ) {
      throw new Error(`Auth profile '${authProfile}' не найден`);
    }

    const iframeAllowValues = ctx
      .normalizeStringList(form.iframeAllow)
      .filter((value: string) => !value.startsWith("allow-"));
    const sandboxTokens = ctx
      .normalizeStringList(form.iframeSandboxExtraTokens)
      .filter(
        (value: string) =>
          value.startsWith("allow-") &&
          value !== "allow-scripts" &&
          value !== "allow-same-origin",
      );
    if (
      sandboxMode === "enabled_scripts" ||
      sandboxMode === "enabled_scripts_same_origin"
    ) {
      sandboxTokens.push("allow-scripts");
    }
    if (
      sandboxMode === "enabled_same_origin" ||
      sandboxMode === "enabled_scripts_same_origin"
    ) {
      sandboxTokens.push("allow-same-origin");
    }

    const iframeItem: DashboardItem = {
      ...baseItem,
      type: "iframe",
      iframe: {
        sandbox: sandboxValue,
        allow: Array.from(new Set([...iframeAllowValues, ...sandboxTokens])),
        referrer_policy: String(form.iframeReferrerPolicy || "").trim() || null,
      },
    };
    applyHealthConfig(iframeItem);

    if (authProfile) {
      iframeItem.auth_profile = authProfile;
    }

    return iframeItem;
  }

  async function submitItemEditor(): Promise<void> {
    if (!itemEditor.open || itemEditor.submitting || !config.value) return;

    itemEditor.submitting = true;
    itemEditor.error = "";

    const success = await applyConfigMutation((cfg: DashboardConfig) => {
      const targetGroupId = String(
        itemEditor.form.parentGroupId || itemEditor.groupId || "",
      ).trim();
      const targetSubgroupId = String(
        itemEditor.form.parentSubgroupId || itemEditor.subgroupId || "",
      ).trim();
      const targetSubgroup = findSubgroupInConfig(
        cfg,
        targetGroupId,
        targetSubgroupId,
      );
      if (!targetSubgroup) {
        throw new Error(`Подгруппа '${targetSubgroupId}' не найдена`);
      }

      if (itemEditor.mode === "create") {
        const nextItem = buildItemFromEditorForm(cfg);
        targetSubgroup.items.push(nextItem);
        return true;
      }

      const sourceSubgroup = findSubgroupInConfig(
        cfg,
        itemEditor.groupId,
        itemEditor.subgroupId,
      );
      if (!sourceSubgroup) {
        throw new Error(`Подгруппа '${itemEditor.subgroupId}' не найдена`);
      }

      const index = (sourceSubgroup.items || []).findIndex(
        (entry: any) => entry.id === itemEditor.originalItemId,
      );
      if (index < 0) {
        throw new Error(`Элемент '${itemEditor.originalItemId}' не найден`);
      }
      const sourceItem = sourceSubgroup.items[index] || null;
      const nextItem = buildItemFromEditorForm(cfg, sourceItem);

      const isParentChanged =
        targetGroupId !== itemEditor.groupId ||
        targetSubgroupId !== itemEditor.subgroupId;

      if (isParentChanged && sourceSubgroup.items.length <= 1) {
        throw new Error(
          "В исходной подгруппе должен остаться минимум один элемент.",
        );
      }

      if (!isParentChanged) {
        sourceSubgroup.items.splice(index, 1, nextItem);
      } else {
        sourceSubgroup.items.splice(index, 1);
        targetSubgroup.items.push(nextItem);
      }

      return true;
    });

    itemEditor.submitting = false;
    if (success) {
      ctx.closeItemEditor(true);
    } else {
      itemEditor.error = ctx.saveError.value || "Не удалось сохранить сервис";
    }
  }

  return {
    addItem,
    buildItemFromEditorForm,
    submitItemEditor,
  };
}
