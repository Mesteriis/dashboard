export function createDashboardCrudItemEditor(ctx: any) {
  const {
    DEFAULT_ITEM_URL,
    config,
    defaultItemEditorForm,
    findSubgroupInConfig,
    groupById,
    itemEditor,
  } = ctx as any;

  function closeItemEditor(force: boolean | MouseEvent = false): void {
    const forceClose = typeof force === "boolean" ? force : false;
    if (itemEditor.submitting && !forceClose) return;

    itemEditor.open = false;
    itemEditor.mode = "create";
    itemEditor.groupId = "";
    itemEditor.subgroupId = "";
    itemEditor.originalItemId = "";
    itemEditor.error = "";
    itemEditor.submitting = false;
    itemEditor.form = defaultItemEditorForm();
  }

  function openCreateItemEditor(groupId: string, subgroupId: string): void {
    const subgroup = findSubgroupInConfig(config.value, groupId, subgroupId);
    if (!subgroup) {
      ctx.saveStatus.value = "error";
      ctx.saveError.value = `Подгруппа '${subgroupId}' не найдена`;
      return;
    }

    itemEditor.open = true;
    itemEditor.mode = "create";
    itemEditor.groupId = groupId;
    itemEditor.subgroupId = subgroupId;
    itemEditor.originalItemId = "";
    itemEditor.error = "";
    itemEditor.submitting = false;
    itemEditor.form = {
      ...defaultItemEditorForm(),
      parentGroupId: groupId,
      parentSubgroupId: subgroupId,
    };
  }

  function setItemEditorParentGroup(groupId: string): void {
    const normalizedGroupId = String(groupId || "").trim();
    itemEditor.form.parentGroupId = normalizedGroupId;

    const group = groupById.value.get(normalizedGroupId);
    if (!group) {
      itemEditor.form.parentSubgroupId = "";
      return;
    }

    const hasCurrentSubgroup = (group.subgroups || []).some(
      (subgroup: any) => subgroup.id === itemEditor.form.parentSubgroupId,
    );
    if (hasCurrentSubgroup) return;
    itemEditor.form.parentSubgroupId = String(group.subgroups?.[0]?.id || "");
  }

  function openEditItemEditor(
    groupId: string,
    subgroupId: string,
    itemId: string,
  ): void {
    const subgroup = findSubgroupInConfig(config.value, groupId, subgroupId);
    const item = (subgroup?.items || []).find((entry: any) => entry.id === itemId);
    if (!subgroup || !item) {
      ctx.saveStatus.value = "error";
      ctx.saveError.value = `Элемент '${itemId}' не найден`;
      return;
    }

    itemEditor.open = true;
    itemEditor.mode = "edit";
    itemEditor.groupId = groupId;
    itemEditor.subgroupId = subgroupId;
    itemEditor.originalItemId = itemId;
    itemEditor.error = "";
    itemEditor.submitting = false;
    const itemCheckUrl = String(
      item.check_url || item.healthcheck?.url || item.url || DEFAULT_ITEM_URL,
    );
    const hasLegacyHealthConfig = Boolean(item.healthcheck || item.check_url);
    const explicitMonitorHealth = ctx.parseBooleanFlag(item.monitor_health);
    const healthEnabled =
      explicitMonitorHealth == null
        ? hasLegacyHealthConfig
        : explicitMonitorHealth;
    const iframeAllowValues =
      item.type === "iframe"
        ? ctx.normalizeStringList(item.iframe?.allow || [])
        : [];
    const iframeSandboxTokens = iframeAllowValues.filter((value: string) =>
      value.startsWith("allow-"),
    );
    const allowScriptsEnabled = iframeSandboxTokens.includes("allow-scripts");
    const allowSameOriginEnabled =
      iframeSandboxTokens.includes("allow-same-origin");

    itemEditor.form = {
      id: item.id,
      title: String(item.title || ""),
      type: item.type === "iframe" ? "iframe" : "link",
      url: String(item.url || DEFAULT_ITEM_URL),
      icon: item.icon || "",
      siteInput: String(item.site || ""),
      tagsInput: (item.tags || []).join(", "),
      open: item.open === "same_tab" ? "same_tab" : "new_tab",
      healthcheckEnabled: healthEnabled,
      healthcheckUrl: itemCheckUrl,
      healthcheckIntervalSec: item.healthcheck
        ? Number(item.healthcheck.interval_sec || 30)
        : 30,
      healthcheckTimeoutMs: item.healthcheck
        ? Number(item.healthcheck.timeout_ms || 1500)
        : 1500,
      healthcheckTlsVerify: ctx.resolveHealthcheckTlsVerify(item.healthcheck),
      iframeSandboxMode:
        item.type === "iframe"
          ? item.iframe?.sandbox == null
            ? allowScriptsEnabled && allowSameOriginEnabled
              ? "enabled_scripts_same_origin"
              : allowScriptsEnabled
                ? "enabled_scripts"
                : allowSameOriginEnabled
                  ? "enabled_same_origin"
                  : "default"
            : item.iframe.sandbox
              ? allowScriptsEnabled && allowSameOriginEnabled
                ? "enabled_scripts_same_origin"
                : allowScriptsEnabled
                  ? "enabled_scripts"
                  : allowSameOriginEnabled
                    ? "enabled_same_origin"
                    : "enabled"
              : "disabled"
          : "default",
      iframeAllow:
        item.type === "iframe"
          ? iframeAllowValues.filter(
              (value: string) => !value.startsWith("allow-"),
            )
          : [],
      iframeSandboxExtraTokens:
        item.type === "iframe"
          ? iframeSandboxTokens.filter(
              (value: string) =>
                value !== "allow-scripts" && value !== "allow-same-origin",
            )
          : [],
      iframeReferrerPolicy:
        item.type === "iframe" ? item.iframe?.referrer_policy || "" : "",
      authProfile: item.type === "iframe" ? item.auth_profile || "" : "",
      parentGroupId: groupId,
      parentSubgroupId: subgroupId,
    };
  }

  return {
    closeItemEditor,
    openCreateItemEditor,
    openEditItemEditor,
    setItemEditorParentGroup,
  };
}
