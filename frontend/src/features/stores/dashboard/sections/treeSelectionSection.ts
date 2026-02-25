export function createDashboardTreeSelectionSection(ctx: any) {
  function resolvePageForGroupKey(groupKey: string): string {
    const normalized = String(groupKey || "");
    if (!normalized) return "";

    if (normalized.startsWith("group:")) {
      const groupId = normalized.slice(6);
      return ctx.pageByBlockGroupId.value.get(groupId) || "";
    }

    if (!normalized.startsWith("subgroup:")) {
      return "";
    }

    const subgroupId = normalized.slice(9);
    const subgroupRef = ctx.subgroupById.value.get(subgroupId);
    if (subgroupRef) {
      return (
        ctx.pageByBlockGroupId.value.get(String(subgroupRef.group.id || "")) ||
        ctx.pageByBlockGroupId.value.get(subgroupId) ||
        ""
      );
    }
    return ctx.pageByBlockGroupId.value.get(subgroupId) || "";
  }

  function activatePageForGroupKey(groupKey: string): void {
    const pageId = resolvePageForGroupKey(groupKey);
    if (!pageId) return;
    if (
      !ctx.pages.value.some(
        (page: any) => String(page?.id || "") === String(pageId || ""),
      )
    ) {
      return;
    }
    if (String(ctx.activePageId.value || "") !== String(pageId || "")) {
      ctx.preserveTreeSelectionOnPageSwitch = true;
    }
    ctx.activePageId.value = String(pageId || "");
  }

  function toggleGroupNode(groupKey: string): void {
    activatePageForGroupKey(groupKey);
    ctx.expandedGroups[groupKey] = !isGroupExpanded(groupKey);
    ctx.selectedNode.groupKey = groupKey;
    ctx.selectedNode.subgroupId = "";
    ctx.selectedNode.itemId = "";
  }

  function selectSubgroupNode(groupKey: string, subgroupId: string): void {
    activatePageForGroupKey(groupKey);
    ctx.expandedGroups[groupKey] = true;
    ctx.selectedNode.groupKey = groupKey;
    ctx.selectedNode.subgroupId = subgroupId;
    ctx.selectedNode.itemId = "";
  }

  function selectItemNode(groupKey: string, subgroupId: string, itemId: string): void {
    activatePageForGroupKey(groupKey);
    ctx.expandedGroups[groupKey] = true;
    ctx.selectedNode.groupKey = groupKey;
    ctx.selectedNode.subgroupId = subgroupId;
    ctx.selectedNode.itemId = itemId;
  }

  function isGroupExpanded(groupKey: string): boolean {
    return Boolean(ctx.expandedGroups[groupKey]);
  }

  function isGroupSelected(groupKey: string): boolean {
    return (
      ctx.selectedNode.groupKey === groupKey &&
      !ctx.selectedNode.subgroupId &&
      !ctx.selectedNode.itemId
    );
  }

  function isSubgroupSelected(groupKey: string, subgroupId: string): boolean {
    return (
      ctx.selectedNode.groupKey === groupKey &&
      ctx.selectedNode.subgroupId === subgroupId &&
      !ctx.selectedNode.itemId
    );
  }

  function isItemSelected(itemId: string): boolean {
    return ctx.selectedNode.itemId === itemId;
  }

  return {
    activatePageForGroupKey,
    isGroupExpanded,
    isGroupSelected,
    isItemSelected,
    isSubgroupSelected,
    resolvePageForGroupKey,
    selectItemNode,
    selectSubgroupNode,
    toggleGroupNode,
  };
}
