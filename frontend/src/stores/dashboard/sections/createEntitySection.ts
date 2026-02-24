import type {
  CreateEntityKind,
  CreateOption,
  DashboardItem,
  ItemWithOrigin,
  SidebarIconNode,
} from "@/stores/dashboard/storeTypes";

export function createDashboardCreateEntitySection(ctx: any) {
  function resolveDefaultDashboardId(preferredDashboardId = ""): string {
    const normalized = String(preferredDashboardId || "").trim();
    if (
      normalized &&
      ctx.pages.value.some(
        (page: any) => String(page?.id || "") === normalized,
      )
    ) {
      return normalized;
    }
    const activeId = String(ctx.activePageId.value || "").trim();
    if (
      activeId &&
      ctx.pages.value.some((page: any) => String(page?.id || "") === activeId)
    ) {
      return activeId;
    }
    return String(ctx.pages.value[0]?.id || "");
  }

  function resolveGroupIdsForDashboard(dashboardId: string): string[] {
    const page = ctx.pages.value.find(
      (entry: any) => String(entry.id || "") === String(dashboardId || ""),
    );
    if (!page) return [];

    const ids = new Set<string>();
    for (const block of page.blocks || []) {
      if (block?.type !== "groups") continue;
      for (const rawId of block.group_ids || []) {
        const normalizedId = String(rawId || "").trim();
        if (!normalizedId) continue;

        const directGroup = ctx.groupById.value.get(normalizedId);
        if (directGroup) {
          ids.add(String(directGroup.id || ""));
          continue;
        }

        const subgroupRef = ctx.subgroupById.value.get(normalizedId);
        if (subgroupRef) {
          ids.add(String(subgroupRef.group.id || ""));
        }
      }
    }
    return Array.from(ids);
  }

  function resolveDefaultGroupId(preferredGroupId = ""): string {
    const normalized = String(preferredGroupId || "").trim();
    if (normalized && ctx.groupById.value.has(normalized)) {
      return normalized;
    }
    const selectedGroupId = ctx.selectedNode.groupKey.startsWith("group:")
      ? ctx.selectedNode.groupKey.slice(6)
      : "";
    if (selectedGroupId && ctx.groupById.value.has(selectedGroupId)) {
      return selectedGroupId;
    }
    return ctx.createEntityGroupOptions.value[0]?.id || "";
  }

  function resolveDefaultSubgroupId(groupId: string, preferredSubgroupId = ""): string {
    const group = ctx.groupById.value.get(String(groupId || "").trim());
    if (!group) {
      return "";
    }
    const normalized = String(preferredSubgroupId || "").trim();
    const hasExplicit = (group.subgroups || []).some(
      (subgroup: any) => String(subgroup?.id || "") === normalized,
    );
    if (hasExplicit) {
      return normalized;
    }
    const hasSelected = (group.subgroups || []).some(
      (subgroup: any) =>
        String(subgroup?.id || "") === String(ctx.selectedNode.subgroupId || ""),
    );
    if (hasSelected) {
      return String(ctx.selectedNode.subgroupId || "");
    }
    return String(group.subgroups?.[0]?.id || "");
  }

  function closeCreateChooser(): void {
    ctx.createChooser.open = false;
    ctx.createChooser.groupId = "";
    ctx.createChooser.subgroupId = "";
  }

  function openCreateChooser(groupId = "", subgroupId = ""): void {
    if (!ctx.editMode.value) return;
    const resolvedGroupId = resolveDefaultGroupId(groupId);
    ctx.createChooser.open = true;
    ctx.createChooser.groupId = resolvedGroupId;
    ctx.createChooser.subgroupId = resolveDefaultSubgroupId(resolvedGroupId, subgroupId);
  }

  function closeCreateEntityEditor(force: boolean | MouseEvent = false): void {
    const forceClose = typeof force === "boolean" ? force : false;
    if (ctx.createEntityEditor.submitting && !forceClose) return;
    ctx.createEntityEditor.open = false;
    ctx.createEntityEditor.submitting = false;
    ctx.createEntityEditor.error = "";
    ctx.createEntityEditor.form = ctx.defaultCreateEntityForm();
  }

  function setCreateEntityKind(kind: CreateEntityKind): void {
    ctx.createEntityEditor.form.kind = kind;
  }

  function setCreateEntityParentDashboard(dashboardId: string): void {
    const resolvedDashboardId = resolveDefaultDashboardId(dashboardId);
    ctx.createEntityEditor.form.parentDashboardId = resolvedDashboardId;

    const groupIds = resolveGroupIdsForDashboard(resolvedDashboardId);
    const preferredGroupId = String(ctx.createEntityEditor.form.parentGroupId || "");
    const nextGroupId = groupIds.includes(preferredGroupId)
      ? preferredGroupId
      : String(groupIds[0] || "");
    ctx.createEntityEditor.form.parentGroupId = nextGroupId;
    ctx.createEntityEditor.form.parentSubgroupId = resolveDefaultSubgroupId(
      nextGroupId,
      ctx.createEntityEditor.form.parentSubgroupId,
    );
  }

  function setCreateEntityParentGroup(groupId: string): void {
    const isItemKind = ctx.createEntityEditor.form.kind === "item";
    let resolvedGroupId = "";

    if (isItemKind) {
      const allowedGroupIds = resolveGroupIdsForDashboard(
        ctx.createEntityEditor.form.parentDashboardId,
      );
      const normalized = String(groupId || "").trim();
      resolvedGroupId = allowedGroupIds.includes(normalized)
        ? normalized
        : String(allowedGroupIds[0] || "");
    } else {
      resolvedGroupId = resolveDefaultGroupId(groupId);
    }

    ctx.createEntityEditor.form.parentGroupId = resolvedGroupId;
    ctx.createEntityEditor.form.parentSubgroupId = resolveDefaultSubgroupId(
      resolvedGroupId,
      ctx.createEntityEditor.form.parentSubgroupId,
    );
  }

  function openCreateEntityEditor(kind: CreateEntityKind): void {
    const dashboardId = resolveDefaultDashboardId(ctx.activePageId.value);
    const itemDashboardGroupIds = resolveGroupIdsForDashboard(dashboardId);
    const preferredItemGroupId = String(ctx.createChooser.groupId || "").trim();
    const defaultItemGroupId = itemDashboardGroupIds.includes(preferredItemGroupId)
      ? preferredItemGroupId
      : String(itemDashboardGroupIds[0] || "");
    const groupId =
      kind === "item" ? defaultItemGroupId : resolveDefaultGroupId(ctx.createChooser.groupId);
    const subgroupId = resolveDefaultSubgroupId(groupId, ctx.createChooser.subgroupId);

    ctx.createEntityEditor.open = true;
    ctx.createEntityEditor.submitting = false;
    ctx.createEntityEditor.error = "";
    ctx.createEntityEditor.form = {
      ...ctx.defaultCreateEntityForm(),
      kind,
      icon: kind === "dashboard" ? "layout-dashboard" : "folder",
      parentDashboardId: dashboardId,
      parentGroupId: groupId,
      parentSubgroupId: subgroupId,
    };
  }

  function openCreateOption(option: CreateOption): void {
    closeCreateChooser();
    if (option === "dashboard") {
      openCreateEntityEditor("dashboard");
      return;
    }
    if (option === "group_or_subgroup") {
      openCreateEntityEditor("group");
      return;
    }
    openCreateEntityEditor("item");
  }

  function isSidebarIconActive(node: SidebarIconNode | null | undefined): boolean {
    if (!node) return false;
    if (node.type === "group") return ctx.isGroupSelected(node.groupKey);
    if (node.type === "subgroup") {
      return ctx.isSubgroupSelected(node.groupKey, node.subgroupId);
    }
    return false;
  }

  function sidebarIconNodeTitle(node: SidebarIconNode | null | undefined): string {
    if (!node) return "";
    if (node.type === "group") {
      return `Группа: ${node.group?.title || ""}`;
    }
    if (node.type === "subgroup") {
      return `Подгруппа: ${node.subgroup?.title || ""}`;
    }
    return "";
  }

  function selectSidebarIconNode(node: SidebarIconNode | null | undefined): void {
    if (!node) return;

    if (node.type === "group") {
      ctx.expandedGroups[node.groupKey] = true;
      ctx.selectedNode.groupKey = node.groupKey;
      ctx.selectedNode.subgroupId = "";
      ctx.selectedNode.itemId = "";
      return;
    }

    if (node.type === "subgroup") {
      ctx.selectSubgroupNode(node.groupKey, node.subgroupId);
    }
  }

  function onItemCardClick(
    groupKey: string,
    subgroupId: string,
    item: DashboardItem & Partial<ItemWithOrigin>,
  ): void {
    void groupKey;
    void subgroupId;
    if (ctx.editMode.value) return;
    ctx.openItem(item);
  }

  return {
    closeCreateChooser,
    closeCreateEntityEditor,
    isSidebarIconActive,
    onItemCardClick,
    openCreateChooser,
    openCreateEntityEditor,
    openCreateOption,
    resolveDefaultDashboardId,
    resolveDefaultGroupId,
    resolveDefaultSubgroupId,
    resolveGroupIdsForDashboard,
    selectSidebarIconNode,
    setCreateEntityKind,
    setCreateEntityParentDashboard,
    setCreateEntityParentGroup,
    sidebarIconNodeTitle,
  };
}
